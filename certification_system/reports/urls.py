from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportListView.as_view(), name='report_list'),
    path('success/', views.ReportListView.as_view(), {'status': 'success'}, name='report_success'),
    path('failed/', views.ReportListView.as_view(), {'status': 'failed'}, name='report_failed'),
]