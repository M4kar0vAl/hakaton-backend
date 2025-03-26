from django import forms

from core.apps.chat.models import RoomFavorites


class MessageAdminForm(forms.ModelForm):

    def clean(self):
        user = self.cleaned_data.get('user')
        room = self.cleaned_data.get('room')

        if not user or not room:
            return

        if not user.is_superuser and not user.is_staff and not user.rooms.filter(pk=room.pk).exists():
            raise forms.ValidationError(f'Selected user is not a participant of {room}')


class RoomFavoritesAdminForm(forms.ModelForm):

    def clean(self):
        user = self.cleaned_data.get('user')
        room = self.cleaned_data.get('room')

        if not user or not room:
            return

        if RoomFavorites.objects.filter(user=user, room=room).exists():
            raise forms.ValidationError(f'{user} has already added {room} to favorites!')

        # admins and staff can add any room to favorites
        if user.is_superuser or user.is_staff:
            return

        # users can add only rooms they are participants of
        if not user.rooms.filter(pk=room.pk).exists():
            raise forms.ValidationError(f'Selected user is not a participant of {room}')
