import hashlib
import logging
import secrets

from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OAUTH_STATE_PREFIX = "oauth_state:"
OAUTH_STATE_TTL = 600  # 10 minutes


class OAuthProviderConfigurationError(ValueError):
    pass


# ---------------------------------------------------------------------------
# State + PKCE helpers
# ---------------------------------------------------------------------------

def generate_oauth_state(provider: str) -> dict:
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    cache.set(
        f"{OAUTH_STATE_PREFIX}{state}",
        {"provider": provider, "code_verifier": code_verifier},
        timeout=OAUTH_STATE_TTL,
    )
    return {"state": state, "code_verifier": code_verifier}


def validate_oauth_state(state: str) -> dict | None:
    key = f"{OAUTH_STATE_PREFIX}{state}"
    data = cache.get(key)
    if data:
        cache.delete(key)
    return data


def _require_provider_config(provider: str, conf: dict, required_fields: list[str]) -> None:
    missing = [field for field in required_fields if not str(conf.get(field, "")).strip()]
    if missing:
        readable = ", ".join(missing)
        raise OAuthProviderConfigurationError(
            f"{provider.title()} sign-in is not configured. Missing: {readable}."
        )


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

def google_authorize_url(state: str, code_verifier: str) -> str:
    conf = settings.OAUTH_PROVIDERS["google"]
    _require_provider_config("google", conf, ["client_id", "redirect_uri"])
    session = OAuth2Session(
        client_id=conf["client_id"],
        redirect_uri=conf["redirect_uri"],
        scope="openid email profile",
        code_challenge_method="S256",
    )
    url, _ = session.create_authorization_url(
        "https://accounts.google.com/o/oauth2/v2/auth",
        state=state,
        code_verifier=code_verifier,
    )
    return url


def google_exchange_code(code: str, code_verifier: str) -> dict:
    conf = settings.OAUTH_PROVIDERS["google"]
    _require_provider_config("google", conf, ["client_id", "client_secret", "redirect_uri"])
    session = OAuth2Session(
        client_id=conf["client_id"],
        client_secret=conf["client_secret"],
        redirect_uri=conf["redirect_uri"],
        code_challenge_method="S256",
    )
    token = session.fetch_token(
        "https://oauth2.googleapis.com/token",
        code=code,
        code_verifier=code_verifier,
    )
    resp = session.get("https://openidconnect.googleapis.com/v1/userinfo")
    resp.raise_for_status()
    info = resp.json()
    return {
        "provider": "google",
        "sub": info["sub"],
        "email": info["email"].lower(),
        "name": info.get("name", ""),
        "email_verified": info.get("email_verified", False),
        "access_token_hash": hashlib.sha256(token["access_token"].encode()).hexdigest(),
    }


# ---------------------------------------------------------------------------
# Microsoft
# ---------------------------------------------------------------------------

def _microsoft_base_url(tenant: str) -> str:
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"


def microsoft_authorize_url(state: str, code_verifier: str) -> str:
    conf = settings.OAUTH_PROVIDERS["microsoft"]
    _require_provider_config("microsoft", conf, ["client_id", "redirect_uri"])
    tenant = conf.get("tenant", "common")
    session = OAuth2Session(
        client_id=conf["client_id"],
        redirect_uri=conf["redirect_uri"],
        scope="openid email profile User.Read",
        code_challenge_method="S256",
    )
    url, _ = session.create_authorization_url(
        f"{_microsoft_base_url(tenant)}/authorize",
        state=state,
        code_verifier=code_verifier,
    )
    return url


def microsoft_exchange_code(code: str, code_verifier: str) -> dict:
    conf = settings.OAUTH_PROVIDERS["microsoft"]
    _require_provider_config("microsoft", conf, ["client_id", "client_secret", "redirect_uri"])
    tenant = conf.get("tenant", "common")
    session = OAuth2Session(
        client_id=conf["client_id"],
        client_secret=conf["client_secret"],
        redirect_uri=conf["redirect_uri"],
        code_challenge_method="S256",
    )
    token = session.fetch_token(
        f"{_microsoft_base_url(tenant)}/token",
        code=code,
        code_verifier=code_verifier,
    )
    resp = session.get("https://graph.microsoft.com/v1.0/me")
    resp.raise_for_status()
    info = resp.json()
    email = (info.get("mail") or info.get("userPrincipalName") or "").lower()
    return {
        "provider": "microsoft",
        "sub": info["id"],
        "email": email,
        "name": info.get("displayName", ""),
        "email_verified": True,  # Microsoft accounts have verified emails
        "access_token_hash": hashlib.sha256(token["access_token"].encode()).hexdigest(),
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

AUTHORIZE_URL_BUILDERS = {
    "google": google_authorize_url,
    "microsoft": microsoft_authorize_url,
}

CODE_EXCHANGERS = {
    "google": google_exchange_code,
    "microsoft": microsoft_exchange_code,
}
