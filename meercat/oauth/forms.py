from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(label='GitHub account email', max_length=200)
    message = forms.CharField()

    #set field attributes
    name.widget = forms.TextInput(attrs={'class': 'form-control'})
    email.widget = forms.EmailInput(attrs={'class': 'form-control'})
    message.widget = forms.Textarea(
        attrs={
            'class': 'form-control',
            'placeholder': 'Please tell us which repositories you would like to join, and your role in them.'
        }
    )

    #Unique email constraint
    def clean_email(self):
        email = self.cleaned_data['email']
    
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered")
    
        return email