from channels.db import database_sync_to_async
from django.core.paginator import Paginator, InvalidPage
from django.db import transaction, DatabaseError
from django.db.models import Model, QuerySet

from core.apps.chat.exceptions import ServerError, BadRequest
from core.apps.chat.models import Message, Room


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
