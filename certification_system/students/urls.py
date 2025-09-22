from django.urls import path
from . import views

urlpatterns = [
    path('', views.StudentListView.as_view(), name='student_list'),
    path('create/', views.StudentCreateView.as_view(), name='student_create'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('import/', views.import_students, name='student_import'),
    path('export/', views.export_students, name='student_export'),
    path('<int:student_id>/send-certificate/', views.send_certificate, name='send_certificate'),
    path('<int:student_id>/download-certificate/', views.download_certificate, name='download_certificate'),
    path('<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/bulk-delete/', views.bulk_delete_students, name='bulk_delete_students'),
    path('students/bulk-send/', views.bulk_send_certificates, name='bulk_send_certificates'),
    path('students/register/', views.StudentSelfRegisterView.as_view(), name='student_self_register'),
    path('mt/<int:pk>', views.mt, name='mt'),
]