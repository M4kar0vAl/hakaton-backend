# Generated by Django 5.0.6 on 2024-09-08 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_fake_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordRecovery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('token', models.CharField()),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
