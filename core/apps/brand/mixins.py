import re

from rest_framework import serializers

from core.apps.brand.models import Category


class BrandValidateMixin:
    def validate_tg_nickname(self, tg_nickname):
        # telegram username need to be 5-32 characters long
        # and only consist of Latin letters, digits and underscores
        if not re.fullmatch(r'@[a-zA-Z\d_]{5,32}', tg_nickname):
            raise serializers.ValidationError(
                'Username must be 5-32 characters long. '
                'Allowed characters: Latin letters, digits and underscores'
            )
        return tg_nickname

    def validate_category(self, category):
        if not category:
            raise serializers.ValidationError('Category is required!')

        if 'name' not in category:
            raise serializers.ValidationError('Category must have "name" key!')

        if 'is_other' in category:
            if category['is_other']:
                # user selected "other" variant, so create category with given name
                category_obj = Category.objects.create(**category)
            else:
                try:
                    # user selected one of the given categories, so get instance from db
                    category_obj = Category.objects.get(**category)
                except Category.DoesNotExist:
                    raise serializers.ValidationError(f"Category with name: {category['name']} does not exist!")
        else:
            try:
                # is_other wasn't passed, so get instance from db
                category_obj = Category.objects.get(**category)
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"Category with name: {category['name']} does not exist!")

        return category_obj

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError('Tags are required!')

        common_num = 0
        other_num = 0

        for tag in tags:
            if 'is_other' not in tag or not tag['is_other']:
                common_num += 1
                if common_num > 5:
                    raise serializers.ValidationError('You can only specify 5 or less "common" tags')
            elif 'is_other' in tag and tag['is_other']:
                other_num += 1
                if other_num > 1:
                    raise serializers.ValidationError('You can only specify no more than 1 "other" tag')

        return tags

    def validate_formats(self, formats):
        other_num = 0

        for format_ in formats:
            if 'is_other' in format_ and format_['is_other']:
                other_num += 1
                if other_num > 1:
                    raise serializers.ValidationError('You can only specify no more than 1 "other" format')

        return formats

    def validate_goals(self, goals):
        other_num = 0

        for goal in goals:
            if 'is_other' in goal and goal['is_other']:
                other_num += 1
                if other_num > 1:
                    raise serializers.ValidationError('You can only specify no more than 1 "other" goal')

        return goals

    def validate_categories_of_interest(self, categories):
        other_num = 0

        for cat in categories:
            if 'is_other' in cat and cat['is_other']:
                other_num += 1
                if other_num > 1:
                    raise serializers.ValidationError('You can only specify no more than 1 "other" category')

        return categories
