from django.forms import ModelForm

from database.models import SupportSubmission

class SupportSubmissionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supportType'].widget.attrs.update({'class': 'form-control'})
        self.fields['feature'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['image'].widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = SupportSubmission
        exclude = ('user', 'datetime')