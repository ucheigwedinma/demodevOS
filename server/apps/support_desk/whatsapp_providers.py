from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from urllib import error as urlerror
from urllib import parse, request
from uuid import uuid4

from django.conf import settings


@dataclass
class WhatsAppDispatchResult:
    provider_key: str
    provider_label: str
    mode: str
    status: str
    provider_message_id: str
    payload: dict


class BaseWhatsAppProviderAdapter:
    provider_key: str = ""
    provider_label: str = ""

    def is_configured(self) -> bool:
        return False

    def send_message(
        self,
        *,
        recipient_phone: str,
        message: str,
        metadata: dict | None = None,
    ) -> WhatsAppDispatchResult:
        if not self.is_configured():
            return self._mock_result(recipient_phone=recipient_phone, message=message, metadata=metadata)
        return self._send_live(recipient_phone=recipient_phone, message=message, metadata=metadata)

    def _send_live(
        self,
        *,
        recipient_phone: str,
        message: str,
        metadata: dict | None = None,
    ) -> WhatsAppDispatchResult:
        raise NotImplementedError

    def _mock_result(
        self,
        *,
        recipient_phone: str,
        message: str,
        metadata: dict | None = None,
    ) -> WhatsAppDispatchResult:
        provider_message_id = f"mock-{uuid4()}"
        payload = {
            "provider": self.provider_key,
            "provider_label": self.provider_label,
            "mode": "mock",
            "status": "queued",
            "recipient_phone": recipient_phone,
            "message_length": len(message),
            "note": (
                "Provider credentials were not configured. "
                "Dispatch was recorded in mock mode."
            ),
            "metadata": metadata or {},
        }
        return WhatsAppDispatchResult(
            provider_key=self.provider_key,
            provider_label=self.provider_label,
            mode="mock",
            status="queued",
            provider_message_id=provider_message_id,
            payload=payload,
        )

    def _post_json(self, url: str, body: dict, headers: dict[str, str]) -> tuple[int, dict]:
        encoded = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/json")
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            with request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else {}
        except urlerror.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            details = {}
            if raw:
                try:
                    details = json.loads(raw)
                except json.JSONDecodeError:
                    details = {"raw": raw}
            raise RuntimeError(f"Provider HTTP {exc.code}: {details or 'unknown error'}") from exc
        except urlerror.URLError as exc:
            raise RuntimeError(f"Provider connection error: {exc.reason}") from exc


class MockWhatsAppAdapter(BaseWhatsAppProviderAdapter):
    provider_key = "mock"
    provider_label = "Mock Provider"

    def is_configured(self) -> bool:
        return False


class MetaCloudWhatsAppAdapter(BaseWhatsAppProviderAdapter):
    provider_key = "meta_cloud"
    provider_label = "Meta Cloud API"

    def _access_token(self) -> str:
        return getattr(settings, "SUPPORT_DESK_WHATSAPP_META_ACCESS_TOKEN", "").strip()

    def _phone_number_id(self) -> str:
        return getattr(settings, "SUPPORT_DESK_WHATSAPP_META_PHONE_NUMBER_ID", "").strip()

    def _api_base_url(self) -> str:
        configured = getattr(
            settings,
            "SUPPORT_DESK_WHATSAPP_META_API_BASE_URL",
            "https://graph.facebook.com/v20.0",
        ).strip()
        return configured.rstrip("/")

    def is_configured(self) -> bool:
        return bool(self._access_token() and self._phone_number_id())

    def _send_live(self, *, recipient_phone: str, message: str, metadata: dict | None = None) -> WhatsAppDispatchResult:
        url = f"{self._api_base_url()}/{self._phone_number_id()}/messages"
        body = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message},
        }
        status_code, data = self._post_json(
            url,
            body,
            headers={"Authorization": f"Bearer {self._access_token()}"},
        )

        provider_message_id = ""
        messages = data.get("messages") if isinstance(data, dict) else None
        if isinstance(messages, list) and messages:
            provider_message_id = str(messages[0].get("id", "")).strip()
        if not provider_message_id:
            provider_message_id = f"meta-{uuid4()}"

        payload = {
            "provider": self.provider_key,
            "provider_label": self.provider_label,
            "mode": "live",
            "status_code": status_code,
            "response": data,
            "metadata": metadata or {},
        }
        return WhatsAppDispatchResult(
            provider_key=self.provider_key,
            provider_label=self.provider_label,
            mode="live",
            status="sent" if 200 <= status_code < 300 else "failed",
            provider_message_id=provider_message_id,
            payload=payload,
        )


class TwilioWhatsAppAdapter(BaseWhatsAppProviderAdapter):
    provider_key = "twilio"
    provider_label = "Twilio WhatsApp"

    def _account_sid(self) -> str:
        return getattr(settings, "SUPPORT_DESK_WHATSAPP_TWILIO_ACCOUNT_SID", "").strip()

    def _auth_token(self) -> str:
        return getattr(settings, "SUPPORT_DESK_WHATSAPP_TWILIO_AUTH_TOKEN", "").strip()

    def _from_number(self) -> str:
        return getattr(settings, "SUPPORT_DESK_WHATSAPP_TWILIO_FROM_NUMBER", "").strip()

    def is_configured(self) -> bool:
        return bool(self._account_sid() and self._auth_token() and self._from_number())

    def _send_live(self, *, recipient_phone: str, message: str, metadata: dict | None = None) -> WhatsAppDispatchResult:
        sid = self._account_sid()
        token = self._auth_token()
        from_number = self._from_number()
        to_number = recipient_phone
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        form_payload = parse.urlencode(
            {
                "To": to_number,
                "From": from_number,
                "Body": message,
            }
        ).encode("utf-8")

        auth_header = base64.b64encode(f"{sid}:{token}".encode()).decode("utf-8")
        req = request.Request(url, data=form_payload, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Authorization", f"Basic {auth_header}")

        try:
            with request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                provider_message_id = str(data.get("sid") or f"twilio-{uuid4()}")
                payload = {
                    "provider": self.provider_key,
                    "provider_label": self.provider_label,
                    "mode": "live",
                    "status_code": response.status,
                    "response": data,
                    "metadata": metadata or {},
                }
                return WhatsAppDispatchResult(
                    provider_key=self.provider_key,
                    provider_label=self.provider_label,
                    mode="live",
                    status=str(data.get("status") or "queued"),
                    provider_message_id=provider_message_id,
                    payload=payload,
                )
        except urlerror.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            details = {}
            if raw:
                try:
                    details = json.loads(raw)
                except json.JSONDecodeError:
                    details = {"raw": raw}
            raise RuntimeError(f"Provider HTTP {exc.code}: {details or 'unknown error'}") from exc
        except urlerror.URLError as exc:
            raise RuntimeError(f"Provider connection error: {exc.reason}") from exc


_ADAPTERS: dict[str, BaseWhatsAppProviderAdapter] = {
    "mock": MockWhatsAppAdapter(),
    "meta_cloud": MetaCloudWhatsAppAdapter(),
    "twilio": TwilioWhatsAppAdapter(),
}


def get_whatsapp_provider_adapter(provider_key: str | None = None) -> BaseWhatsAppProviderAdapter:
    resolved_key = (provider_key or "").strip().lower()
    if not resolved_key:
        resolved_key = getattr(settings, "SUPPORT_DESK_WHATSAPP_PROVIDER", "mock").strip().lower() or "mock"

    adapter = _ADAPTERS.get(resolved_key)
    if adapter is None:
        raise ValueError(
            f"Unsupported WhatsApp provider '{resolved_key}'. "
            f"Supported providers: {', '.join(sorted(_ADAPTERS.keys()))}."
        )
    return adapter


def whatsapp_provider_options() -> list[dict[str, str]]:
    return [{"key": key, "label": adapter.provider_label} for key, adapter in _ADAPTERS.items()]
