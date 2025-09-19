from django.urls import path
from . import views

app_name = "templates_app"

urlpatterns = [
    path('', views.TemplateListView.as_view(), name='template_list'),
    path('create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('<int:pk>/update/', views.TemplateUpdateView.as_view(), name='template_update'),
    path('<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('<int:pk>/detail/', views.TemplateDetailView.as_view(), name='template_detail'),
]
