from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(email, otp):
    # print(f'email = {email},otp = {otp}')
    subject = "Her Choice - Password Reset OTP"
    message = f"""
Your OTP for password reset is: {otp}

Do not share this OTP with anyone.
"""
    sender = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject,
        message,
        sender,
        [email],
        fail_silently=False,
    )
