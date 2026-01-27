from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(recipient_email, otp_code, subject_prefix="Verification"):
    """
    Sends a generic OTP code. 
    The OTP is removed from the subject line for better privacy/security.
    """
    # Subject now only identifies the purpose of the email
    subject = f"Her Choice - {subject_prefix}"
    
    message = f"""
Dear User,

Your 6-digit code for {subject_prefix.lower()} is: {otp_code}

This code is valid for 2 minutes.
Do not share this OTP with anyone.

Thank you,
Her Choice Team
"""
    sender = settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
        return False