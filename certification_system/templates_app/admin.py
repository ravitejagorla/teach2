from django.contrib import admin
from .models import CertificateTemplate

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'organization', 'template_type', 'is_active', 'created_at')
    list_filter = ('template_type', 'is_active', 'organization')
    search_fields = ('name', 'specialization', 'organization')
    ordering = ('-created_at',)
