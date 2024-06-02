from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser

from core.apps.brand.models import Brand
from core.apps.brand.permissions import IsOwnerOrReadOnly
from core.apps.brand.serializers import BrandSerializer


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsOwnerOrReadOnly]
