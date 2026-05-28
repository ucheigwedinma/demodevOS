"""
Proprietary implementation removed for public demo.
This module exists in production — business logic not published.
Live product: https://developeros.pro
"""

from __future__ import annotations
from apps.settings.models import Role
from .models import Approver, ProcessAuthority, ProcessWorkflowStep, WorkflowRole

def seed_process_authority_for_org(org, *, reset: bool = False) -> dict[str, int]:
    pass  # implementation not published
