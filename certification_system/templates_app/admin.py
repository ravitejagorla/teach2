from django.contrib import admin
from .models import CertificateTemplate, Asset

# Inline for Asset so it shows up within CertificateTemplate
class AssetInline(admin.TabularInline):
    model = Asset
    extra = 1  # Number of extra blank forms
    fields = ('logo', 'signature', 'stamp')

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'organization', 'course', 'template_type', 'created_at', 'is_active')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('name', 'specialization', 'organization', 'course')
    inlines = [AssetInline]

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('institute','font', 'logo', 'signature', 'stamp')
    list_filter = ('institute',)
    search_fields = ('institute__name',)