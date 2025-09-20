from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportListView.as_view(), name='report_list'),
    path('success/', views.ReportListView.as_view(), {'status': 'success'}, name='report_success'),
    path('failed/', views.ReportListView.as_view(), {'status': 'failed'}, name='report_failed'),

    # Action URLs
    path('<int:pk>/delete/', views.report_delete, name='report_delete'),
    path('<int:pk>/resend/', views.report_resend, name='report_resend'),
    path('<int:pk>/download/', views.report_download, name='report_download'),
]