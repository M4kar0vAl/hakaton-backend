from django import forms


class BlackListAdminForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()

        initiator = cleaned_data.get('initiator')  # Brand instance
        blocked = cleaned_data.get('blocked')  # Brand instance

        if initiator.id == blocked.id:
            raise forms.ValidationError('User cannot block himself')

        if initiator.blacklist_as_initiator.filter(blocked=blocked).exists():
            raise forms.ValidationError(f'{initiator} have already blocked this brand.')

        return cleaned_data
