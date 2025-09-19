from django.db import models
from students.models import Student

class EmailReport(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    last_retry = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student.certificate_id} - {self.status}"