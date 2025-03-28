from django import forms
from django.db.models import Q

from core.apps.brand.models import Match, Collaboration


class BrandAdminForm(forms.ModelForm):
    class Meta:
        widgets = {
            'uniqueness': forms.Textarea,
            'mission_statement': forms.Textarea,
            'offline_space': forms.Textarea,
            'problem_solving': forms.Textarea,
        }


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


class CollaborationAdminForm(forms.ModelForm):

    class Meta:
        widgets = {
            'success_reason': forms.Textarea,
            'to_improve': forms.Textarea,
            'new_offers_comment': forms.Textarea,
            'difficulties_comment': forms.Textarea,
        }

    def clean(self):
        reporter = self.cleaned_data.get('reporter')
        collab_with = self.cleaned_data.get('collab_with')

        if 'reporter' in self.changed_data or 'collab_with' in self.changed_data:
            if Collaboration.objects.filter(reporter=reporter, collab_with=collab_with).exists():
                raise forms.ValidationError(f"{reporter} has already reported collaboration with {collab_with}!")

            # only one match is expected to exist for two brands
            match = Match.objects.filter(
                Q(initiator=reporter, target=collab_with) |
                Q(initiator=collab_with, target=reporter),
                is_match=True
            )

            if not match:
                raise forms.ValidationError(f'Match for selected brands was not found!')

            if len(match) > 1:
                raise forms.ValidationError(
                    f'More than one match was found. You must resolve this issue! Found IDs: {[m.id for m in match]}'
                )
