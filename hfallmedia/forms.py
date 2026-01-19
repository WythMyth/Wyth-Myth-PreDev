from django import forms
from .models import ContactUs, HeroVideo

class HeroVideoForm(forms.ModelForm):
    class Meta:
        model = HeroVideo
        fields = ['title', 'video', 'video_url']

        widgets = {
            'title': forms.TextInput(),
            'video': forms.FileInput(),
            'video_url': forms.URLInput(),
        }

class ContactUsForm(forms.ModelForm):

    class Meta:
        model = ContactUs
        fields = [
            "name",
            "email",
            "subject",
            "message",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter your full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Enter your email"}),
            "subject": forms.TextInput(attrs={"placeholder": "Enter subject name"}),
            "message": forms.Textarea(attrs={"placeholder": "Please add details or message..."}),
        }