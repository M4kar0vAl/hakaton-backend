from rest_framework import permissions


class IsBlacklistInitiator(permissions.BasePermission):
    """
    Allow access only to brand that is the initiator of the blacklist entity.
    """
    def has_object_permission(self, request, view, obj):
        return obj.initiator == request.user.brand
