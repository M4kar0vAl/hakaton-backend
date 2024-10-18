# Generated by Django 5.0.6 on 2024-10-17 11:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('brand', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('R', 'Registration'), ('D', 'Deletion'), ('P', 'Payment')], max_length=1, verbose_name='Действие')),
                ('performed_at', models.DateTimeField(auto_now_add=True, verbose_name='Выполнено')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='activity', to='brand.brand', verbose_name='Бренд')),
            ],
        ),
        migrations.CreateModel(
            name='MatchActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_match', models.BooleanField(verbose_name='Метч')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('initiator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='activity_as_initiator', to='brand.brand', verbose_name='Кто лайкнул')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='activity_as_target', to='brand.brand', verbose_name='Кого лайкнули')),
            ],
        ),
    ]
