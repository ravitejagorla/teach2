from django.db import models
from templates_app.models import CertificateTemplate

class Student(models.Model):
    certificate_id = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=15, blank=True, null=True)
    specialization = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    course = models.CharField(max_length=225)
    institution = models.CharField(max_length=255, default="Quality Thought Institution")
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    template = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    certificate_generated = models.BooleanField(default=False)  # Add this field
    
    def __str__(self):
        return f"{self.full_name} ({self.certificate_id})"
    
    def save(self, *args, **kwargs):
        if not self.certificate_id:
            last_student = Student.objects.order_by('-id').first()
            if last_student and last_student.certificate_id:
                try:
                    last_id = int(last_student.certificate_id.split('202500')[-1])
                except (ValueError, IndexError):
                    last_id = 0
            else:
                last_id = 0
            self.certificate_id = f"202500{last_id + 1:04d}"
        
        # Auto-assign template based on specialization and organization
        if not self.template:
            matching_template = CertificateTemplate.objects.filter(
                specialization__iexact=self.specialization.strip(),
                organization__iexact=self.organization.strip(),
                course__iexact=self.course.strip(),
                is_active=True
            ).first()
            
            if matching_template:
                self.template = matching_template
        
        super().save(*args, **kwargs)
    
    def has_template(self):
        """Check if student has a valid template assigned"""
        return self.template is not None and self.template.is_active


