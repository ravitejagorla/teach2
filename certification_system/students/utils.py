from io import BytesIO
import os
import io
import tempfile
from datetime import datetime
import threading
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.colors import Color
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from reports.models import EmailReport
from xhtml2pdf import pisa


class EmailThread(threading.Thread):
    def __init__(self, email, student):
        self.email = email
        self.student = student
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.email.send()
            # Log success
            EmailReport.objects.create(
                student=self.student,
                status='success'
            )
            return True
        except Exception as e:
            # Log failure
            EmailReport.objects.create(
                student=self.student,
                status='failed',
                error_message=str(e)
            )
            return False


def generate_certificate(student):
    """
    Generate a certificate PDF for the student using the provided template.
    Positions are dynamically chosen based on template name.
    """
    if not student.template or not student.template.is_active:
        return None

    try:
        buffer = io.BytesIO()
        template_path = student.template.template_file.path

        page_size = landscape(letter) if student.template.template_type == 'landscape' else portrait(letter)
        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        # Draw template background
        if template_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            try:
                c.drawImage(template_path, 0, 0, width=width, height=height)
            except Exception as e:
                print(f"Error loading image template: {e}")
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, width, height, fill=1)
        else:
            c.setFillColorRGB(1, 1, 1)
            c.rect(0, 0, width, height, fill=1)

        # Scaling functions (for 1130x1600 base template)
        template_width, template_height = 1130, 1600

        def scale_x(x): return (x / template_width) * width
        def scale_y(y): return height - (y / template_height) * height

        # --- Choose coordinates based on template name ---
        template_name = student.template.name.lower()  # assuming .name exists

        if "qualitythought" in template_name:
            name_x, name_y = scale_x(565), scale_y(620)
            course_x, course_y = scale_x(565), scale_y(720)
            start_x, start_y = scale_x(140), scale_y(1100)
            end_x, end_y = scale_x(140), scale_y(1160)
            cert_x, cert_y = scale_x(140), scale_y(1200)
        elif "ramanasoft" in template_name:
            name_x, name_y = scale_x(560), scale_y(600)
            course_x, course_y = scale_x(560), scale_y(680)
            start_x, start_y = scale_x(150), scale_y(1050)
            end_x, end_y = scale_x(150), scale_y(1100)
            cert_x, cert_y = scale_x(150), scale_y(1150)
        else:
            name_x, name_y = scale_x(565), scale_y(650)
            course_x, course_y = scale_x(565), scale_y(750)
            start_x, start_y = scale_x(140), scale_y(1080)
            end_x, end_y = scale_x(140), scale_y(1140)
            cert_x, cert_y = scale_x(140), scale_y(1180)

        # --- Draw content ---
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(Color(0, 0, 0, 1))
        c.drawCentredString(name_x, name_y, student.full_name)

        c.setFont("Helvetica", 20)
        c.drawCentredString(course_x, course_y, f"To be recognized as a {student.specialization}")

        c.setFont("Helvetica-Bold", 14)
        c.drawString(start_x, start_y, f"Start Date : {student.start_date.strftime('%d/%m/%Y')}")
        c.drawString(end_x, end_y, f"End Date : {student.end_date.strftime('%d/%m/%Y')}")
        c.drawString(cert_x, cert_y, f"Certification Id : {student.certificate_id}")

        # Timestamp for audit
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(scale_x(100), scale_y(1550), f"Generated on: {current_time}")

        # Save PDF
        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        cert_filename = f"certificates/{student.certificate_id}_{student.full_name.replace(' ', '_')}.pdf"
        cert_path = default_storage.save(cert_filename, ContentFile(pdf_content))
        return cert_path

    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_simple_certificate(student):
    """
    Generate a simple text-based certificate (fallback option)
    """
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Background and border
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(0, 0, width, height, fill=1)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2)
        c.rect(20, 20, width-40, height-40, stroke=1, fill=0)

        # Title and content
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

        cert_filename = f"certificates/{student.certificate_id}_{student.full_name.replace(' ', '_')}.pdf"
        cert_path = default_storage.save(cert_filename, ContentFile(pdf_content))
        return cert_path

    except Exception as e:
        print(f"Error generating simple certificate: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_certificate_email(student, certificate_path):
    if not certificate_path:
        return False

    subject = f"Your Certificate - {student.specialization}"
    message = f"""
Dear {student.full_name},

Please find attached your certificate for {student.specialization}.

Best regards,
Quality Thought Institution
"""
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.email]
    )

    try:
        with open(certificate_path, 'rb') as f:
            email.attach(f'certificate_{student.certificate_id}.pdf', f.read(), 'application/pdf')

        email_thread = EmailThread(email, student)
        email_thread.start()
        return True
    except Exception as e:
        EmailReport.objects.create(
            student=student,
            status='failed',
            error_message=str(e)
        )
        return False