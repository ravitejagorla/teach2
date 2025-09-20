import os
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, HttpResponse
from django.views.generic import ListView
from django.core.mail import EmailMessage
from django.conf import settings
from .models import EmailReport

# ------------------ List View ------------------

class ReportListView(ListView):
    model = EmailReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 10

    def get_queryset(self):
        status = self.kwargs.get('status')
        qs = EmailReport.objects.all()
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-sent_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.kwargs.get('status', 'all')
        context['success_count'] = EmailReport.objects.filter(status='success').count()
        context['failed_count'] = EmailReport.objects.filter(status='failed').count()
        context['total_count'] = EmailReport.objects.all().count()
        return context

# ------------------ Action Views ------------------

def report_delete(request, pk):
    """Delete a report."""
    report = get_object_or_404(EmailReport, pk=pk)
    report.delete()
    return redirect('report_list')


def report_resend(request, pk):
    """Resend the certificate email for a given report."""
    report = get_object_or_404(EmailReport, pk=pk)
    student = report.student

    # Build the certificate file path
    safe_name = student.full_name.replace(' ', '_')
    certificate_file_path = os.path.join(
        settings.MEDIA_ROOT,
        'certificates',
        f"{student.certificate_id}_{safe_name}.pdf"
    )

    # Check if the file exists
    if not os.path.exists(certificate_file_path):
        return HttpResponse("Certificate file not found. Cannot resend email.", status=404)

    # Prepare email
    email_subject = "Your Certificate"
    email_body = f"Hello {student.full_name},\n\nPlease find your certificate attached."
    email = EmailMessage(
        email_subject,
        email_body,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
    )

    # Attach the certificate
    email.attach_file(certificate_file_path)

    # Send the email
    try:
        email.send(fail_silently=False)
        report.status = 'success'
        report.retry_count += 1
        report.save()
    except Exception as e:
        report.status = 'failed'
        report.retry_count += 1
        report.save()
        return HttpResponse(f"Failed to resend email: {e}", status=500)

    return redirect('report_list')


def report_download(request, pk):
    """Download the certificate PDF for a given report."""
    report = get_object_or_404(EmailReport, pk=pk)
    student = report.student

    safe_name = student.full_name.replace(' ', '_')
    certificate_file_path = os.path.join(
        settings.MEDIA_ROOT,
        'certificates',
        f"{student.certificate_id}_{safe_name}.pdf"
    )

    if not os.path.exists(certificate_file_path):
        return HttpResponse("Certificate file not found.", status=404)

    return FileResponse(
        open(certificate_file_path, 'rb'),
        as_attachment=True,
        filename=f"{student.certificate_id}_{safe_name}.pdf"
    )