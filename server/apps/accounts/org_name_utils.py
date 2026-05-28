"""
Organization name normalization and duplicate-detection utilities.

Used by registration, company setup, and check-company serializers
to prevent near-duplicate organizations from being created.
"""

import re
import unicodedata

# ── Business suffix list (ordered longest-first) ──────────────────────────────

BUSINESS_SUFFIXES = [
    "limited liability company",
    "limited liability partnership",
    "gesellschaft mit beschrankter haftung",
    "public limited company",
    "private limited",
    "proprietary limited",
    "societe anonyme",
    "sociedad anonima",
    "incorporated",
    "corporation",
    "proprietary",
    "limited",
    "company",
    "pty ltd",
    "corp",
    "inc",
    "llc",
    "llp",
    "plc",
    "ltd",
    "pty",
    "gmbh",
    "ag",
    "sa",
    "sl",
    "co",
    "nv",
    "bv",
]

_SUFFIX_PATTERN = re.compile(
    r"[,.]?\s+(?:" + "|".join(re.escape(s) for s in BUSINESS_SUFFIXES) + r")\.?\s*$",
    re.IGNORECASE,
)

# ── Free email providers (never used for domain matching) ─────────────────────

FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk", "yahoo.co.in",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "aol.com",
    "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me",
    "tutanota.com", "tuta.io",
    "zoho.com",
    "yandex.com", "yandex.ru",
    "mail.com", "gmx.com", "gmx.net",
    "fastmail.com",
    "pm.me",
})


# ── Public API ────────────────────────────────────────────────────────────────

def normalize_org_name(name: str) -> str:
    """
    Normalize an organization name for duplicate-detection comparison.

    "Orange Ltd", "orange limited", "ORANGE, LLC" all normalize to "orange".
    """
    # Unicode normalize → strip combining marks (accents)
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()

    # Strip business suffixes (multi-pass for compound suffixes like "Pty Ltd")
    for _ in range(3):
        prev = text
        text = _SUFFIX_PATTERN.sub("", text).strip()
        if text == prev:
            break

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip trailing punctuation
    text = re.sub(r"[.,\-]+$", "", text).strip()

    return text


def extract_email_domain(email: str) -> str:
    """
    Extract the domain from an email address.
    Returns empty string for free email providers.
    """
    if "@" not in email:
        return ""
    domain = email.strip().lower().rsplit("@", 1)[-1]
    if domain in FREE_EMAIL_DOMAINS:
        return ""
    return domain


def find_similar_organizations(name: str, threshold: float = 0.4, limit: int = 5):
    """
    Find organizations with similar normalized names using PostgreSQL
    trigram similarity.  Returns a queryset.
    """
    from django.contrib.postgres.search import TrigramSimilarity

    from .models import Organization

    normalized = normalize_org_name(name)
    if not normalized:
        return Organization.objects.none()

    return (
        Organization.objects
        .exclude(name__startswith="Workspace-")
        .annotate(similarity=TrigramSimilarity("normalized_name", normalized))
        .filter(similarity__gt=threshold)
        .order_by("-similarity")[:limit]
    )
