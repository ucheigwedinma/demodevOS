from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings

from .models import DocumentSignatureRequest


@dataclass
class SignatureDispatchResult:
    envelope_id: str
    signing_url: str
    payload: dict


class BaseSignatureProviderAdapter:
    provider_key: str = ""
    provider_label: str = ""
    env_url_setting: str = ""

    def _base_signing_url(self) -> str:
        configured = getattr(settings, self.env_url_setting, "").strip()
        if configured:
            return configured.rstrip("/")
        return "https://signing.example.com"

    def send(self, signature_request: DocumentSignatureRequest) -> SignatureDispatchResult:
        envelope_id = str(uuid4())
        signing_url = f"{self._base_signing_url()}/{self.provider_key}/envelopes/{envelope_id}"
        payload = {
            "provider": self.provider_key,
            "provider_label": self.provider_label,
            "mode": "mock",
            "note": (
                "No provider credentials configured. Generated a mock envelope/sign URL. "
                "Set provider secrets and adapter implementation for live dispatch."
            ),
        }
        return SignatureDispatchResult(
            envelope_id=envelope_id,
            signing_url=signing_url,
            payload=payload,
        )


class DocuSignAdapter(BaseSignatureProviderAdapter):
    provider_key = DocumentSignatureRequest.Provider.DOCUSIGN
    provider_label = "DocuSign"
    env_url_setting = "DOCUMENT_ESIGN_DOCUSIGN_SIGNING_BASE_URL"


class AdobeAcrobatSignAdapter(BaseSignatureProviderAdapter):
    provider_key = DocumentSignatureRequest.Provider.ADOBE_ACROBAT_SIGN
    provider_label = "Adobe Acrobat Sign"
    env_url_setting = "DOCUMENT_ESIGN_ADOBE_SIGNING_BASE_URL"


class DropboxSignAdapter(BaseSignatureProviderAdapter):
    provider_key = DocumentSignatureRequest.Provider.DROPBOX_SIGN
    provider_label = "Dropbox Sign"
    env_url_setting = "DOCUMENT_ESIGN_DROPBOX_SIGNING_BASE_URL"


class SignNowAdapter(BaseSignatureProviderAdapter):
    provider_key = DocumentSignatureRequest.Provider.SIGNNOW
    provider_label = "SignNow"
    env_url_setting = "DOCUMENT_ESIGN_SIGNNOW_SIGNING_BASE_URL"


_ADAPTERS: dict[str, BaseSignatureProviderAdapter] = {
    DocumentSignatureRequest.Provider.DOCUSIGN: DocuSignAdapter(),
    DocumentSignatureRequest.Provider.ADOBE_ACROBAT_SIGN: AdobeAcrobatSignAdapter(),
    DocumentSignatureRequest.Provider.DROPBOX_SIGN: DropboxSignAdapter(),
    DocumentSignatureRequest.Provider.SIGNNOW: SignNowAdapter(),
}


def get_signature_provider_adapter(provider_key: str) -> BaseSignatureProviderAdapter:
    adapter = _ADAPTERS.get(provider_key)
    if adapter is None:
        raise ValueError(f"Unsupported e-signature provider '{provider_key}'.")
    return adapter


def signature_provider_options() -> list[dict[str, str]]:
    return [
        {"key": key, "label": adapter.provider_label}
        for key, adapter in _ADAPTERS.items()
    ]
