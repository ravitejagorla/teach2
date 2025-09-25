from django.contrib import admin
from .models import Student
from templates_app.models import CertificateTemplate

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'certificate_id',
        'email',
        'mobile',
        'specialization',
        'organization',
        'course',
        'institution',
        'start_date',
        'end_date',
        'certificate_generated',
        'template',
    )
    list_filter = ('organization', 'course', 'certificate_generated', 'template')
    search_fields = ('full_name', 'email', 'certificate_id', 'organization', 'institution')
    readonly_fields = ('certificate_id', 'created_at', 'updated_at')
    autocomplete_fields = ('template',)
    ordering = ('-created_at',)

    def has_template_status(self, obj):
        return obj.has_template()
    has_template_status.boolean = True
    has_template_status.short_description = 'Has Template?'

