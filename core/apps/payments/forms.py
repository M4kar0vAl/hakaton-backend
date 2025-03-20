from django import forms


class GiftPromoCodeAdminForm(forms.ModelForm):

    def clean(self):
        giver = self.cleaned_data.get('giver')
        tariff = self.cleaned_data.get('tariff')
        promocode = self.cleaned_data.get('promocode')

        if tariff.name == 'Trial':
            raise forms.ValidationError('Trial tariff cannot be given!')

        if promocode is not None:
            # check that promo code wasn't used when purchasing subscription
            if giver.subscriptions.filter(promocode=promocode).exists():
                raise forms.ValidationError(f'{giver} has already used this promocode!')

            # check that promo code wasn't used when purchasing a gift
            if giver.gifts_as_giver.filter(promocode=promocode).exists():
                raise forms.ValidationError(f'{giver} has already used this promocode!')
