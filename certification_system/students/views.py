import csv
import json
import logging
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView, CreateView, UpdateView
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Student
from .forms import StudentForm, ImportCSVForm
from templates_app.models import CertificateTemplate
from .utils import generate_certificate, generate_simple_certificate, send_certificate_email
from reports.models import EmailReport  # ✅ Added for logging

logger = logging.getLogger(__name__)

# -----------------------------
# Helper Functions
# -----------------------------
def assign_template(student_or_form, organization, specialization):
    """Assign the first active template for the given organization and specialization."""
    template = CertificateTemplate.objects.filter(
        organization=organization,
        specialization=specialization,
        is_active=True
    ).first()
    if template:
        student_or_form.template = template
    return template

def is_gmail(email):
    """Check if email is a Gmail address."""
    return email and email.lower().endswith("@gmail.com")

def generate_and_send_certificate(student):
    """Generate a certificate and send via email. Returns a status dict."""
    try:
        if not is_gmail(student.email):
            EmailReport.objects.create(
                student=student,
                status='failed',
                error_message='Email not sent — only Gmail addresses are allowed'
            )
            return {'status': 'failed', 'message': 'Only Gmail addresses are allowed'}

        cert_path = generate_certificate(student) or generate_simple_certificate(student)
        if not cert_path:
            EmailReport.objects.create(
                student=student,
                status='failed',
                error_message='Certificate generation failed'
            )
            return {'status': 'failed', 'message': 'Certificate generation failed'}

        if send_certificate_email(student, cert_path):
            EmailReport.objects.create(student=student, status='success')
            return {'status': 'success', 'student_name': student.full_name}
        else:
            EmailReport.objects.create(
                student=student,
                status='failed',
                error_message='Email sending failed'
            )
            return {'status': 'failed', 'message': 'Email sending failed'}
    except Exception as e:
        logger.exception(f"Error sending certificate for student {student.id}")
        EmailReport.objects.create(
            student=student,
            status='failed',
            error_message=str(e)
        )
        return {'status': 'failed', 'message': 'Unexpected error'}

# -----------------------------
# Student Views
# -----------------------------
class StudentListView(ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(certificate_id__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class StudentCreateView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student_list')

    def form_valid(self, form):
        assign_template(form.instance, form.cleaned_data.get("organization"), form.cleaned_data.get("specialization"))
        messages.success(self.request, 'Student created successfully!')
        return super().form_valid(form)

class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student_list')

    def form_valid(self, form):
        assign_template(form.instance, form.cleaned_data.get("organization"), form.cleaned_data.get("specialization"))
        messages.success(self.request, 'Student updated successfully!')
        return super().form_valid(form)

# -----------------------------
# Delete Views
# -----------------------------
@require_POST
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    return JsonResponse({'status': 'success'})

@csrf_exempt
def bulk_delete_students(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        deleted_count, _ = Student.objects.filter(id__in=student_ids).delete()
        return JsonResponse({'status': 'success', 'message': f'Successfully deleted {deleted_count} students'})
    except Exception:
        logger.exception("Bulk delete error")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

# -----------------------------
# CSV Import/Export
# -----------------------------
@csrf_exempt
def import_students(request):
    if request.method == "POST":
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                students_to_create = []

                for row in reader:
                    if not row.get('Full Name') or not row.get('Mobile'):
                        continue
                    try:
                        start_date = datetime.strptime(row['Start Date'], '%m/%d/%Y').date()
                        end_date = datetime.strptime(row['End Date'], '%m/%d/%Y').date()
                    except Exception:
                        continue

                    template = CertificateTemplate.objects.filter(
                        organization=row.get('Organization'),
                        specialization=row.get('Specialization'),
                        course=row.get('Course'),
                        is_active=True
                    ).first()

                    students_to_create.append(Student(
                        full_name=row.get('Full Name'),
                        email=row.get('Email'),
                        mobile=row.get('Mobile'),
                        specialization=row.get('Specialization', ''),
                        course=row.get('Course', ''),
                        organization=row.get('Organization', ''),
                        institution=row.get('Institution', ''),
                        start_date=start_date,
                        end_date=end_date,
                        template=template
                    ))

                Student.objects.bulk_create(students_to_create)
                messages.success(request, f"Successfully imported {len(students_to_create)} students!")
                return redirect('student_list')

            except Exception:
                logger.exception("CSV import error")
                messages.error(request, "Error importing CSV.")
    else:
        form = ImportCSVForm()
    return render(request, 'students/import.html', {'form': form})

def export_students(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Email', 'Mobile', 'Specialization', 'Course', 'Organization', 'Institution', 'Start Date', 'End Date'])

    for student in Student.objects.all():
        writer.writerow([
            student.full_name,
            student.email,
            student.mobile or '',
            student.specialization,
            student.course,
            student.organization,
            student.institution,
            student.start_date,
            student.end_date
        ])
    return response

# -----------------------------
# Certificate Views
# -----------------------------
@require_POST
def send_certificate(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if not is_gmail(student.email):
        EmailReport.objects.create(
            student=student,
            status='failed',
            error_message='Only Gmail addresses are allowed'
        )
        return JsonResponse({"status": "failed", "message": "Only Gmail addresses are allowed."})

    cert_path = generate_certificate(student) or generate_simple_certificate(student)
    if not cert_path:
        EmailReport.objects.create(
            student=student,
            status='failed',
            error_message='Certificate generation failed'
        )
        return JsonResponse({"status": "failed", "message": "Certificate generation failed."})

    email_sent = send_certificate_email(student, cert_path)
    if email_sent:
        EmailReport.objects.create(student=student, status='success')
        return JsonResponse({"status": "success", "student_name": student.full_name})
    else:
        EmailReport.objects.create(
            student=student,
            status='failed',
            error_message='Email sending failed'
        )
        return JsonResponse({"status": "failed", "message": "Email sending failed."})

@csrf_exempt
def bulk_send_certificates(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        students = Student.objects.filter(id__in=student_ids)
        student_map = {s.id: s for s in students}

        results = []
        for student_id in student_ids:
            student = student_map.get(student_id)
            if student:
                results.append({'id': student_id, **generate_and_send_certificate(student)})
            else:
                results.append({'id': student_id, 'status': 'failed', 'message': 'Student not found'})

        return JsonResponse({'status': 'success', 'results': results})
    except Exception:
        logger.exception("bulk_send_certificates error")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

def download_certificate(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    cert_path = generate_certificate(student) or generate_simple_certificate(student)
    if not cert_path:
        messages.error(request, 'Failed to generate certificate.')
        return redirect('student_list')

    filename = f"{student.certificate_id}_{student.full_name}.pdf"
    try:
        return FileResponse(
            default_storage.open(cert_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
    except Exception:
        logger.exception("Certificate download error")
        messages.error(request, 'Error downloading certificate.')
        return redirect('student_list')

# -----------------------------
# AJAX: Get Specializations and Courses
# -----------------------------
@require_GET
def get_specializations(request):
    org = request.GET.get('organization')
    specs = CertificateTemplate.objects.filter(organization=org, is_active=True).values_list('specialization', flat=True).distinct()
    courses = CertificateTemplate.objects.filter(organization=org, is_active=True).values_list('course', flat=True).distinct()
    return JsonResponse({'specializations': list(specs), 'courses': list(courses)})

# -----------------------------
# Student Self-Register View
# -----------------------------
class StudentSelfRegisterView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_self_register.html'
    success_url = reverse_lazy('student_self_register')

    def form_valid(self, form):
        assign_template(
            form.instance,
            form.cleaned_data.get("organization"),
            form.cleaned_data.get("specialization")
        )
        response = super().form_valid(form)
        self.notify_admin(form.instance)
        messages.success(self.request, "Your details have been submitted successfully!")
        return response

    def notify_admin(self, student):
        try:
            admin_email = settings.ADMIN_EMAIL
            if not is_gmail(admin_email):
                logger.warning(f"Admin email {admin_email} is not a Gmail address. Skipping notification.")
                return
            subject = "New Student Registration"
            message = (
                f"A new student has registered.\n\n"
                f"Name: {student.full_name}\n"
                f"Email: {student.email}\n"
                f"Mobile: {student.mobile}\n"
                f"Organization: {student.organization}\n"
                f"Specialization: {student.specialization}\n"
                f"Course: {student.course}\n"
                f"Start Date: {student.start_date}\n"
                f"End Date: {student.end_date}\n"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [admin_email], fail_silently=True)
        except Exception:
            logger.exception("Failed to send admin notification email")

# -----------------------------
# MT View: Download Certificate or Manual Template
# -----------------------------
def mt(request, pk):
    student = get_object_or_404(Student, pk=pk)
    download_type = request.GET.get('type', 'auto')  # 'auto' for PDF, 'manual' for HTML template

    if download_type == 'manual':
        # Download HTML template
        html_content = render_to_string('certificate_template.html', {'student': student})
        response = HttpResponse(html_content, content_type='text/html')
        filename = f"{student.full_name}_manual_template.html"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        # Download generated PDF certificate
        cert_path = generate_certificate(student) or generate_simple_certificate(student)
        if not cert_path:
            messages.error(request, 'Failed to generate certificate.')
            return redirect('student_list')

        filename = f"{student.certificate_id}_{student.full_name}.pdf"
        try:
            return FileResponse(
                default_storage.open(cert_path, 'rb'),
                as_attachment=True,
                filename=filename
            )
        except Exception:
            logger.exception("Certificate download error")
            messages.error(request, 'Error downloading certificate.')
            return redirect('student_list')
