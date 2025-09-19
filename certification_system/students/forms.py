from django import forms
from .models import Student
from templates_app.models import CertificateTemplate


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91XXXXXXXXXX'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fetch distinct values safely with ordering
        orgs = CertificateTemplate.objects.order_by('organization').values_list('organization', flat=True).distinct()
        specs = CertificateTemplate.objects.order_by('specialization').values_list('specialization', flat=True).distinct()
        institutes = CertificateTemplate.objects.order_by('name').values_list('name', flat=True).distinct()

        # Handle optional course field (only if it exists in the model)
        try:
            course = CertificateTemplate.objects.order_by('course').values_list('course', flat=True).distinct()
        except Exception:
            course = []  # fallback if course field doesn't exist

        # Dropdown for Organization
        self.fields['organization'] = forms.ChoiceField(
            choices=[('', 'Select Organization')] + [(o, o) for o in orgs if o],
            required=True
        )

        # Dropdown for Specialization
        self.fields['specialization'] = forms.ChoiceField(
            choices=[('', 'Select Specialization')] + [(s, s) for s in specs if s],
            required=True
        )

        # Dropdown for Institution (using CertificateTemplate.name)
        self.fields['institution'] = forms.ChoiceField(
            choices=[('', 'Select Institution')] + [(i, i) for i in institutes if i],
            required=True
        )

        # Dropdown for Course (only if values exist)
        self.fields['course'] = forms.ChoiceField(
            choices=[('', 'Select Course')] + [(c, c) for c in course if c],
            required=True
        )

        # Apply Bootstrap classes to all remaining fields
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'
                
class ImportCSVForm(forms.Form):
    file = forms.FileField(required=True, label="Select CSV file")