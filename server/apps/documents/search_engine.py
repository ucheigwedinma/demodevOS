from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from django.conf import settings
from django.contrib.postgres.search import SearchVector
from django.db import connection, models, transaction
from django.utils import timezone

from .models import Document, DocumentSearchIndex, DocumentVersion

logger = logging.getLogger(__name__)


def _resolve_file_path(file_path: str) -> Path | None:
    if not file_path:
        return None

    path = Path(file_path)
    if path.is_absolute() and path.exists():
        return path

    media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "")
    if media_root:
        candidate = media_root / file_path
        if candidate.exists():
            return candidate
    return None


def _extract_pdf_text(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except Exception:  # pragma: no cover - optional dependency
        return "", "pypdf_unavailable"

    try:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                chunks.append(text)
        return "\n\n".join(chunks), "ok"
    except Exception as exc:  # pragma: no cover - parser/runtime dependent
        return "", f"pdf_extract_error:{exc}"


def _extract_pdf_ocr_text(path: Path) -> tuple[str, str]:
    if not getattr(settings, "DOCUMENT_OCR_ENABLED", False):
        return "", "ocr_disabled"

    try:
        import pytesseract
        from pdf2image import convert_from_path
    except Exception:  # pragma: no cover - optional dependency
        return "", "ocr_dependencies_unavailable"

    lang = getattr(settings, "DOCUMENT_OCR_LANG", "eng")
    dpi = int(getattr(settings, "DOCUMENT_OCR_DPI", 220))
    max_pages = int(getattr(settings, "DOCUMENT_OCR_MAX_PAGES", 20))

    try:
        images = convert_from_path(str(path), dpi=dpi, first_page=1, last_page=max_pages)
        chunks = []
        for image in images:
            text = (pytesseract.image_to_string(image, lang=lang) or "").strip()
            if text:
                chunks.append(text)
        return "\n\n".join(chunks), "ok"
    except Exception as exc:  # pragma: no cover - ocr runtime dependent
        return "", f"ocr_error:{exc}"


def _extract_plain_text(path: Path) -> tuple[str, str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore"), "ok"
    except Exception as exc:
        return "", f"text_extract_error:{exc}"


def _extract_clauses(text: str, max_clauses: int = 500) -> list[str]:
    if not text:
        return []

    normalized = re.sub(r"\r\n?", "\n", text)
    parts = re.split(r"\n+|(?<=[.;:])\s+", normalized)
    clauses: list[str] = []
    seen: set[str] = set()

    for part in parts:
        clause = " ".join(part.split()).strip()
        if len(clause) < 12:
            continue
        lowered = clause.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        clauses.append(clause)
        if len(clauses) >= max_clauses:
            break
    return clauses


def _compute_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_version(document: Document) -> DocumentVersion | None:
    return (
        document.versions
        .order_by("-version_major", "-version_minor", "-uploaded_at")
        .first()
    )


def build_search_index_for_document(document: Document, force: bool = False) -> DocumentSearchIndex:
    version = document.current_version or _latest_version(document)
    index, _ = DocumentSearchIndex.objects.get_or_create(
        document=document,
        defaults={"organization": document.organization},
    )

    if not version:
        index.index_status = DocumentSearchIndex.IndexStatus.FAILED
        index.error_message = "No document version available for indexing."
        index.indexed_at = timezone.now()
        index.save()
        return index

    file_path = _resolve_file_path(version.file_path)
    if file_path is None:
        index.document_version = version
        index.index_status = DocumentSearchIndex.IndexStatus.FAILED
        index.error_message = f"File not found: {version.file_path}"
        index.indexed_at = timezone.now()
        index.save()
        return index

    suffix = file_path.suffix.lower()
    extracted_text = ""
    ocr_text = ""
    errors: list[str] = []

    if suffix == ".pdf":
        extracted_text, pdf_state = _extract_pdf_text(file_path)
        if pdf_state != "ok":
            errors.append(pdf_state)
        ocr_text, ocr_state = _extract_pdf_ocr_text(file_path)
        if ocr_state not in ("ok", "ocr_disabled"):
            errors.append(ocr_state)
    else:
        extracted_text, text_state = _extract_plain_text(file_path)
        if text_state != "ok":
            errors.append(text_state)

    combined_text = "\n".join(part for part in [extracted_text, ocr_text] if part).strip()
    clauses = _extract_clauses(combined_text)
    clause_text = "\n".join(clauses)
    content_hash = _compute_hash(combined_text)

    if (
        not force
        and index.content_hash == content_hash
        and index.document_version_id == version.id
        and index.index_status == DocumentSearchIndex.IndexStatus.INDEXED
    ):
        return index

    index.document_version = version
    index.extracted_text = extracted_text
    index.ocr_text = ocr_text
    index.indexed_clauses = clauses
    index.clause_text = clause_text
    index.combined_text = combined_text
    index.content_hash = content_hash
    index.indexed_at = timezone.now()

    if combined_text:
        index.index_status = DocumentSearchIndex.IndexStatus.INDEXED
        index.error_message = "; ".join(errors)
    else:
        index.index_status = DocumentSearchIndex.IndexStatus.FAILED
        index.error_message = "; ".join(errors) or "No extractable text found."

    index.save()

    if connection.vendor == "postgresql":
        DocumentSearchIndex.objects.filter(pk=index.pk).update(
            search_vector=SearchVector(models.Value(index.combined_text), config="english")
        )

    return index


def build_search_index_for_document_id(document_id: int, force: bool = False) -> DocumentSearchIndex:
    document = (
        Document.objects
        .select_related("current_version")
        .prefetch_related("versions")
        .get(id=document_id)
    )
    return build_search_index_for_document(document=document, force=force)


def rebuild_search_index(*, organization_id: int, force: bool = False) -> dict[str, int]:
    created_or_updated = 0
    failed = 0

    queryset = Document.objects.filter(organization_id=organization_id).order_by("id")
    for document in queryset:
        index = build_search_index_for_document(document=document, force=force)
        created_or_updated += 1
        if index.index_status == DocumentSearchIndex.IndexStatus.FAILED:
            failed += 1

    return {
        "processed": created_or_updated,
        "failed": failed,
        "indexed": created_or_updated - failed,
    }


def schedule_document_reindex(document_id: int, force: bool = True) -> None:
    def _run():
        try:
            build_search_index_for_document_id(document_id=document_id, force=force)
        except Exception:
            logger.exception("Failed to reindex document %s", document_id)

    transaction.on_commit(_run)
