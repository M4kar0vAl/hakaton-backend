from django import forms
from django.utils import timezone


class GiftPromoCodeAdminForm(forms.ModelForm):

    def clean(self):
        giver = self.cleaned_data.get('giver')

        if 'promocode' in self.changed_data:
            promocode = self.cleaned_data.get('promocode')

            if promocode and promocode.is_used_by_brand(giver):
                raise forms.ValidationError(f'{giver} has already used this promocode!')

    def clean_tariff(self):
        tariff = self.cleaned_data.get('tariff')

        if tariff.name == 'Trial':
            raise forms.ValidationError('Trial tariff cannot be given!')

        return tariff


class SubscriptionAdminForm(forms.ModelForm):

    def clean(self):
        brand = self.cleaned_data.get('brand')
        tariff = self.cleaned_data.get('tariff')
        gift_promocode = self.cleaned_data.get('gift_promocode')
        upgraded_from = self.cleaned_data.get('upgraded_from')
        upgraded_at = self.cleaned_data.get('upgraded_at')

        if 'promocode' in self.changed_data:
            promocode = self.cleaned_data.get('promocode')

            if promocode and promocode.is_used_by_brand(brand):
                raise forms.ValidationError(f'{brand} has already used this promocode!')

        if gift_promocode:
            if gift_promocode.giver == brand:
                raise forms.ValidationError(f'{brand} cannot use own gift!')

            if gift_promocode.tariff != tariff:
                raise forms.ValidationError(
                    f'If gift promocode is specified, you need to select its tariff! '
                    f'Selected gift promocode tariff: {gift_promocode.tariff}'
                )

        if upgraded_from or upgraded_at:
            if tariff.name != 'Business Match':
                raise forms.ValidationError(f'Brands can only upgrade to Business Match tariff!')

            subscription = brand.subscriptions.filter(
                is_active=True, end_date__gt=timezone.now()
            ).order_by('-id').select_related('tariff').first()

            # upgrade section should only be available if brand already has active subscription
            if not subscription:
                raise forms.ValidationError(f'Brand must have active subscription to upgrade tariff!')

            cur_tariff = subscription.tariff

            if 'tariff' in self.changed_data and tariff == cur_tariff:
                raise forms.ValidationError(f'Brands cannot upgrade to their current tariff!')

            # if current active tariff and selected as "upgraded_from" do not match
            if upgraded_from != cur_tariff:
                raise forms.ValidationError(
                    f'"Upgraded from" must be current tariff. {brand} now has {cur_tariff} tariff active!'
                )

    def clean_gift_promocode(self):
        gift_promocode = self.cleaned_data.get('gift_promocode')

        if gift_promocode and gift_promocode.is_used:
            raise forms.ValidationError(f'{gift_promocode} already_used!')

        return gift_promocode
