from django import forms
from django.utils import timezone


class GiftPromoCodeAdminForm(forms.ModelForm):

    def clean_tariff(self):
        tariff = self.cleaned_data.get('tariff')

        if tariff.name == 'Trial':
            raise forms.ValidationError('Trial tariff cannot be given!')

        return tariff


class SubscriptionAdminForm(forms.ModelForm):

    def clean(self):
        brand = self.cleaned_data.get('brand')
        tariff = self.cleaned_data.get('tariff')
        promocode = self.cleaned_data.get('promocode')
        gift_promocode = self.cleaned_data.get('gift_promocode')
        upgraded_from = self.cleaned_data.get('upgraded_from')
        upgraded_at = self.cleaned_data.get('upgraded_at')

        if promocode:
            # check that promo code wasn't used when purchasing subscription
            if brand.subscriptions.filter(promocode=promocode).exists():
                raise forms.ValidationError(f'{brand} has already used this promocode!')

            # check that promo code wasn't used when purchasing a gift
            if brand.gifts_as_giver.filter(promocode=promocode).exists():
                raise forms.ValidationError(f'{brand} has already used this promocode!')

        if gift_promocode:
            if gift_promocode.is_used:
                raise forms.ValidationError(f'{gift_promocode} already_used!')

            if gift_promocode.giver == brand:
                raise forms.ValidationError(f'{brand} cannot use own gift!')

            if gift_promocode.tariff != tariff:
                raise forms.ValidationError(
                    f'If gift promocode is specified, you need to select its tariff! '
                    f'Selected gift promocode tariff: {gift_promocode.tariff}'
                )

        if upgraded_from or upgraded_at:
            subscription = brand.subscriptions.filter(
                is_active=True, end_date__gt=timezone.now()
            ).order_by('-id').select_related('tariff').first()

            # upgrade section should only be available if brand already has active subscription
            if not subscription:
                raise forms.ValidationError(f'Brand must have active subscription to upgrade tariff!')

            cur_tariff = subscription.tariff

            # if current active tariff and selected as "upgraded_from" do not match
            if upgraded_from != cur_tariff:
                raise forms.ValidationError(
                    f'"Upgraded from" must be current tariff. {brand} now has {cur_tariff} tariff active!'
                )
