import json
import csv
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.conf import settings
from django.core.files.storage import default_storage

from .models import Student
from .forms import StudentForm, ImportCSVForm
from templates_app.models import CertificateTemplate
from .utils import generate_certificate, send_certificate_email, generate_simple_certificate


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
        organization = form.cleaned_data.get("organization")
        specialization = form.cleaned_data.get("specialization")
        template = CertificateTemplate.objects.filter(
            organization=organization,
            specialization=specialization,
            is_active=True
        ).first()

        if template:
            form.instance.template = template
        else:
            messages.warning(self.request, "No active certificate template found for this combination.")

        messages.success(self.request, 'Student created successfully!')
        return super().form_valid(form)


class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student_list')

    def form_valid(self, form):
        organization = form.cleaned_data.get("organization")
        specialization = form.cleaned_data.get("specialization")
        template = CertificateTemplate.objects.filter(
            organization=organization,
            specialization=specialization,
            is_active=True
        ).first()

        if template:
            form.instance.template = template
        else:
            messages.warning(self.request, "No active certificate template found for this combination.")

        messages.success(self.request, 'Student updated successfully!')
        return super().form_valid(form)


# -----------------------------
# Single Delete
# -----------------------------
def student_delete(request, pk):
    if request.method == 'POST':
        student = get_object_or_404(Student, pk=pk)
        student.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


# -----------------------------
# Bulk Delete
# -----------------------------
@csrf_exempt
def bulk_delete_students(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            deleted_count = 0

            for student_id in student_ids:
                try:
                    student = Student.objects.get(pk=student_id)
                    student.delete()
                    deleted_count += 1
                except Student.DoesNotExist:
                    continue

            return JsonResponse({'status': 'success', 'message': f'Successfully deleted {deleted_count} students'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


# -----------------------------
# CSV Import
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


# -----------------------------
# CSV Export
# -----------------------------
def export_students(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Email', 'Mobile', 'Specialization', 'Course', 'Organization', 'Institution', 'Start Date', 'End Date'])

    students = Student.objects.all()
    for student in students:
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
# Download Certificate
# -----------------------------
def download_certificate(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    certificate_path = generate_certificate(student)
    if not certificate_path:
        certificate_path = generate_simple_certificate(student)

    if not certificate_path:
        messages.error(request, 'Failed to generate certificate.')
        return redirect('student_list')

    filename = f"{student.certificate_id}_{student.full_name}.pdf"
    try:
        with default_storage.open(certificate_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        messages.error(request, f'Error downloading certificate: {str(e)}')
        return redirect('student_list')


# -----------------------------
# Send Single Certificate
# -----------------------------
@csrf_exempt
def send_certificate(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(id=student_id)

            if settings.DEBUG:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Certificate sent successfully (simulated)',
                    'student_name': student.full_name
                })

            certificate_path = generate_certificate(student)
            if not certificate_path:
                certificate_path = generate_simple_certificate(student)

            if certificate_path:
                success = send_certificate_email(student, certificate_path)
                if success:
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Certificate sent successfully',
                        'student_name': student.full_name
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': 'Failed to send certificate'}, status=500)
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to generate certificate'}, status=500)

        except Student.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# -----------------------------
# Bulk Send Certificates
# -----------------------------
@csrf_exempt
def bulk_send_certificates(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            results = []

            for student_id in student_ids:
                try:
                    student = Student.objects.get(pk=student_id)
                    certificate_path = generate_certificate(student)
                    if not certificate_path:
                        certificate_path = generate_simple_certificate(student)

                    if certificate_path and send_certificate_email(student, certificate_path):
                        results.append({'id': student_id, 'status': 'success', 'student_name': student.full_name})
                    else:
                        results.append({'id': student_id, 'status': 'failed'})
                except Student.DoesNotExist:
                    results.append({'id': student_id, 'status': 'failed'})

            return JsonResponse({'status': 'success', 'results': results})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


# -----------------------------
# Get Specializations and Courses (AJAX)
# -----------------------------
@require_GET
def get_specializations(request):
    org = request.GET.get('organization')
    specs = CertificateTemplate.objects.filter(organization=org).values_list('specialization', flat=True).distinct()
    courses = CertificateTemplate.objects.filter(organization=org).values_list('course', flat=True).distinct()
    return JsonResponse({
        'specializations': list(specs),
        'courses': list(courses)
    })