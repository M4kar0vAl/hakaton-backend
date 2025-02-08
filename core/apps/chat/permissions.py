from typing import Dict, Any

from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from djangochannelsrestframework.permissions import IsAuthenticated, BasePermission

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Brand, Match
from core.apps.chat.models import Room
from core.apps.payments.models import Subscription

User = get_user_model()


class IsAuthenticatedConnect(IsAuthenticated):
    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        user = scope.get('user')
        if type(user) is User:
            return user.is_authenticated
        return False


class IsBrand(BasePermission):
    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return await Brand.objects.filter(user=user).aexists()

    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return await Brand.objects.filter(user=user).aexists()


class HasActiveSub(BasePermission):
    """
    Allow access only to users that have an active subscription.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        return await Subscription.objects.filter(
            is_active=True, end_date__gt=timezone.now(), brand__user=scope['user']
        ).aexists()

    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        return await Subscription.objects.filter(
            is_active=True, end_date__gt=timezone.now(), brand__user=scope['user']
        ).aexists()


class IsAdminUser(BasePermission):
    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return user.is_staff

    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return user.is_staff


class CanUserJoinRoom(BasePermission):
    """
    Check whether the user can join the room.

    User can join a room if not connected to a room yet.
    User can join only rooms he is a participant of.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if hasattr(consumer, 'room'):
            # if already in room
            return False

        room_pk = kwargs.get('room_pk')
        brand_rooms = consumer.brand_rooms

        if room_pk not in brand_rooms:
            # update brand rooms
            brand_rooms = await database_sync_to_async(set)(scope['user'].rooms.values_list('pk', flat=True))

            # check again
            if room_pk not in brand_rooms:
                return False

        return True


class UserInRoom(BasePermission):
    """
    Allows access to the action if the user connected to a room.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if hasattr(consumer, 'room'):
            return True

        return False


class CanCreateMessage(BasePermission):
    """
    Check whether the current user allowed to create a message in a room.

    Admins can create messages only in support rooms.
    Other users can create messages in all rooms.

    If room type is instant, then allow to create a message only
    if the current user is the initiator of the instant coop and hasn't created any messages in this room yet.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if not hasattr(consumer, 'room'):
            return False

        room = consumer.room

        if not hasattr(consumer, 'brand'):
            return False

        brand = consumer.brand

        if room.type == Room.INSTANT:
            match = await Match.objects.aget(room=room)
            if match.initiator_id != brand.id:
                # if the user is not the initiator of the instant coop
                return False
            elif await scope['user'].messages.filter(room=room).aexists():
                # if user has already sent message to this instant room
                return False

        return True


class NotInBlacklist(BasePermission):
    """
    Allow access only if current brand haven't blocked interlocutor
    AND interlocutor haven't blocked current brand.

    If room type is Support, then access will be granted,
    because admins don't have brands and blacklist is inaccessible for them.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if not hasattr(consumer, 'room'):
            return False

        room = consumer.room

        if not hasattr(consumer, 'brand'):
            return False

        brand = consumer.brand

        # support room doesn't have interlocutor, so allow access to it
        if room.type == Room.SUPPORT:
            return True

        try:
            interlocutor_user = await room.participants.exclude(id=scope['user'].id).aget()
        except User.DoesNotExist:
            interlocutor_user = None

        if not interlocutor_user:
            # If user was deleted, then deny access.
            # If user already deleted, then it cannot be restored,
            # that's why access will be denied
            return False

        interlocutor_brand = await Brand.objects.aget(user=interlocutor_user)

        # If current brand blocked interlocutor OR interlocutor blocked current brand,
        # then deny access
        return not await BlackList.objects.filter(
            Q(initiator=brand, blocked=interlocutor_brand)
            | Q(initiator=interlocutor_brand, blocked=brand)
        ).aexists()


class CanAdminJoinRoom(BasePermission):
    """
    Check whether the admin can join a room.

    Admin can join a room if not connected to a room yet.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if hasattr(consumer, 'room'):
            return False

        return True


class CanAdminAct(BasePermission):
    """
    Check if the admin user allowed to take "write" actions in the room.

    "write" actions are:
    - create message
    - edit message
    - delete message

    Admins can take "write" actions only in support rooms.
    """

    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        if not scope['user'].is_staff:
            return False

        if not hasattr(consumer, 'room'):
            return False

        return consumer.room.type == Room.SUPPORT
