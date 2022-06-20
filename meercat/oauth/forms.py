from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(label='GitHub account email', max_length=200)
    message = forms.CharField()
    username = forms.CharField(max_length=100)
    personal_email = forms.EmailField(label='Personal email', max_length=200, required=False)

    #set field attributes
    name.widget = forms.TextInput(attrs={'class': 'form-control'})
    email.widget = forms.EmailInput(attrs={'class': 'form-control'})
    message.widget = forms.Textarea(
        attrs={
            'class': 'form-control',
            'placeholder': 'Please tell us about your interest in MeerCAT.'
        }
    )
    username.widget = forms.TextInput(attrs={'class': 'form-control'})
    personal_email.widget = forms.EmailInput(attrs={'class': 'form-control'})

    #Unique email constraint
    def clean_email(self):
        email = self.cleaned_data['email']
    
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered")
    
        return email