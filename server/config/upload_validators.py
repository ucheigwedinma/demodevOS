"""
Reusable file upload validators for Django FileField / ImageField.

Usage in serializers:

    from config.upload_validators import validate_upload

    def validate_file(self, value):
        return validate_upload(value, kind="document")

    def validate_image(self, value):
        return validate_upload(value, kind="image")
"""

import os

from django.core.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Allowed extensions by category
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {
    "document": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf",
        ".xls", ".xlsx", ".csv",
        ".ppt", ".pptx",
        ".dwg", ".dxf",
        ".zip", ".rar", ".7z",
    },
    "image": {
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".bmp", ".tiff", ".tif", ".svg",
    },
    "any": None,  # document + image combined
}

# Merge for "any"
ALLOWED_EXTENSIONS["any"] = ALLOWED_EXTENSIONS["document"] | ALLOWED_EXTENSIONS["image"]

# MIME prefixes accepted per category
ALLOWED_MIME_PREFIXES = {
    "document": (
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "text/plain",
        "text/csv",
        "text/rtf",
        "application/rtf",
        "application/zip",
        "application/x-rar",
        "application/x-7z-compressed",
        "application/acad",
        "application/dxf",
        "application/octet-stream",  # CAD files often report this
    ),
    "image": (
        "image/",
    ),
}

ALLOWED_MIME_PREFIXES["any"] = ALLOWED_MIME_PREFIXES["document"] + ALLOWED_MIME_PREFIXES["image"]

# ---------------------------------------------------------------------------
# Default size limits (megabytes)
# ---------------------------------------------------------------------------
DEFAULT_MAX_MB = {
    "document": 20,
    "image": 5,
    "any": 20,
}


def validate_upload(file, *, kind="any", max_mb=None):
    """
    Validate an uploaded file's extension, MIME type, and size.

    Parameters
    ----------
    file : InMemoryUploadedFile / TemporaryUploadedFile
        The uploaded file from ``request.FILES`` or a serializer field.
    kind : str
        One of ``"document"``, ``"image"``, or ``"any"`` (default).
    max_mb : int | None
        Maximum file size in megabytes.  Falls back to DEFAULT_MAX_MB[kind].

    Returns
    -------
    file
        The original file object if validation passes.

    Raises
    ------
    ValidationError
        If the file fails any check.
    """
    if file is None:
        return file

    if max_mb is None:
        max_mb = DEFAULT_MAX_MB.get(kind, 50)

    # --- Extension check ---
    ext = os.path.splitext(file.name)[1].lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(kind, ALLOWED_EXTENSIONS["any"])
    if ext not in allowed_exts:
        raise ValidationError(
            f"File type '{ext}' is not allowed. "
            f"Accepted: {', '.join(sorted(allowed_exts))}"
        )

    # --- MIME type check ---
    content_type = getattr(file, "content_type", "") or ""
    mime_prefixes = ALLOWED_MIME_PREFIXES.get(kind, ALLOWED_MIME_PREFIXES["any"])
    if not any(content_type.startswith(prefix) for prefix in mime_prefixes):
        raise ValidationError(
            f"File content type '{content_type}' is not allowed for {kind} uploads."
        )

    # --- Size check ---
    max_bytes = max_mb * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f"File size {file.size / (1024 * 1024):.1f} MB exceeds "
            f"the {max_mb} MB limit."
        )

    return file
