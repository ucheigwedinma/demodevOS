"""
Core MFA business logic: TOTP, recovery codes, WebAuthn helpers.
"""

import base64
import io
import secrets
import string

import pyotp
import qrcode
import qrcode.constants
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import RecoveryCode, TOTPDevice, WebAuthnCredential

# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------

TOTP_ISSUER = "developerOS"
TOTP_VALID_WINDOW = 1  # accept codes from ±1 time-step (±30 s)


def generate_totp_secret():
    """Return a random base32 secret suitable for authenticator apps."""
    return pyotp.random_base32(length=32)


def get_totp_uri(user, secret):
    """Build the otpauth:// URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user.email, issuer_name=TOTP_ISSUER)


def get_totp_qr_base64(uri):
    """Return a base64-encoded PNG of the QR code for the given URI."""
    img = qrcode.make(
        uri,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def verify_totp_code(secret, code):
    """Verify a 6-digit TOTP code against the secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=TOTP_VALID_WINDOW)


def setup_totp(user):
    """
    Create or replace an unconfirmed TOTP device for a user.
    Returns (secret, uri, qr_base64).
    """
    secret = generate_totp_secret()
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    TOTPDevice.objects.create(user=user, secret=secret, confirmed=False)
    uri = get_totp_uri(user, secret)
    qr = get_totp_qr_base64(uri)
    return secret, uri, qr


def confirm_totp(user, code):
    """
    Confirm TOTP setup by verifying the first code.
    Returns True on success, False on bad code.
    Raises TOTPDevice.DoesNotExist if no pending setup.
    """
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    if not verify_totp_code(device.secret, code):
        return False
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    # Flip the profile flag
    profile = getattr(user, "profile", None)
    if profile:
        profile.mfa_enabled = True
        profile.save(update_fields=["mfa_enabled"])
    return True


def disable_totp(user):
    """Remove TOTP device for a user."""
    TOTPDevice.objects.filter(user=user).delete()


def user_has_totp(user):
    """Return True if user has a confirmed TOTP device."""
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


# ---------------------------------------------------------------------------
# Recovery Codes
# ---------------------------------------------------------------------------

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 8
RECOVERY_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_code():
    raw = "".join(secrets.choice(RECOVERY_CODE_CHARS) for _ in range(RECOVERY_CODE_LENGTH))
    return f"{raw[:4]}-{raw[4:]}"


def generate_recovery_codes(user):
    """
    Generate fresh recovery codes for a user.
    Deletes all previous codes.  Returns list of plaintext codes (show once).
    """
    RecoveryCode.objects.filter(user=user).delete()
    plaintext_codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = _generate_code()
        plaintext_codes.append(code)
        RecoveryCode.objects.create(
            user=user,
            code_hash=make_password(code),
        )
    return plaintext_codes


def verify_recovery_code(user, code):
    """
    Check a recovery code.  If valid, mark it used and return True.
    """
    code = code.strip().upper()
    for rc in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
        if check_password(code, rc.code_hash):
            rc.used_at = timezone.now()
            rc.save(update_fields=["used_at"])
            return True
    return False


def remaining_recovery_codes(user):
    """Count of unused recovery codes."""
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


# ---------------------------------------------------------------------------
# WebAuthn Helpers
# ---------------------------------------------------------------------------


def get_webauthn_rp_id():
    return getattr(settings, "WEBAUTHN_RP_ID", "localhost")


def get_webauthn_rp_name():
    return getattr(settings, "WEBAUTHN_RP_NAME", "developerOS")


def get_webauthn_origin():
    return getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost:5173")


def user_has_passkeys(user):
    return WebAuthnCredential.objects.filter(user=user).exists()


def get_available_mfa_methods(user):
    """Return list of MFA methods available for a user."""
    methods = ["email"]  # always available
    if user_has_totp(user):
        methods.insert(0, "totp")
    if user_has_passkeys(user):
        methods.insert(0, "passkey")
    if remaining_recovery_codes(user) > 0:
        methods.append("recovery")
    return methods
