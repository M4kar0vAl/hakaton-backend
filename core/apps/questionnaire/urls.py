from .api import QuestionViewSet
from rest_framework import routers


router = routers.DefaultRouter()
router.register('', QuestionViewSet, basename='question')

urlpatterns = []

urlpatterns += router.urls
