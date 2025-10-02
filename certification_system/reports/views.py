import os
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, HttpResponse
from django.views.generic import TemplateView
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import dns.resolver
from .models import EmailReport


# ------------------ List View ------------------

class ReportListView(TemplateView):
    template_name = 'reports/report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Separate querysets for success and failed reports
        context['success_reports'] = EmailReport.objects.filter(status='success').order_by('-sent_at')
        context['failed_reports'] = EmailReport.objects.filter(status='failed').order_by('-sent_at')

        # Counts
        context['total_count'] = EmailReport.objects.count()
        context['success_count'] = context['success_reports'].count()
        context['failed_count'] = context['failed_reports'].count()

        return context


# ------------------ Action Views ------------------

def report_delete(request, pk):
    """Delete a report."""
    report = get_object_or_404(EmailReport, pk=pk)
    report.delete()
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


def report_resend(request, pk):
    """Resend the certificate email with validation and error handling."""
    report = get_object_or_404(EmailReport, pk=pk)
    student = report.student
    safe_name = student.full_name.replace(' ', '_')
    certificate_file_path = os.path.join(
        settings.MEDIA_ROOT,
        'certificates',
        f"{student.certificate_id}_{safe_name}.pdf"
    )

    # 1️⃣ Check if certificate file exists
    if not os.path.exists(certificate_file_path):
        report.status = 'failed'
        report.error_message = 'Certificate file not found'
        report.retry_count += 1
        report.save()
        return redirect('report_list')

    # 2️⃣ Validate email format   
    try:
        validate_email(student.email)
    except ValidationError:
        report.status = 'failed'
        report.error_message = 'Invalid email address'
        report.retry_count += 1
        report.save()
        return redirect('report_list')

    # 3️⃣ Check domain MX record
    try:
        domain = student.email.split('@')[1]
        dns.resolver.resolve(domain, 'MX')
    except Exception:
        report.status = 'failed'
        report.error_message = f'Domain {domain} not found'
        report.retry_count += 1
        report.save()
        return redirect('report_list')

    # 4️⃣ Prepare email
    email_subject = "Your Certificate"
    email_body = f"Hello {student.full_name},\n\nPlease find your certificate attached."
    email = EmailMessage(
        email_subject,
        email_body,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
    )
    email.attach_file(certificate_file_path)

    # 5️⃣ Send email and handle exceptions
    try:
        connection = get_connection(fail_silently=False)
        email.connection = connection
        num_sent = email.send()
        if num_sent > 0:
            report.status = 'success'
            report.error_message = ''
        else:
            report.status = 'failed'
            report.error_message = 'SMTP server did not accept the message'
    except Exception as e:
        report.status = 'failed'
        report.error_message = str(e)

    # 6️⃣ Increment retry count and save
    report.retry_count += 1
    report.save()

    return redirect('report_list')

import csv
from django.http import HttpResponse
from .models import EmailReport

def report_export(request):
    """Export all email reports (success & failed) as CSV."""
    # Create the HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="email_reports.csv"'

    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'Certificate ID',
        'Student Name',
        'Email',
        'Status',
        'Sent At',
        'Error Message',
        'Retry Count'
    ])

    # Fetch all reports ordered by sent_at
    reports = EmailReport.objects.select_related('student').order_by('-sent_at')

    for report in reports:
        writer.writerow([
            report.student.certificate_id,
            report.student.full_name,
            report.student.email,
            report.status,
            report.sent_at.strftime("%Y-%m-%d %H:%M") if report.sent_at else '',
            report.error_message or '',
            report.retry_count
        ])

    return response
