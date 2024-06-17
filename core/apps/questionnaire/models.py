from django.db import models


class Question(models.Model):
    TYPES = (
        ('TEXT', 'Текстовый ввод'),
        ('ONE', 'Единственный выбор'),
        ('MANY', 'Множественный выбор'),
        ('IMAGE', 'Загрузка изображения')
    )
    published = models.BooleanField()
    text = models.CharField(max_length=256)
    answer_type = models.CharField(max_length=16, choices=TYPES)
    index = models.PositiveIntegerField('Порядковый номер')

    class Meta:
        verbose_name = 'Вопрос анкеты'
        verbose_name_plural = 'Вопросы анкеты'

    def __repr__(self):
        return f'{self.text}'


class AnswerChoice(models.Model):
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answer_variable'
    )
    index = models.PositiveIntegerField('Порядковый номер')

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __repr__(self):
        return f'{self.text}'
