from django.core.mail import send_mail

from django.conf import settings
from core.celery import app

def send_email(subject, message, recipient_list, html_message=None):
    email_from = settings.EMAIL_HOST_USER
    result = send_mail(
        subject,
        message,
        email_from,
        recipient_list,
        html_message=html_message
    )
    return result