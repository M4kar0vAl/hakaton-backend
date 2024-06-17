from rest_framework import serializers

from .models import Question, AnswerChoice


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = [
            'id',
            'text',
        ]


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True, source='answer_variable')

    class Meta:
        model = Question
        fields = [
            'id',
            'text',
            'answer_type',
            'choices',
        ]
