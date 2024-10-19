# Generated by Django 5.0.6 on 2024-10-19 12:11

import datetime

from django.contrib.auth import get_user_model
from django.db import migrations


def add_users(apps, schema_editor):
    User = get_user_model()

    staff_users = User.objects.bulk_create([
        User(
            email='staff@example.com',
            phone='+79998884422',
            fullname='Стаффов Стафф Стаффович',
            date_joined=datetime.datetime.now(),
            is_active=True,
            is_staff=True,
        ),
        User(
            email='admin@example.com',
            phone='+79993332211',
            fullname='Админов Админ Админович',
            date_joined=datetime.datetime.now(),
            is_active=True,
            is_staff=True,
        )
    ])
    for user in staff_users:
        user.set_password('Pass!234')
        user.save()


def delete_users(apps, schema_editor):
    User = get_user_model()

    User.objects.filter(email__in=['staff@example.com', 'admin@example.com']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_users, delete_users)
    ]
