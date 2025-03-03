from typing import Set

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, InvalidPage
from django.db import transaction, DatabaseError
from django.db.models import Model, QuerySet, Prefetch
from djangochannelsrestframework.observer import model_observer

from core.apps.chat.exceptions import ServerError, BadRequest
from core.apps.chat.models import Message, Room


User = get_user_model()


class ConsumerSerializationMixin:
    """
    Mixin that handles serialization in consumers.

    Consumer must have a defined get_serializer method, which should return necessary serializer class
    """

    @database_sync_to_async
    def get_serialized_data(self, instance: Model | QuerySet[Model], many: bool = False, **kwargs):
        serializer = self.get_serializer(instance=instance, many=many, action_kwargs=kwargs)

        return serializer.data


class ConsumerUtilitiesMixin:
    """
    A mixin that provides utility functions to the consumer.
    """

    async def edit_message_in_db(self, msg_id: int, text: str) -> int:
        """
        Edit message text in db. Allows editing only messages authored by the current user.
        The consumer must have a "room" attribute.

        Args:
            msg_id: primary key of the message being edited
            text: new text to be set

        Returns:
            The number of rows matched in the db.
            Either 0 if the message with msg_id was not found in the db
            or 1 if the message was found and updated
        """
        # filter uses user = self.scope['user'] to allow editing current user's messages only
        # if the message with id <msg_id> don't belong to the user, then nothing happens
        return await Message.objects.filter(pk=msg_id, user=self.scope['user'], room=self.room).aupdate(text=text)

    async def delete_messages_in_db(self, msg_id_list: list[int]) -> int:
        """
        Delete messages from db. Allows deleting only messages authored by the current user.
        The consumer must have a "room" attribute.

        Args:
            msg_id_list: list of ids of message to delete

        Returns:
            The number of messages deleted
        """
        deleted: tuple[int, dict] = await Message.objects.filter(
            pk__in=msg_id_list, user=self.scope['user'], room=self.room
        ).adelete()
        return deleted[0]

    @database_sync_to_async
    def get_or_create_support_room(self) -> tuple[Room, bool]:
        """
        Get the support room for the current brand. If the room does not exist, then create it.

        Returns:
            The room instance and the status whether it was created or not.
        """
        created = False  # whether a new room was created
        try:
            room = self.scope['user'].rooms.get(type=Room.SUPPORT)
        except Room.DoesNotExist:
            try:
                with transaction.atomic():
                    room = Room.objects.create(type=Room.SUPPORT)
                    room.participants.add(self.scope['user'])
                    created = True
            except DatabaseError:
                raise ServerError("Room creation failed! Please try again.")

        return room, created


class ConsumerPaginationMixin:
    """
    A mixin that provides pagination functions to the consumer.
    """

    @database_sync_to_async
    def paginate_queryset(self, queryset: QuerySet, per_page: int, action: str, orphans: int = 0) -> Paginator:
        """
        Paginate a queryset. Remembers resulting paginator for the action to avoid recreating it if one already exists.

        Args:
            queryset: the queryset to paginate
            per_page: the number of objects per page
            action: the name of the action to paginate for
            orphans: if the number of objects on the last page is less than or equal to orphans,
                     then those items will be added to the previous page, which will become the last page

        Returns:
            Paginator instance.
        """
        paginator = self._get_paginator(action)

        if paginator is None:
            paginator = Paginator(queryset, per_page, orphans)
            self.action_paginators[action] = paginator

        return paginator

    @database_sync_to_async
    def get_page_objects(self, paginator: Paginator, page_number: int):
        """
        Get objects of the page.

        Args:
            paginator: paginator instance for the current action
            page_number: the page number which objects to return

        Returns:
            The list of objects on the page
        """

        page = self._get_page(paginator, page_number)

        return page.object_list

    @database_sync_to_async
    def get_paginated_data(self, data, paginator: Paginator, page_number: int):
        """
        Get objects of the page and wrap them with pagination info.
        """

        next_ = self._get_next_page_number(paginator, page_number)

        return {
            'count': paginator.count,
            'results': data,
            'next': next_
        }

    def delete_paginator_for_action(self, action: str) -> None:
        """
        Delete paginator for the specified action.
        """
        try:
            self.action_paginators.pop(action)
        except KeyError:
            pass

    def delete_all_paginators(self) -> None:
        """
        Delete paginators for all actions of the consumer.
        """

        self.action_paginators = {}

    def _get_paginator(self, action: str):
        paginator = self.action_paginators.get(action)

        return paginator

    def _get_page(self, paginator: Paginator, page_number: int):
        self._check_page_number(paginator, page_number)

        page = paginator.get_page(page_number)

        return page

    def _get_next_page_number(self, paginator: Paginator, page_number: int) -> int:
        page = self._get_page(paginator, page_number)

        try:
            next_ = page.next_page_number()
        except InvalidPage:
            next_ = None

        return next_

    def _check_page_number(self, paginator: Paginator, page_number: int) -> None:
        if type(page_number) is not int:
            raise BadRequest('Page number must be an integer!')

        if page_number not in paginator.page_range:
            raise BadRequest(f'Page {page_number} does not exist!')


class ConsumerObserveAdminActivityMixin:
    """
    Mixin that observes user activity and maintains the set of all admins' pks.

    Consumer must have "admins_pks_set" attribute. In most cases should be populated during connect method.
    """

    def __init__(self):
        self.admins_pks_set = set()

    # WARNING
    # When using this to decorate a method to avoid the method firing multiple times you should ensure that
    # if there are multiple @model_observer wrapped methods for the same model type within a single file
    # that each method HAS A DIFFERENT NAME.
    # (https://github.com/NilCoalescing/djangochannelsrestframework?tab=readme-ov-file#subscribing-to-all-instances-of-a-model)
    @model_observer(User)
    async def user_activity(
            self,
            data,
            action,
            **kwargs
    ):
        if not data:
            return

        if data['is_staff']:
            if action == 'create':
                self.admins_pks_set.add(data['pk'])
            elif action == 'delete':
                self.admins_pks_set.remove(data['pk'])

    @user_activity.serializer
    def user_activity(self, instance: User, action, **kwargs):
        if action == 'update':
            return

        return {'pk': instance.pk, 'is_staff': instance.is_staff}

    def get_user_groups_for_room(self, room: Room) -> Set[str]:
        """
        Get a list of group names for a given room.
        Room instance must have prefetched participants in attribute 'room_participants'.

        Args:
            room: instance of the room to get groups for

        Returns:
            List of group names as strings
        """
        groups = {f'user_{user.pk}' for user in room.room_participants}

        if room.type == Room.SUPPORT:
            for pk in self.admins_pks_set:
                groups.add(f'user_{pk}')

        return groups

    @database_sync_to_async
    def get_room_with_participants(self, room_pk):
        try:
            room = Room.objects.filter(pk=room_pk).prefetch_related(
                Prefetch(
                    'participants',
                    queryset=User.objects.all(),
                    to_attr='room_participants'
                )
            ).get()
        except Room.DoesNotExist:
            return None

        return room

    @database_sync_to_async
    def get_admins_pks_set(self):
        admin_pks = User.objects.filter(is_staff=True, is_active=True).values_list('pk', flat=True)

        return set(admin_pks)
