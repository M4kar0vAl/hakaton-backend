# Generated by Django 5.0.6 on 2024-06-13 16:48

from django.db import migrations, models


def add_promo_codes(apps, schema_editor):
    PromoCode = apps.get_model("payments", "PromoCode")
    promo_codes = [
        PromoCode(
            code='discount10',
            discount=10
        ),
        PromoCode(
            code='discount5',
            discount=5
        )
    ]
    for code in promo_codes:
        code.save()


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=30, verbose_name='Промокод')),
                ('discount', models.IntegerField()),
            ],
        ),
        migrations.RunPython(add_promo_codes),
    ]
