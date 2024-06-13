from django.db import migrations


def add_sub_types(apps, schema_editor):
    from datetime import timedelta
    Sub = apps.get_model("payments", "Subscription")
    # PromoCode = apps.get_model("payments", "PromoCode")

    sub_obj = [
        Sub(
            name='Лайт',
            cost=12000,
            duration=timedelta(days=365),
        ),
        Sub(
            name='Комфорт',
            cost=24000,
            duration=timedelta(days=365),
        ),
        Sub(
            name='Бизнес',
            cost=60000,
            duration=timedelta(days=365),
        ),
    ]
    for sub in sub_obj:
        sub.save()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('payments', '0002_promocode'),
    ]

    operations = [
        migrations.RunPython(add_sub_types),
    ]
