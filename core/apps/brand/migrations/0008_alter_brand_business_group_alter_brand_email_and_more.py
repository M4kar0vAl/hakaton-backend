# Generated by Django 5.0.6 on 2024-06-16 19:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brand', '0007_remove_brand_formats_remove_brand_goal_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brand',
            name='business_group',
            field=models.CharField(max_length=512, verbose_name='Сообщество предпринимателей'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Эл. почта'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='fullname',
            field=models.CharField(max_length=512, verbose_name='Фамилия и имя'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='mission_statement',
            field=models.CharField(max_length=512, verbose_name='Миссия бренда'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='phone',
            field=models.CharField(max_length=12, verbose_name='Номер телефона'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='problem_solving',
            field=models.CharField(max_length=512, verbose_name='Какую проблему решает'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='product_description',
            field=models.CharField(max_length=512, verbose_name='Описание продукта'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='unique_product_is',
            field=models.CharField(max_length=512, verbose_name='Уникальность продукта'),
        ),
    ]
