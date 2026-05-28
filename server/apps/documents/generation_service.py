from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.utils import timezone

from .models import (
    Document,
    DocumentGenerationRecord,
    DocumentType,
    DocumentVersion,
)


@dataclass
class GenerationResult:
    generation_record: DocumentGenerationRecord
    document: Document
    version: DocumentVersion


def _branding_snapshot(*, user, request=None) -> dict[str, Any]:
    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)
    if organization is None:
        raise ValueError("You must belong to an organization to generate branded documents.")

    logo_url = ""
    if getattr(organization, "logo", None):
        logo_path = organization.logo.url
        logo_url = request.build_absolute_uri(logo_path) if request is not None else logo_path

    address_parts = [
        organization.address_line_1,
        organization.address_line_2,
        organization.city,
        organization.state_province,
        organization.postal_code,
        organization.country,
    ]
    address = ", ".join(part.strip() for part in address_parts if part and part.strip())
    return {
        "organization_id": organization.id,
        "name": organization.name,
        "legal_name": organization.legal_name,
        "trading_name": organization.trading_name,
        "registration_number": organization.registration_number,
        "tax_id": organization.tax_id,
        "email": organization.email,
        "phone": organization.phone,
        "website": organization.website,
        "address": address,
        "logo_url": logo_url,
    }


def _document_type_for_kind(generation_kind: str, *, preferred_code: str = "") -> DocumentType:
    preferred_code = (preferred_code or "").strip().lower()
    if preferred_code:
        preferred_type = DocumentType.objects.filter(
            code=preferred_code,
            is_active=True,
        ).first()
        if preferred_type:
            return preferred_type

    preferred_code_map = {
        DocumentGenerationRecord.GenerationKind.CONTRACT: "contract_agreement",
        DocumentGenerationRecord.GenerationKind.INVOICE: "invoice",
        DocumentGenerationRecord.GenerationKind.REPORT: "other",
    }
    preferred = preferred_code_map.get(generation_kind)

    if preferred:
        doc_type = DocumentType.objects.filter(code=preferred, is_active=True).first()
        if doc_type:
            return doc_type

    category_map = {
        DocumentGenerationRecord.GenerationKind.CONTRACT: "CON",
        DocumentGenerationRecord.GenerationKind.INVOICE: "FIN",
        DocumentGenerationRecord.GenerationKind.REPORT: "GEN",
    }
    fallback_category = category_map.get(generation_kind, "GEN")
    category_candidate = (
        DocumentType.objects
        .filter(category_code__iexact=fallback_category, is_active=True)
        .order_by("name")
        .first()
    )
    if category_candidate:
        return category_candidate

    any_type = DocumentType.objects.filter(is_active=True).order_by("name").first()
    if any_type:
        return any_type
    raise ValueError("No active document type is configured. Seed document types first.")


def _render_branded_html(*, generation_kind: str, title: str, summary: str, body: str, branding: dict, variables: dict):
    return render_to_string(
        "documents/generated/branded_document.html",
        {
            "generation_kind": generation_kind,
            "title": title,
            "summary": summary,
            "body_html": html.escape(body).replace("\n", "<br>"),
            "branding": branding,
            "variables": variables or {},
            "generated_at": timezone.now(),
        },
    )


def _persist_generated_file(*, document: Document, generation_kind: str, html_payload: str) -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    relative_path = f"documents/{document.id}/generated/{timestamp}_{generation_kind}.html"
    return default_storage.save(relative_path, ContentFile(html_payload.encode("utf-8")))


def generate_branded_document(
    *,
    request,
    user,
    validated_data: dict[str, Any],
) -> GenerationResult:
    generation_kind = validated_data["generation_kind"]
    title = validated_data["title"].strip()
    summary = (validated_data.get("summary") or "").strip()
    body = validated_data.get("body") or ""
    template_code = (validated_data.get("template_code") or "").strip()
    variables = validated_data.get("variables") or {}

    branding = _branding_snapshot(user=user, request=request)
    document_type = _document_type_for_kind(
        generation_kind,
        preferred_code=(validated_data.get("document_type_code") or ""),
    )

    document = Document.objects.create(
        organization_id=branding["organization_id"],
        title=title,
        project_code=(validated_data.get("project_code") or "").strip(),
        document_type=document_type,
        confidentiality_level=validated_data["confidentiality_level"],
        owner_role=validated_data["owner_role"],
        contract_value=validated_data.get("contract_value") or 0,
        business_unit_division=validated_data.get("business_unit_division"),
        business_unit_department=validated_data.get("business_unit_department"),
        project=validated_data.get("project"),
        land=validated_data.get("land"),
        unit=validated_data.get("unit"),
        client=validated_data.get("client"),
        vendor=validated_data.get("vendor"),
        phase=validated_data["phase"],
        status=Document.Status.DRAFT,
        retention_policy=validated_data["retention_policy"],
    )

    rendered_html = _render_branded_html(
        generation_kind=generation_kind,
        title=title,
        summary=summary,
        body=body,
        branding=branding,
        variables=variables,
    )
    file_path = _persist_generated_file(
        document=document,
        generation_kind=generation_kind,
        html_payload=rendered_html,
    )
    version = DocumentVersion.objects.create(
        organization_id=branding["organization_id"],
        document=document,
        version_major=1,
        version_minor=0,
        file_path=file_path,
        change_summary=(
            f"Auto-generated branded {generation_kind} document"
            + (f" ({template_code})" if template_code else "")
            + "."
        ),
        uploaded_by=user,
        approval_status=DocumentVersion.ApprovalStatus.PENDING,
    )

    generation_record = DocumentGenerationRecord.objects.create(
        organization_id=branding["organization_id"],
        document=document,
        document_version=version,
        generation_kind=generation_kind,
        title=title,
        template_code=template_code,
        branding_snapshot=branding,
        context_payload={
            "summary": summary,
            "variables": variables,
            "body_length": len(body),
        },
        file_path=file_path,
        requested_by=user,
    )
    return GenerationResult(
        generation_record=generation_record,
        document=document,
        version=version,
    )
