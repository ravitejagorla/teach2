import csv
import json
import logging
from datetime import datetime

import pdfkit
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView, CreateView, UpdateView

from .models import Student
from .forms import StudentForm, ImportCSVForm
from .utils import generate_certificate, generate_simple_certificate, send_certificate_email, assign_template, is_gmail
from templates_app.models import CertificateTemplate
from reports.models import EmailReport

logger = logging.getLogger(__name__)

# -----------------------------
# Helper Functions
# -----------------------------
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
    if request.method == 'POST':
        try:
            deleted_count = 0
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            deleted_count = Student.objects.filter(pk__in=student_ids).delete()[0]
            return JsonResponse({'status': 'success', 'message': f'Successfully deleted {deleted_count} students'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


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
                imported_count = 0

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

                    Student.objects.create(
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
                    )
                    imported_count += 1

                messages.success(request, f"Successfully imported {imported_count} students!")
                return redirect('student_list')

            except Exception as e:
                messages.error(request, f"Error importing CSV: {str(e)}")
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
@require_POST
def send_certificate(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    cert_type = request.GET.get("type", "auto")

    try:
        if not is_gmail(student.email):
            EmailReport.objects.create(
                student=student,
                status='failed',
                error_message='Email not sent — only Gmail addresses are allowed'
            )
            return JsonResponse({'status': 'failed', 'message': 'Only Gmail addresses are allowed'})

        if cert_type == "manual":
            # Generate manual template using reportlab
            buffer = mt(request, student_id).content  # reuse mt
            filename = f"certificate_{student.id}.pdf"
            path = f"certificates/{filename}"
            with default_storage.open(path, 'wb') as f:
                f.write(buffer)
            cert_path = path
        else:
            # Default auto
            cert_path = generate_certificate(student) or generate_simple_certificate(student)

        if not cert_path:
            return JsonResponse({'status': 'failed', 'message': 'Certificate generation failed'})

        if send_certificate_email(student, cert_path):
            EmailReport.objects.create(student=student, status='success')
            return JsonResponse({'status': 'success', 'student_name': student.full_name})
        else:
            EmailReport.objects.create(
                student=student,
                status='failed',
                error_message='Email sending failed'
            )
            return JsonResponse({'status': 'failed', 'message': 'Email sending failed'})
    except Exception as e:
        logger.exception(f"Error sending certificate for student {student.id}")
        return JsonResponse({'status': 'failed', 'message': str(e)})

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
    cert_type = request.GET.get("type", "auto")

    if cert_type == "manual":
        return mt(request, student_id)  # use your reportlab certificate

    # else -> default auto certificate
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
    success_url = '/students/register/'

    def form_valid(self, form):
        assign_template(
            form.instance,
            form.cleaned_data.get("organization"),
            form.cleaned_data.get("specialization")
        )
        self.object = form.save()
        self.notify_admin(self.object)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Thank you! Your registration was successful."})

        messages.success(self.request, "Your details have been submitted successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
        return super().form_invalid(form)

    def notify_admin(self, student):
        try:
            admin_email = settings.ADMIN_EMAIL
            if not is_gmail(admin_email):
                logger.warning(f"Admin email {admin_email} is not Gmail. Skipping notification.")
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

from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from dateutil.relativedelta import relativedelta
from students.models import Student
from templates_app.models import Asset
from PIL import Image
import requests


# ---------------- HELPER ----------------
def get_image_reader(field_file):
    """
    Returns a ReportLab-compatible ImageReader object
    from a Django FileField (works for local and remote storage).
    Converts to RGB if the image has transparency.
    """
    if not field_file:
        return None

    try:
        # For remote storages (e.g. S3) where .path may not exist
        file_url = field_file.url
        if file_url.startswith("http"):
            response = requests.get(file_url)
            img = Image.open(BytesIO(response.content))
        else:
            # Local storage
            img = Image.open(field_file.path)

        # Convert RGBA/Palette to RGB to avoid ReportLab issues
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)

    except Exception as e:
        print(f"Error loading image {field_file}: {e}")
        return None


# ---------------- MAIN VIEW ----------------
def mt(request, student_id):
    student = Student.objects.get(id=student_id)

    # Internship duration
    months = 0
    if student.start_date and student.end_date:
        delta = relativedelta(student.end_date, student.start_date)
        months = delta.years * 12 + delta.months
        if months == 0:
            months = 1

    # Assets (logo, signature, stamp, etc.)
    assets = Asset.objects.filter(institute__name=student.institution).first()

    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font = "Helvetica"

    # Margins
    left_margin = 2 * cm
    right_margin = 2 * cm
    top_margin = 2 * cm
    bottom_margin = 2 * cm

    # ---------------- HEADER ----------------
    logo = get_image_reader(assets.logo) if assets and assets.logo else None
    if logo:
        p.drawImage(
            logo,
            left_margin,
            height - top_margin - 180,  # lower Y to avoid clipping
            width=120,
            preserveAspectRatio=True,
            mask="auto",
        )

    # ---------------- TITLE ----------------
    p.setFont(f"{font}-Bold", 16)
    p.drawCentredString(width / 2, height - top_margin - 80, f"{student.organization}")

    # ---------------- DATE ----------------
    if student.end_date:
        p.setFont(font, 12)
        p.drawRightString(
            width - right_margin,
            height - top_margin - 100,
            student.end_date.strftime("%d/%m/%Y"),
        )

    # ---------------- BODY ----------------
    text = p.beginText(left_margin, height - top_margin - 160)
    text.setFont(font, 12)
    text.setLeading(18)

    text.textLine(f"Dear {student.full_name},")
    text.textLine("")
    text.textLine(f"We are delighted to certify that you have successfully completed a {months} ")
    text.textLine(f"month{'s' if months > 1 else ''} internship with us as a {student.specialization} intern.")
    text.textLine("")
    text.textLine("During your internship, you had the opportunity to:")
    text.textLine(" • Work with a variety of technologies and programming languages.")
    text.textLine(" • Learn and apply software development methodologies such as Agile and Waterfall.")
    text.textLine(" • Develop coding and debugging skills.")
    text.textLine(" • Learn about software testing and quality assurance processes.")
    text.textLine(" • Collaborate with team members on projects and contribute to development.")
    text.textLine(" • Gain exposure to the software industry and network with professionals.")
    text.textLine("")
    text.textLine("We believe this internship has provided you with a valuable opportunity to ")
    text.textLine("expand your skills, gain practical experience, and build your professional network.")
    p.drawText(text)

    # ---------------- SIGNATURE ----------------
    sig_y = bottom_margin
    sig = get_image_reader(assets.signature) if assets and assets.signature else None
    if sig:
        p.drawImage(
            sig,
            left_margin,
            sig_y + 70,
            width=100,
            preserveAspectRatio=True,
            mask="auto",
        )

    p.setFont(font, 12)
    p.drawString(left_margin, sig_y + 260, "Sincerely,")
    p.setFont(f"{font}-Bold", 12)
    p.drawString(left_margin, sig_y + 240, f"From {student.institution or 'RamanaSoft'}")

    # ---------------- STAMP ----------------
    stamp = get_image_reader(assets.stamp) if assets and assets.stamp else None
    if stamp:
        p.drawImage(
            stamp,
            left_margin,
            bottom_margin + 70,
            width=100,
            preserveAspectRatio=True,
            mask="auto",
        )

    # Finish
    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="certificate_{student.id}.pdf"'
    return response
