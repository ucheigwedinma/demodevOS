import uuid
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserAuthSession, UserSecurityEvent

MFA_REAUTH_WINDOW = timedelta(minutes=15)


class MFAReauthRequired(BasePermission):
    """
    Require that the JWT contains a recent MFA verification.

    Checks the ``mfa_at`` claim and rejects if it is older than
    MFA_REAUTH_WINDOW (15 minutes) or missing.  Apply this alongside
    ``IsAuthenticated`` on sensitive endpoints like password change,
    TOTP disable, etc.
    """

    message = "MFA re-authentication required. Please verify your identity."

    def has_permission(self, request, view):
        token = getattr(request, "auth", None)
        if token is None:
            return False

        mfa_at_raw = token.get("mfa_at", "")
        if not mfa_at_raw:
            return False

        try:
            mfa_at = datetime.fromisoformat(mfa_at_raw)
            if timezone.is_naive(mfa_at):
                mfa_at = timezone.make_aware(mfa_at)
            return (timezone.now() - mfa_at) <= MFA_REAUTH_WINDOW
        except (ValueError, TypeError):
            return False


def extract_client_ip(request):
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def extract_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:1024]


def build_device_label(user_agent):
    if not user_agent:
        return "Unknown device"
    marker_tokens = ["Chrome", "Safari", "Firefox", "Edge", "Opera"]
    browser = next((token for token in marker_tokens if token in user_agent), "Browser")
    if "Windows" in user_agent:
        platform = "Windows"
    elif "Mac OS X" in user_agent or "Macintosh" in user_agent:
        platform = "macOS"
    elif "Android" in user_agent:
        platform = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        platform = "iOS"
    elif "Linux" in user_agent:
        platform = "Linux"
    else:
        platform = "Unknown OS"
    return f"{browser} on {platform}"


def log_user_security_event(
    *,
    user=None,
    principal="",
    event_type,
    status=UserSecurityEvent.Status.INFO,
    provider="",
    request=None,
    detail="",
    metadata=None,
):
    """Existing emit helper used by login / OAuth / OTP flows.

    For new emit sites prefer apps.accounts.audit.audit_emit, which
    accepts severity / target_type / target_id and is the canonical
    helper for Cluster 6's IAM audit feed. Both write to the same
    UserSecurityEvent table; this helper is kept for backwards
    compatibility with all the auth-flow callers.
    """
    user_agent = extract_user_agent(request)
    organization = None
    if user is not None:
        profile = getattr(user, "profile", None)
        organization = getattr(profile, "organization", None) if profile else None
    UserSecurityEvent.objects.create(
        user=user,
        organization=organization,
        principal=(principal or "").strip()[:254],
        event_type=event_type,
        status=status,
        provider=provider or "",
        ip_address=extract_client_ip(request),
        user_agent=user_agent,
        device_label=build_device_label(user_agent),
        detail=detail or "",
        metadata=metadata or {},
    )


def create_user_session(*, user, request=None, provider=UserAuthSession.AuthProvider.PASSWORD):
    user_agent = extract_user_agent(request)
    return UserAuthSession.objects.create(
        user=user,
        sid=uuid.uuid4(),
        auth_provider=provider,
        ip_address=extract_client_ip(request),
        user_agent=user_agent,
        device_label=build_device_label(user_agent),
    )


def _session_duration_minutes(user):
    """Look up the user's most-restrictive active session_duration policy.

    Returns (max_minutes, idle_minutes) or (None, None) if no policy
    applies. The most restrictive (smallest max_minutes) wins.
    """
    profile = getattr(user, "profile", None)
    org = getattr(profile, "organization", None) if profile else None
    if not org:
        return None, None
    try:
        from apps.settings.models import AccessPolicy
    except Exception:
        return None, None
    policies = AccessPolicy.objects.filter(
        organization=org,
        kind=AccessPolicy.Kind.SESSION_DURATION,
        is_active=True,
    ).prefetch_related("policy_actions")
    best_max = None
    best_idle = None
    for p in policies:
        action = next((a for a in p.policy_actions.all() if a.is_active), None)
        if not action:
            continue
        params = action.parameters or {}
        m = params.get("max_minutes")
        i = params.get("idle_minutes")
        if isinstance(m, int) and m > 0:
            best_max = m if best_max is None else min(best_max, m)
        if isinstance(i, int) and i > 0:
            best_idle = i if best_idle is None else min(best_idle, i)
    return best_max, best_idle


def issue_tokens_for_user(
    *,
    user,
    request=None,
    remember_me=False,
    provider=UserAuthSession.AuthProvider.PASSWORD,
    mfa_verified=False,
    mfa_method="",
):
    session = create_user_session(user=user, request=request, provider=provider)
    refresh = RefreshToken.for_user(user)
    refresh["sid"] = str(session.sid)

    # MFA claims — embedded in both access and refresh tokens
    now = timezone.now()
    refresh["mfa_verified"] = mfa_verified
    refresh["mfa_method"] = mfa_method
    refresh["mfa_at"] = now.isoformat() if mfa_verified else ""

    if not remember_me:
        refresh.set_exp(lifetime=timedelta(hours=24))

    # Cluster 4: apply the org's session_duration policy if any. The
    # policy's max_minutes caps the refresh-token lifetime; idle_minutes
    # is captured as a claim so the frontend can enforce idle timeout
    # client-side (server idle-timeout enforcement would require last-
    # activity tracking — future work).
    max_minutes, idle_minutes = _session_duration_minutes(user)
    if max_minutes:
        # Only shorten — never extend beyond the SimpleJWT default.
        current_lifetime = refresh.lifetime if hasattr(refresh, "lifetime") else None
        policy_lifetime = timedelta(minutes=max_minutes)
        if current_lifetime is None or policy_lifetime < current_lifetime:
            refresh.set_exp(lifetime=policy_lifetime)
        refresh["session_max_minutes"] = max_minutes
    if idle_minutes:
        refresh["session_idle_minutes"] = idle_minutes

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "session_id": str(session.sid),
        "session_created_at": now.isoformat(),
        "session_max_minutes": max_minutes,
        "session_idle_minutes": idle_minutes,
    }


def record_password_change(user, new_password=None):
    """Record a password change after user.set_password() + user.save().

    Steps:
      1. Append the just-set hash to UserPasswordHistory.
      2. Bump UserProfile.password_last_changed.
      3. Prune history rows beyond the org's password_history_count.

    new_password is accepted for symmetry/future use; only the saved
    user.password (current hash) is needed.
    """
    from .models import UserPasswordHistory, UserProfile

    if user.password:
        UserPasswordHistory.objects.create(user=user, password_hash=user.password)

    profile = getattr(user, "profile", None)
    if profile is None:
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = None
    if profile is not None:
        profile.password_last_changed = timezone.now()
        profile.save(update_fields=["password_last_changed"])

    org = getattr(profile, "organization", None)
    keep = (org.password_history_count if org else 0)
    if keep > 0:
        # Keep keep+1 most-recent rows (the +1 is the current hash, used
        # by next-rotation comparison; older are pruned).
        ids_to_prune = list(
            UserPasswordHistory.objects
            .filter(user=user)
            .order_by("-changed_at")
            .values_list("id", flat=True)[keep + 1:]
        )
        if ids_to_prune:
            UserPasswordHistory.objects.filter(id__in=ids_to_prune).delete()
