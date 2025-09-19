from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from students.models import Student
from reports.models import EmailReport
from templates_app.models import CertificateTemplate

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def dashboard(request):
    total_students = Student.objects.count()
    certificates_sent = EmailReport.objects.filter(status='success').count()
    total_templates = CertificateTemplate.objects.count()
    failed_emails = EmailReport.objects.filter(status='failed').count()
    
    context = {
        'total_students': total_students,
        'certificates_sent': certificates_sent,
        'total_templates': total_templates,
        'failed_emails': failed_emails,
    }
    return render(request, 'accounts/dashboard.html', context)