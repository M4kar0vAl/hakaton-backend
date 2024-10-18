# Generated by Django 5.0.6 on 2024-10-17 11:49

from django.db import migrations


def add_formats(apps, schema_editor):
    Format = apps.get_model('brand', 'Format')

    formats = [
        Format(name='Продукт'),
        Format(name='Контент в соцсетях'),
        Format(name='Мероприятие'),
        Format(name='Кросс промо'),
    ]

    Format.objects.bulk_create(formats)


def delete_formats(apps, schema_editor):
    Format = apps.get_model('brand', 'Format')

    Format.objects.filter(is_other=False, name__in=[
        'Продукт',
        'Контент в соцсетях',
        'Мероприятие',
        'Кросс промо',
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('brand', '0003_categories'),
    ]

    operations = [
        migrations.RunPython(add_formats, delete_formats)
    ]
