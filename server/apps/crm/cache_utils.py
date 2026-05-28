from django.core.cache import cache

CRM_CACHE_VERSION_KEY = "crm:cache-version:org:{org_id}"
DEFAULT_CACHE_VERSION = 1


def _version_key(org_id: int) -> str:
    return CRM_CACHE_VERSION_KEY.format(org_id=org_id)


def get_crm_cache_version(org_id: int | None) -> int:
    if not org_id:
        return DEFAULT_CACHE_VERSION
    value = cache.get(_version_key(org_id))
    if value is None:
        cache.set(_version_key(org_id), DEFAULT_CACHE_VERSION, timeout=None)
        return DEFAULT_CACHE_VERSION
    try:
        return int(value)
    except (TypeError, ValueError):
        cache.set(_version_key(org_id), DEFAULT_CACHE_VERSION, timeout=None)
        return DEFAULT_CACHE_VERSION


def bump_crm_cache_version(org_id: int | None) -> int:
    if not org_id:
        return DEFAULT_CACHE_VERSION
    key = _version_key(org_id)
    try:
        return cache.incr(key)
    except ValueError:
        current = get_crm_cache_version(org_id)
        updated = current + 1
        cache.set(key, updated, timeout=None)
        return updated
