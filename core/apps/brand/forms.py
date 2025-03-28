from django import forms

from core.apps.brand.models import Match


class MatchAdminForm(forms.ModelForm):

    def clean(self):
        initiator = self.cleaned_data.get('initiator')
        target = self.cleaned_data.get('target')

        if 'initiator' in self.changed_data or 'target' in self.changed_data:
            if initiator == target:
                raise forms.ValidationError('Brands cannot "like" themselves')

            try:
                # check if this brand have already performed that same 'like' action
                match = Match.objects.get(initiator=initiator, target=target)
                if match.is_match:
                    raise forms.ValidationError(
                        f"{initiator} already have 'match' with {target}!")
                raise forms.ValidationError(f"{initiator} have already 'liked' {target}!")
            except Match.DoesNotExist:
                # at this point it means that there is no entry in db with that initiator and target,
                # BUT there may be a reverse entry, which is checked further
                pass

            try:
                # check if there is match
                match = Match.objects.get(initiator=target, target=initiator)
            except Match.DoesNotExist:
                match = None

            if match is not None and match.is_match:
                # if is_match = True already, then raise an exception
                raise forms.ValidationError(f"{initiator} already have 'match' with {target}!")
