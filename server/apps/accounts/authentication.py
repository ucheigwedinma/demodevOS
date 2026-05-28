import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.models import APIKey, ApplicationToken, ServiceAccount, UserAuthSession
from apps.accounts.security import build_device_label, extract_client_ip, extract_user_agent


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate requests using service-account API keys.

    Accepts keys via:
      - Authorization: Api-Key <key>
      - X-API-Key: <key>

    The key prefix (first 8 chars) is used for DB lookup, then the full
    SHA-256 hash is compared for verification.
    """

    keyword = "Api-Key"
    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request):
        raw_key = self._extract_key(request)
        if raw_key is None:
            return None  # Let other authenticators try

        if len(raw_key) < APIKey.PREFIX_LENGTH:
            raise AuthenticationFailed("Invalid API key.")

        prefix = raw_key[: APIKey.PREFIX_LENGTH]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        try:
            api_key = APIKey.objects.select_related(
                "service_account", "service_account__owner"
            ).get(prefix=prefix, hashed_key=hashed)
        except APIKey.DoesNotExist as err:
            raise AuthenticationFailed("Invalid API key.") from err

        if not api_key.is_active:
            raise AuthenticationFailed("API key has been revoked.")

        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired.")

        sa = api_key.service_account
        if sa.status != ServiceAccount.Status.ACTIVE:
            raise AuthenticationFailed("Service account is not active.")

        # Stamp last_used_at (fire-and-forget, don't block the request)
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        user = sa.owner
        if user is None:
            raise AuthenticationFailed("Service account has no owner.")

        return (user, api_key)

    def _extract_key(self, request):
        # Try Authorization header first: "Api-Key <key>"
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith(f"{self.keyword} "):
            return auth_header[len(self.keyword) + 1 :]

        # Fall back to X-API-Key header
        return request.META.get(self.header_name)

    def authenticate_header(self, request):
        return self.keyword


class ApplicationTokenAuthentication(BaseAuthentication):
    """Authenticate requests using long-lived ApplicationToken bearer tokens.

    Accepts tokens via Authorization: AppToken <dvo_...>.

    Sets request.auth to the ApplicationToken instance so DRF permission
    classes (HasAppTokenScope) can read its scopes. The authenticated
    user is the token's created_by (or any active org user as fallback);
    the token itself isn't tied to a single human, just to an
    organisation.
    """

    keyword = "AppToken"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None
        raw = auth_header[len(self.keyword) + 1:].strip()
        if not raw or not raw.startswith("dvo_"):
            return None  # not our token format; let other authenticators try

        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        try:
            token = ApplicationToken.objects.select_related(
                "organization", "created_by"
            ).get(token_hash=h)
        except ApplicationToken.DoesNotExist as err:
            raise AuthenticationFailed("Invalid application token.") from err

        if not token.is_active:
            raise AuthenticationFailed("Application token revoked.")
        if token.expires_at and token.expires_at < timezone.now():
            raise AuthenticationFailed("Application token expired.")

        # Stamp last_used_at (fire-and-forget)
        ApplicationToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())

        # Use the token's creator as the request user. If they're gone,
        # fall back to any active org admin so the request doesn't 401.
        user = token.created_by
        if user is None or not user.is_active:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(
                profile__organization=token.organization,
                is_active=True,
            ).first()
            if user is None:
                raise AuthenticationFailed("App token has no usable owner.")

        return (user, token)

    def authenticate_header(self, request):
        return self.keyword


class SessionAwareJWTAuthentication(JWTAuthentication):
    """
    JWT auth with optional server-side session enforcement.

    Tokens issued after session tracking include `sid`. If present, the related
    session must be active (not revoked). Legacy tokens without `sid` are accepted.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        sid = validated_token.get("sid")
        if sid:
            try:
                session = UserAuthSession.objects.get(
                    user=user,
                    sid=sid,
                    revoked_at__isnull=True,
                )
            except UserAuthSession.DoesNotExist as err:
                raise AuthenticationFailed("Session has expired or been revoked.") from err

            user_agent = extract_user_agent(request)
            updates = {
                "last_seen_at": timezone.now(),
            }
            ip_address = extract_client_ip(request)
            if ip_address and session.ip_address != ip_address:
                updates["ip_address"] = ip_address
            if user_agent and session.user_agent != user_agent:
                updates["user_agent"] = user_agent
                updates["device_label"] = build_device_label(user_agent)
            UserAuthSession.objects.filter(pk=session.pk).update(**updates)

        return (user, validated_token)
