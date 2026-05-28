from __future__ import annotations

from django.apps import apps

GENERIC_CURRENCY_CODE = "XXX"


def _normalize_currency_code(value: object) -> str:
    if not isinstance(value, str):
        return ""
    code = value.strip().upper()
    if len(code) != 3 or not code.isalpha():
        return ""
    return code


def get_default_currency_code() -> str:
    try:
        MasterDataEntry = apps.get_model("settings", "MasterDataEntry")
        code = (
            MasterDataEntry.objects.filter(category="currency", is_active=True)
            .order_by("sort_order", "label")
            .values_list("code", flat=True)
            .first()
        )
        seeded = _normalize_currency_code(code)
        if seeded:
            return seeded
    except Exception:
        pass

    return GENERIC_CURRENCY_CODE
