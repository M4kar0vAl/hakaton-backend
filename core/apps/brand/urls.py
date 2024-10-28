from django.urls import path
from rest_framework import routers

from core.apps.brand.api import BrandViewSet, QuestionnaireChoicesListView, CollaborationCreateView

router = routers.DefaultRouter()
router.register('brand', BrandViewSet, basename='brand')

urlpatterns = [
    path('questionnaire_choices/', QuestionnaireChoicesListView.as_view(), name='questionnaire_choices'),
    path('collaboration/', CollaborationCreateView.as_view(), name='collaboration')
]

urlpatterns += router.urls
