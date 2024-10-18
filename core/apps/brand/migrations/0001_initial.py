# Generated by Django 5.0.6 on 2024-10-17 11:11

import core.apps.brand.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('chat', '0001_initial'),
        ('payments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Age',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('men', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Мужчины')),
                ('women', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Женщины')),
            ],
            options={
                'verbose_name': 'Возраст',
                'verbose_name_plural': 'Возрасты',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Категория')),
                ('is_other', models.BooleanField(default=False, verbose_name='Другое')),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Категории',
            },
        ),
        migrations.CreateModel(
            name='Format',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Формат')),
                ('is_other', models.BooleanField(default=False, verbose_name='Другое')),
            ],
            options={
                'verbose_name': 'Формат',
                'verbose_name_plural': 'Форматы',
            },
        ),
        migrations.CreateModel(
            name='Gender',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('men', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='% мужчин')),
                ('women', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='% женщин')),
            ],
            options={
                'verbose_name': 'Пол',
                'verbose_name_plural': 'Пол',
            },
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Бизнес задача')),
                ('is_other', models.BooleanField(default=False, verbose_name='Другое')),
            ],
            options={
                'verbose_name': 'Бизнес задача',
                'verbose_name_plural': 'Бизнес задачи',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Тег')),
                ('is_other', models.BooleanField(default=False, verbose_name='Другое')),
            ],
            options={
                'verbose_name': 'Тег',
                'verbose_name_plural': 'Теги',
            },
        ),
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('published', models.BooleanField(default=False, verbose_name='Опубликовано')),
                ('sub_expire', models.DateField(null=True, verbose_name='Окончание подписки')),
                ('tg_nickname', models.CharField(blank=True, max_length=64, verbose_name='Ник в телеграме')),
                ('blog_url', models.URLField(blank=True, verbose_name='Блог бренда')),
                ('name', models.CharField(max_length=256, verbose_name='Название бренда')),
                ('position', models.CharField(max_length=256, verbose_name='Должность')),
                ('inst_url', models.URLField(blank=True, verbose_name='Бренд в Instagram')),
                ('vk_url', models.URLField(blank=True, verbose_name='Бренд в ВК')),
                ('tg_url', models.URLField(blank=True, verbose_name='Бренд в Telegram')),
                ('wb_url', models.URLField(blank=True, verbose_name='Магазин в ВБ')),
                ('lamoda_url', models.URLField(blank=True, verbose_name='Магазин в Lamoda')),
                ('site_url', models.URLField(blank=True, verbose_name='Сайт бренда')),
                ('subs_count', models.PositiveIntegerField(verbose_name='Кол-во подписчиков')),
                ('avg_bill', models.PositiveIntegerField(verbose_name='Средний чек')),
                ('uniqueness', models.CharField(max_length=512, verbose_name='Уникальность бренда')),
                ('logo', models.ImageField(upload_to=core.apps.brand.models.user_directory_path, verbose_name='Лого')),
                ('photo', models.ImageField(upload_to=core.apps.brand.models.user_directory_path, verbose_name='Фото представителя')),
                ('description', models.CharField(blank=True, max_length=512, verbose_name='Описание бренда')),
                ('mission_statement', models.CharField(blank=True, max_length=512, verbose_name='Миссия бренда')),
                ('offline_space', models.CharField(blank=True, max_length=512, verbose_name='Оффлайн пространство')),
                ('problem_solving', models.CharField(blank=True, max_length=512, verbose_name='Какую проблему решает')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='brands', to='payments.subscription', verbose_name='Тариф')),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('categories_of_interest', models.ManyToManyField(blank=True, related_name='brands_as_interest', to='brand.category', verbose_name='Интересующие категории')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='brands', to='brand.category', verbose_name='Категория')),
                ('formats', models.ManyToManyField(blank=True, related_name='brands', to='brand.format', verbose_name='Форматы коллабораций')),
                ('goals', models.ManyToManyField(blank=True, related_name='brands', to='brand.goal', verbose_name='Бизнес задачи')),
                ('tags', models.ManyToManyField(related_name='brands', to='brand.tag', verbose_name='Ценности')),
            ],
            options={
                'verbose_name': 'Бренд',
                'verbose_name_plural': 'Бренды',
            },
        ),
        migrations.CreateModel(
            name='BusinessGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название или ссылка')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_groups', to='brand.brand', verbose_name='Бренд')),
            ],
        ),
        migrations.CreateModel(
            name='GalleryPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=core.apps.brand.models.gallery_path, verbose_name='Фото')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gallery_photos', to='brand.brand', verbose_name='Бренд')),
            ],
            options={
                'verbose_name': 'Фото для галереи',
                'verbose_name_plural': 'Фото для галереи',
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_match', models.BooleanField(default=False, verbose_name='Метч')),
                ('initiator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='initiator', to='brand.brand', verbose_name='Кто лайкнул')),
                ('room', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.room')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='target', to='brand.brand', verbose_name='Кого лайкнули')),
            ],
        ),
        migrations.CreateModel(
            name='ProductPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('format', models.CharField(choices=[('M', 'Для метча'), ('C', 'Для карточки бренда')], max_length=1, verbose_name='Формат изображения')),
                ('image', models.ImageField(upload_to=core.apps.brand.models.product_photo_path, verbose_name='Фото')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_photos', to='brand.brand', verbose_name='Бренд')),
            ],
            options={
                'verbose_name': 'Фото продукта',
                'verbose_name_plural': 'Фото продукта',
            },
        ),
        migrations.CreateModel(
            name='TargetAudience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('income', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(50000), django.core.validators.MaxValueValidator(1000000)], verbose_name='Доход')),
                ('age', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='target_audience', to='brand.age', verbose_name='Возраст')),
                ('gender', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='target_audience', to='brand.gender', verbose_name='Пол')),
            ],
            options={
                'verbose_name': 'Целевая аудитория',
                'verbose_name_plural': 'Целевая аудитория',
            },
        ),
        migrations.CreateModel(
            name='GEO',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=256, verbose_name='Город')),
                ('people_percentage', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Процент людей')),
                ('target_audience', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='geos', to='brand.targetaudience', verbose_name='Целевая аудитория')),
            ],
            options={
                'verbose_name': 'ГЕО',
                'verbose_name_plural': 'ГЕО',
            },
        ),
        migrations.AddField(
            model_name='brand',
            name='target_audience',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='brand.targetaudience', verbose_name='Целевая аудитория'),
        ),
    ]
