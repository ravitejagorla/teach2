from import_export import resources
from import_export.fields import Field
from .models import Student

class StudentResource(resources.ModelResource):
    certificate_id = Field(attribute='certificate_id', column_name='Certificate ID')
    full_name = Field(attribute='full_name', column_name='Full Name')
    email = Field(attribute='email', column_name='Email')
    specialization = Field(attribute='specialization', column_name='Specialization')
    organization = Field(attribute='organization', column_name='Organization')
    institution = Field(attribute='institution', column_name='Institution')
    start_date = Field(attribute='start_date', column_name='Start Date')
    end_date = Field(attribute='end_date', column_name='End Date')
    
    class Meta:
        model = Student
        fields = ('certificate_id', 'full_name', 'email', 'specialization', 'organization', 'institution', 'start_date', 'end_date')
        export_order = fields