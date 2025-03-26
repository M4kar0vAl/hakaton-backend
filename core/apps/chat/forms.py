from django import forms


class MessageAdminForm(forms.ModelForm):

    def clean(self):
        user = self.cleaned_data.get('user')
        room = self.cleaned_data.get('room')

        if not user or not room:
            return

        if not user.is_superuser and not user.is_staff and not user.rooms.filter(pk=room.pk).exists():
            raise forms.ValidationError(f'Selected user is not a participant of {room}')
