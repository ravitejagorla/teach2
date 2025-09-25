from django.contrib import admin
from .models import CertificateTemplate

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'specialization',
        'organization',
        'course',
        'template_type',
        'is_active',
        'created_at',
    )
    list_filter = ('organization', 'course', 'template_type', 'is_active')
    search_fields = ('name', 'specialization', 'organization', 'course')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} template(s) marked as active.")
    make_active.short_description = "Mark selected templates as active"

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} template(s) marked as inactive.")
    make_inactive.short_description = "Mark selected templates as inactive"
