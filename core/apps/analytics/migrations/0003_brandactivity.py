# Generated by Django 5.0.6 on 2024-09-09 13:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_alter_matchactivity_initiator_and_more'),
        ('brand', '0017_alter_avgbill_brand_alter_category_brand_and_more'),
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
    ]
