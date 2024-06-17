from django.db.models import Prefetch
from rest_framework import viewsets, mixins

from .models import Question, AnswerChoice
from .serializers import QuestionSerializer


class QuestionViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_queryset(self):
        queryset = Question.objects.prefetch_related(
            Prefetch(
                'answer_variable',
                queryset=AnswerChoice.objects.order_by('index')
            )
        ).filter(published=True).order_by('index')
        return queryset
