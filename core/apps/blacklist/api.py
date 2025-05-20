from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from core.apps.blacklist.models import BlackList
from core.apps.blacklist.permissions import IsBlacklistInitiator
from core.apps.blacklist.serializers import BlacklistListSerializer, BlacklistCreateSerializer
from core.apps.brand.pagination import StandardResultsSetPagination
from core.apps.brand.permissions import IsBrand
from core.apps.payments.permissions import HasActiveSub


class BlacklistViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = BlackList.objects.all()
    serializer_class = BlacklistListSerializer
    permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action == 'list':
            return self.request.user.brand.blacklist_as_initiator.select_related('blocked__category').order_by('-id')

        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action == 'destroy':
            permission_classes += [IsBlacklistInitiator]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return BlacklistCreateSerializer

        return super().get_serializer_class()
