from django.db import models
import random
from django.utils import timezone
from templates_app.models import CertificateTemplate

def generate_certification_id():
    today = timezone.now().strftime("%Y%m%d")
    random_hex = ''.join(random.choices("0123456789ABCDEF", k=4))
    return f"{today}{random_hex}"

class Student(models.Model):
    certificate_id = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=15, blank=True, null=True)
    specialization = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    course = models.CharField(max_length=225)
    institution = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    template = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    certificate_generated = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.full_name} ({self.certificate_id})"
    
    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = generate_certification_id()

        # Assign template automatically if not already set
        if not self.template:
            matching_template = CertificateTemplate.objects.filter(
                organization__iexact=self.organization.strip(),
                name__iexact=self.institution.strip(),
                is_active=True
            ).first()

            if matching_template:
                self.template = matching_template

        super().save(*args, **kwargs)

    
    def has_template(self):
        """Check if student has a valid template assigned"""
        return self.template is not None and self.template.is_active


