"""
Proprietary implementation removed for public demo.
This module exists in production — business logic not published.
Live product: https://developeros.pro
"""

from __future__ import annotations
from collections.abc import Mapping
from .models import DataScope, Role, RoleScope, UserScopeAssignment

def seed_data_scope_catalog() -> dict[str, DataScope]:
    pass  # implementation not published

def _upsert_role_scope(
    *,
    role: Role,
    module: str,
    data_scope: DataScope,
    reset: bool,
) -> tuple[int, int]:
    pass  # implementation not published

def seed_role_scopes_for_org(org, *, reset: bool = False) -> tuple[int, int]:
    pass  # implementation not published

def _default_scope_map_for_profile(profile) -> Mapping[str, str] | None:
    pass  # implementation not published

def seed_user_scope_assignments_for_org(org, *, reset: bool = False) -> tuple[int, int]:
    pass  # implementation not published
