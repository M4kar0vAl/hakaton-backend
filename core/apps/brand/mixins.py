from rest_framework import serializers

from core.apps.brand.models import Category


class BrandValidateMixin:
    def validate_category(self, category):
        if 'is_other' in category:
            if category['is_other']:
                # user selected "other" variant, so create category with given name
                category_obj = Category.objects.create(**category)
            else:
                try:
                    # user selected one of the given categories, so get instance from db
                    category_obj = Category.objects.get(**category)
                except Category.DoesNotExist:
                    raise serializers.ValidationError(
                        {"category": f"Category with name: {category['name']} does not exist!"}
                    )
        else:
            try:
                # is_other wasn't passed, so get instance from db
                category_obj = Category.objects.get(**category)
            except Category.DoesNotExist:
                raise serializers.ValidationError(
                    {"category": f"Category with name: {category['name']} does not exist!"})

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
