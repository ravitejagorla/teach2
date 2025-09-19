from django.db import models

class CertificateTemplate(models.Model):
    ORIENTATION_CHOICES = (
        ('landscape', 'Landscape'),
        ('portrait', 'Portrait'),
    )
    
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    course = models.CharField(max_length=255)
    template_type = models.CharField(max_length=10, choices=ORIENTATION_CHOICES, default='landscape')
    template_file = models.FileField(upload_to='certificate_templates/')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name