from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

class ProfileCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Profile
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number', 'location')

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['location', 'phone_number']
