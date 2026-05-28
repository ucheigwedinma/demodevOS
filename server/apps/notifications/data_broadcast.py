"""
Generic data change broadcaster.

Registers post_save/post_delete signals on key models to broadcast
`data.changed` events via WebSocket to all users in the org.

Import this module in notifications/apps.py ready() to activate.

Frontend pages listen to `ws.lastDataChange` and auto-refetch when
the model name matches their data source.
"""

import logging

from django.db.models.signals import post_delete, post_save

logger = logging.getLogger(__name__)

# Models to broadcast changes for: (app_label.ModelName, display_name)
BROADCAST_MODELS = [
    # Procurement
    ("procurement.PurchaseRequisition", "PurchaseRequisition"),
    ("procurement.PurchaseOrder", "PurchaseOrder"),
    ("procurement.RequestForQuotation", "RFQ"),
    ("procurement.GoodsReceipt", "GoodsReceipt"),
    ("procurement.Vendor", "Vendor"),
    ("procurement.Contract", "Contract"),
    # Finance
    ("finance.Bill", "Bill"),
    ("finance.Invoice", "Invoice"),
    ("finance.Budget", "Budget"),
    # Inventory
    ("inventory.InventoryItem", "InventoryItem"),
    ("inventory.InventoryStock", "InventoryStock"),
    ("inventory.BillOfMaterials", "BillOfMaterials"),
    ("inventory.MaterialRequisition", "MaterialRequisition"),
    ("inventory.MaterialTransfer", "MaterialTransfer"),
    # Projects
    ("projects.Project", "Project"),
    ("projects.ProjectPhase", "ProjectPhase"),
    ("projects.ProjectTask", "ProjectTask"),
    ("projects.ProjectWorkPackage", "WorkPackage"),
    ("projects.ProjectVariationOrder", "VariationOrder"),
    ("projects.ProjectExecutionInspection", "QualityInspection"),
    ("projects.ProjectDailySiteReport", "DailySiteReport"),
    ("projects.NonConformanceReport", "NCR"),
    ("projects.RFI", "RFI"),
    ("projects.SiteInstruction", "SiteInstruction"),
    ("projects.StageGate", "StageGate"),
    ("projects.ProjectPermit", "Permit"),
    ("projects.CostCodeBudget", "CostCodeBudget"),
    ("projects.InterimValuation", "InterimValuation"),
    # Construction
    ("projects.HSEIncident", "HSEIncident"),
    ("projects.HSEPermitToWork", "HSEPermit"),
    ("projects.CommissioningPlan", "CommissioningPlan"),
    ("projects.ConstructionReport", "ConstructionReport"),
    # HR
    ("hr.EmployeeRecord", "Employee"),
    ("hr.LeaveRequest", "LeaveRequest"),
    # CRM
    ("crm.Lead", "Lead"),
    ("crm.UnitReservation", "Reservation"),
    # Tenants
    ("tenants.LeaseAgreement", "Lease"),
    # Meetings
    ("meetings.Meeting", "Meeting"),
    ("meetings.MeetingActionItem", "MeetingActionItem"),
    # Support
    ("support_desk.SupportTicket", "Ticket"),
    # Documents
    ("documents.Document", "Document"),
]


def _get_org_id(instance):
    """Extract organization ID from any model instance."""
    # Direct org FK
    if hasattr(instance, "organization_id") and instance.organization_id:
        return instance.organization_id
    if hasattr(instance, "organization") and instance.organization:
        return instance.organization.pk
    # Through project
    if hasattr(instance, "project") and instance.project and hasattr(instance.project, "organization_id"):
        return instance.project.organization_id
    # Through other relations
    for attr in ("bill", "purchase_order", "lease", "meeting", "ticket", "document"):
        rel = getattr(instance, attr, None)
        if rel and hasattr(rel, "organization_id"):
            return rel.organization_id
    return None


def _get_summary(instance) -> str:
    """Build a short summary string for the change event."""
    # Try common patterns
    for attr in ("__str__", "title", "name"):
        if attr == "__str__":
            try:
                s = str(instance)
                if s and len(s) < 120:
                    return s
            except Exception:
                pass
        else:
            val = getattr(instance, attr, None)
            if val:
                return str(val)[:100]
    return f"#{instance.pk}"


def _make_handler(model_label, display_name):
    """Create a signal handler for a specific model."""

    def on_save(sender, instance, created, **kwargs):
        org_id = _get_org_id(instance)
        if not org_id:
            return
        try:
            from apps.notifications.broadcast import broadcast_data_change
            broadcast_data_change(
                org_id=org_id,
                model=display_name,
                action="created" if created else "updated",
                id=instance.pk,
                summary=_get_summary(instance),
            )
        except Exception:
            pass  # Never break the save

    def on_delete(sender, instance, **kwargs):
        org_id = _get_org_id(instance)
        if not org_id:
            return
        try:
            from apps.notifications.broadcast import broadcast_data_change
            broadcast_data_change(
                org_id=org_id,
                model=display_name,
                action="deleted",
                id=instance.pk,
                summary=_get_summary(instance),
            )
        except Exception:
            pass

    on_save.__name__ = f"broadcast_{display_name}_save"
    on_delete.__name__ = f"broadcast_{display_name}_delete"
    return on_save, on_delete


def register_all_broadcasters():
    """Connect post_save/post_delete signals for all registered models."""
    for model_label, display_name in BROADCAST_MODELS:
        on_save, on_delete = _make_handler(model_label, display_name)
        post_save.connect(on_save, sender=model_label, weak=False)
        post_delete.connect(on_delete, sender=model_label, weak=False)

    logger.debug(f"Registered data change broadcasters for {len(BROADCAST_MODELS)} models")
