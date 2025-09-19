from django.views.generic import ListView
from .models import EmailReport

class ReportListView(ListView):
    model = EmailReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 10
    
    def get_queryset(self):
        status = self.kwargs.get('status')
        if status:
            return EmailReport.objects.filter(status=status)
        return EmailReport.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.kwargs.get('status', 'all')
        context['success_count'] = EmailReport.objects.filter(status='success').count()
        context['failed_count'] = EmailReport.objects.filter(status='failed').count()
        context['total_count'] = EmailReport.objects.count()
        return context