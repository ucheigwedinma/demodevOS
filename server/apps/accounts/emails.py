"""
Email helpers for the accounts app.

In development, emails are printed to the console via Django's
ConsoleEmailBackend.  Set EMAIL_BACKEND to an SMTP backend (or
a service like SendGrid / SES) in production.
"""

from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://localhost:5176")


def _base_context() -> dict:
    """Common template context shared by all email templates."""
    return {
        "frontend_url": FRONTEND_URL,
        "logo_url": f"{FRONTEND_URL}/logo-dark-email-header.png",
        "year": datetime.now().year,
    }


def send_verification_email(user, token: str, org_name: str = "", org_id: int | None = None) -> None:
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"

    context = {
        **_base_context(),
        "first_name": user.first_name,
        "verify_url": verify_url,
        "org_name": org_name,
        "org_id": org_id,
    }

    org_line = ""
    if org_name:
        org_line = (
            f"\nYour organization: {org_name} (ID: {org_id})\n"
        )

    plain = (
        f"Hi {user.first_name},\n\n"
        f"Welcome to developerOS! We're excited to have you on board.\n\n"
        f"To get started, please confirm your email address by clicking "
        f"the link below:\n\n"
        f"{verify_url}\n\n"
        f"If the button above doesn't work, copy and paste this URL "
        f"into your browser:\n"
        f"{verify_url}\n"
        f"{org_line}\n"
        f"Note: This link will expire in 24 hours. If you did not create "
        f"an account, you can safely ignore this email.\n\n"
        f"The developerOS Team"
    )

    html = render_to_string("emails/verify_email.html", context)

    msg = EmailMultiAlternatives(
        subject="Verify your developerOS account",
        body=plain,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_otp_email(user, otp: str) -> None:
    context = {
        **_base_context(),
        "first_name": user.first_name,
        "otp": otp,
    }

    plain = (
        f"Hi {user.first_name},\n\n"
        f"Welcome to developerOS! Please use the following code to verify "
        f"your account:\n\n"
        f"{otp}\n\n"
        f"Important: This code is valid for 5 minutes.\n\n"
        f"For your security, if you did not request this code, please "
        f"delete this email and do not share this number with anyone.\n\n"
        f"The developerOS Team"
    )

    html = render_to_string("emails/otp_code.html", context)

    msg = EmailMultiAlternatives(
        subject="Your developerOS Verification Code",
        body=plain,
        from_email=None,
        to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_password_reset_email(user, token: str) -> None:
    reset_path = "/reset-password"
    try:
        from apps.partners.models import PartnerPortalLegalAcceptance
        from apps.partners.portal_access import resolve_partner_portal_context

        if PartnerPortalLegalAcceptance.objects.filter(user=user).exists():
            reset_path = "/partner/reset-password"
        else:
            portal_context = resolve_partner_portal_context(user)
            if portal_context.is_partner_user:
                reset_path = "/partner/reset-password"
    except Exception:
        # Keep password reset available even if partner context resolution fails.
        reset_path = "/reset-password"

    reset_url = f"{FRONTEND_URL}{reset_path}?token={token}"

    context = {
        **_base_context(),
        "first_name": user.first_name,
        "reset_url": reset_url,
    }

    plain = (
        f"Hi {user.first_name},\n\n"
        f"We received a request to reset your password. "
        f"Click the link below to choose a new one:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in 15 minutes. If you didn't request a "
        f"password reset, you can safely ignore this email.\n\n"
        f"— The developerOS team"
    )

    html = render_to_string("emails/password_reset.html", context)

    msg = EmailMultiAlternatives(
        subject="Reset your developerOS password",
        body=plain,
        from_email=None,
        to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_demo_credentials_email(user, password: str, trial_end) -> None:
    login_url = f"{FRONTEND_URL}/login"

    context = {
        **_base_context(),
        "first_name": user.first_name,
        "email": user.email,
        "password": password,
        "login_url": login_url,
        "trial_end": trial_end.strftime("%B %d, %Y") if hasattr(trial_end, "strftime") else str(trial_end),
    }

    plain = (
        f"Hi {user.first_name},\n\n"
        f"Your developerOS demo is ready!\n\n"
        f"Login: {login_url}\n"
        f"Email: {user.email}\n"
        f"Password: {password}\n\n"
        f"Your trial expires on {context['trial_end']}.\n\n"
        f"Quick tips:\n"
        f"- Explore the Finance Dashboard for cash flow analytics\n"
        f"- Check out Projects for construction tracking\n"
        f"- Try the CRM Pipeline for lead management\n\n"
        f"The developerOS Team"
    )

    html = render_to_string("emails/demo_credentials.html", context)

    msg = EmailMultiAlternatives(
        subject="Your developerOS demo is ready",
        body=plain,
        from_email=None,
        to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_trial_confirmation_email(user, edition_name: str, trial_end) -> None:
    login_url = f"{FRONTEND_URL}/login"

    context = {
        **_base_context(),
        "first_name": user.first_name,
        "edition_name": edition_name,
        "trial_end": trial_end.strftime("%B %d, %Y") if hasattr(trial_end, "strftime") else str(trial_end),
        "login_url": login_url,
    }

    plain = (
        f"Hi {user.first_name},\n\n"
        f"Your 14-day free trial of developerOS {edition_name} is now active!\n\n"
        f"Your trial runs until {context['trial_end']}. During this period, "
        f"you'll have full access to all {edition_name} features.\n\n"
        f"Here are some things to explore:\n"
        f"- Set up your first project and track progress in real time\n"
        f"- Add your properties and manage your portfolio\n"
        f"- Invite your team to collaborate across departments\n"
        f"- Explore financial dashboards and reporting\n\n"
        f"Login anytime: {login_url}\n\n"
        f"The developerOS Team"
    )

    html = render_to_string("emails/trial_confirmation.html", context)

    msg = EmailMultiAlternatives(
        subject="Your developerOS trial is active",
        body=plain,
        from_email=None,
        to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_invitation_email(email: str, org_name: str, inviter_name: str, token: str) -> None:
    invite_url = f"{FRONTEND_URL}/signup?invitation={token}"

    context = {
        **_base_context(),
        "org_name": org_name,
        "inviter_name": inviter_name,
        "invite_url": invite_url,
    }

    plain = (
        f"Hi,\n\n"
        f"{inviter_name} has invited you to join {org_name} on developerOS.\n\n"
        f"Click the link below to create your account:\n\n"
        f"{invite_url}\n\n"
        f"— The developerOS team"
    )

    html = render_to_string("emails/invitation.html", context)

    msg = EmailMultiAlternatives(
        subject=f"You've been invited to join {org_name} on developerOS",
        body=plain,
        from_email=None,
        to=[email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send()
