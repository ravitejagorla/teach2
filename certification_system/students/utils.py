import os
import io
import threading
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.colors import Color
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from reports.models import EmailReport
from templates_app.models import CertificateTemplate
import logging
logger = logging.getLogger(__name__)

# -----------------------------
# Helper Functions
# -----------------------------
def assign_template(student_or_form, organization, specialization):
    """
    Assign the first active template for the given organization and specialization.
    """
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

class EmailThread(threading.Thread):
    """
    Threaded email sender to avoid blocking requests.
    Logs success or failure in EmailReport.
    """
    def __init__(self, email, student):
        threading.Thread.__init__(self)
        self.email = email
        self.student = student

    def run(self):
        try:
            self.email.send()
            EmailReport.objects.create(student=self.student, status='success')
        except Exception as e:
            EmailReport.objects.create(student=self.student, status='failed', error_message=str(e))


def generate_certificate(student):
    """
    Generate a PDF certificate based on the student's assigned template.
    """
    if not student.template or not student.template.is_active:
        return None

    # Ensure template file exists
    if not student.template.template_file or not default_storage.exists(student.template.template_file.name):
        print(f"Template file missing for {student.full_name}")
        return None

    try:
        buffer = io.BytesIO()
        template_file_path = student.template.template_file.path
        page_size = landscape(letter) if student.template.template_type == 'landscape' else portrait(letter)
        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        # Draw template background
        if template_file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            try:
                c.drawImage(template_file_path, 0, 0, width=width, height=height)
            except Exception as e:
                print(f"Error loading image template: {e}")
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, width, height, fill=1)
        else:
            c.setFillColorRGB(1, 1, 1)
            c.rect(0, 0, width, height, fill=1)

        # Scaling functions (base template: 1130x1600)
        template_width, template_height = 1130, 1600
        scale_x = lambda x: (x / template_width) * width
        scale_y = lambda y: height - (y / template_height) * height

        # Choose coordinates based on template name
        template_name = student.template.name.lower() + " " + student.template.organization.lower()
        if "quality thought certificate of participation" in template_name:
            name_x, name_y = scale_x(565), scale_y(620)
            course_x, course_y = scale_x(565), scale_y(690)
            start_x, start_y = scale_x(110), scale_y(1100)
            end_x, end_y = scale_x(110), scale_y(1150)
            cert_x, cert_y = scale_x(110), scale_y(1200)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))
            c.drawCentredString(name_x, name_y, student.full_name)

            c.setFont("Helvetica", 20)
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")

            c.setFont("Helvetica-Bold", 14)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
        elif "quality thought certificate of completion" in template_name:
            name_x, name_y = scale_x(565), scale_y(620)
            course_x, course_y = scale_x(565), scale_y(690)
            start_x, start_y = scale_x(110), scale_y(1100)
            end_x, end_y = scale_x(110), scale_y(1150)
            cert_x, cert_y = scale_x(110), scale_y(1200)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))   
            c.drawCentredString(name_x, name_y, student.full_name)

            c.setFont("Helvetica", 20)  
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")

            c.setFont("Helvetica-Bold", 14)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
        elif "quality thought certificate of appreciation" in template_name:
            name_x, name_y = scale_x(565), scale_y(620)
            course_x, course_y = scale_x(565), scale_y(690)
            start_x, start_y = scale_x(110), scale_y(1100)
            end_x, end_y = scale_x(110), scale_y(1150)
            cert_x, cert_y = scale_x(110), scale_y(1200)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))
            c.drawCentredString(name_x, name_y, student.full_name)

            c.setFont("Helvetica", 20)
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")

            c.setFont("Helvetica-Bold", 14)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
        elif "ramanasoft certificate of internship" in template_name:
            name_x, name_y = scale_x(560), scale_y(620)
            course_x, course_y = scale_x(560), scale_y(690)
            start_x, start_y = scale_x(400), scale_y(1150)
            end_x, end_y = scale_x(400), scale_y(1200)
            cert_x, cert_y = scale_x(400), scale_y(1250)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))
            c.drawCentredString(name_x, name_y, student.full_name)

            c.setFont("Helvetica", 20)
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")

            c.setFont("Helvetica-Bold", 14)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
        elif "ihub certificate of completions" in template_name:
            name_x, name_y = scale_x(565), scale_y(780)
            course_x, course_y = scale_x(565), scale_y(990)
            start_x, start_y = scale_x(140), scale_y(1230)
            end_x, end_y = scale_x(140), scale_y(1280)
            cert_x, cert_y = scale_x(140), scale_y(1330)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))
            c.drawCentredString(name_x, name_y, student.full_name)

            c.setFont("Helvetica", 18)
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")

            c.setFont("Helvetica-Bold", 12)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
        else:
            name_x, name_y = scale_x(565), scale_y(620)
            course_x, course_y = scale_x(565), scale_y(690)
            start_x, start_y = scale_x(140), scale_y(1080)
            end_x, end_y = scale_x(140), scale_y(1140)
            cert_x, cert_y = scale_x(140), scale_y(1180)
            # Draw content
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(Color(0, 0, 0, 1))
            c.drawCentredString(name_x, name_y, student.full_name)
    
            c.setFont("Helvetica", 20)
            c.drawCentredString(course_x, course_y, f"To be recognized as a {student.course} - {student.specialization}")
    
            c.setFont("Helvetica-Bold", 14)
            c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
            c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
            c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")
    
            # Timestamp
            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # c.setFont("Helvetica-Oblique", 10)
            # c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")
    
        

        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        # Ensure certificates directory exists
        cert_dir = "certificates"
        if not default_storage.exists(cert_dir):
            default_storage.makedirs(cert_dir)

        cert_filename = f"{cert_dir}/{student.certificate_id}_{student.full_name.replace(' ', '_')}.pdf"
        cert_path = default_storage.save(cert_filename, ContentFile(pdf_content))
        return cert_path

    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_simple_certificate(student):
    """
    Fallback PDF certificate without a template.
    """
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Background
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(0, 0, width, height, fill=1)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2)
        c.rect(20, 20, width-40, height-40, stroke=1, fill=0)

        # Title
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height-100, "CERTIFICATE OF COMPLETION")
        c.line(50, height-120, width-50, height-120)

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height-180, f"This certifies that {student.full_name}")
        c.setFont("Helvetica", 16)
        c.drawCentredString(width/2, height-220, f"has successfully completed {student.specialization}")
        c.drawCentredString(width/2, height-260, f"at {student.organization}")
        c.drawCentredString(width/2, height-300, f"from {student.start_date.strftime('%B %d, %Y')} to {student.end_date.strftime('%B %d, %Y')}")

        c.setFont("Helvetica-Oblique", 14)
        c.drawCentredString(width/2, height-340, f"Certificate ID: {student.certificate_id}")

        current_date = datetime.now().strftime("%B %d, %Y")
        c.drawCentredString(width/2, height-380, f"Date: {current_date}")

        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, 150, "_________________________")
        c.drawCentredString(width/2, 130, "Authorized Signature")

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, 50, f"Generated on: {current_time}")

        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        # Ensure certificates directory exists
        cert_dir = "certificates"
        if not default_storage.exists(cert_dir):
            default_storage.makedirs(cert_dir)

        cert_filename = f"{cert_dir}/{student.certificate_id}_{student.full_name.replace(' ', '_')}.pdf"
        cert_path = default_storage.save(cert_filename, ContentFile(pdf_content))
        return cert_path

    except Exception as e:
        print(f"Error generating simple certificate: {e}")
        import traceback
        traceback.print_exc()
        return None


class EmailSenderThread(threading.Thread):
    """
    Thread to send email asynchronously without blocking the request.
    """
    def __init__(self, email, student):
        super().__init__()
        self.email = email
        self.student = student

    def run(self):
        try:
            self.email.send(fail_silently=False)
            EmailReport.objects.create(student=self.student, status='success')
            logger.info(f"Email successfully sent to {self.student.email}")
        except Exception as e:
            EmailReport.objects.create(student=self.student, status='failed', error_message=str(e))
            logger.exception(f"Failed to send email to {self.student.email}")

def send_certificate_email(student, certificate_path):
    """
    Send a certificate PDF to a student via email.
    
    Args:
        student: Student instance
        certificate_path: Path to PDF file (relative to default storage)
    
    Returns:
        bool: True if email thread started, False otherwise
    """
    if not certificate_path or not default_storage.exists(certificate_path):
        logger.error(f"Certificate file missing for {student.full_name} at {certificate_path}")
        return False

    subject = f"Your Certificate - {student.specialization}"
    message = f"""
Dear {student.full_name},

Congratulations! Please find attached your certificate for {student.specialization}.

Best regards,
{student.institution}
"""

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[student.email]
    )

    try:
        # Attach PDF
        with default_storage.open(certificate_path, 'rb') as f:
            email.attach(f'certificate_{student.certificate_id}.pdf', f.read(), 'application/pdf')

        # Send email in a separate thread
        EmailSenderThread(email, student).start()
        return True

    except Exception as e:
        logger.exception(f"Failed to start email thread for {student.email}")
        EmailReport.objects.create(student=student, status='failed', error_message=str(e))
        return False