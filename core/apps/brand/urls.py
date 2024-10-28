from django.urls import path
from rest_framework import routers

from core.apps.brand.api import BrandViewSet, QuestionnaireChoicesListView

router = routers.DefaultRouter()
router.register('brand', BrandViewSet, basename='brand')

urlpatterns = [
    path('questionnaire_choices/', QuestionnaireChoicesListView.as_view(), name='questionnaire_choices')
]

urlpatterns += router.urls
