from builtins import property as builtin_property

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.settings.currency import get_default_currency_code


def _linked_facility(property_record):
    return getattr(property_record, "facility_registry", None) if property_record else None


def _derive_tenancy_relationships(instance):
    property_record = getattr(instance, "property", None)
    unit = getattr(instance, "unit", None)
    facility = getattr(instance, "facility", None)
    facility_space = getattr(instance, "facility_space", None)
    lease_agreement = getattr(instance, "lease_agreement", None)

    if lease_agreement is not None:
        property_record = property_record or lease_agreement.property
        unit = unit or lease_agreement.unit
        facility = facility or lease_agreement.facility
        facility_space = facility_space or lease_agreement.facility_space

    if facility_space is not None:
        return {
            "property": facility_space.facility.property,
            "unit": facility_space.unit,
            "facility": facility_space.facility,
            "facility_space": facility_space,
        }

    if unit is not None:
        linked_space = getattr(unit, "facility_space", None)
        derived_facility = facility
        derived_space = None
        if linked_space and linked_space.organization_id == getattr(instance, "organization_id", None):
            derived_space = linked_space
            derived_facility = linked_space.facility
        elif derived_facility is None:
            derived_facility = _linked_facility(unit.property)
        return {
            "property": unit.property,
            "unit": unit,
            "facility": derived_facility,
            "facility_space": derived_space,
        }

    if facility is not None:
        return {
            "property": facility.property,
            "unit": unit,
            "facility": facility,
            "facility_space": facility_space,
        }

    if property_record is not None:
        return {
            "property": property_record,
            "unit": unit,
            "facility": _linked_facility(property_record),
            "facility_space": facility_space,
        }

    tenant_profile = getattr(instance, "tenant_profile", None)
    if tenant_profile is None:
        return {
            "property": None,
            "unit": None,
            "facility": None,
            "facility_space": None,
        }

    property_record = tenant_profile.property
    unit = tenant_profile.unit
    facility = tenant_profile.facility
    facility_space = tenant_profile.facility_space
    if facility_space is not None:
        property_record = facility_space.facility.property
        unit = facility_space.unit
        facility = facility_space.facility
    elif unit is not None:
        property_record = unit.property
        linked_space = getattr(unit, "facility_space", None)
        if linked_space and linked_space.organization_id == getattr(instance, "organization_id", None):
            facility_space = linked_space
            facility = linked_space.facility
        elif facility is None:
            facility = _linked_facility(property_record)
    elif facility is not None:
        property_record = facility.property
    elif property_record is not None:
        facility = _linked_facility(property_record)
    return {
        "property": property_record,
        "unit": unit,
        "facility": facility,
        "facility_space": facility_space,
    }


def _apply_tenancy_relationship_defaults(instance):
    derived = _derive_tenancy_relationships(instance)
    for field_name in ("property", "unit", "facility", "facility_space"):
        if getattr(instance, f"{field_name}_id", None) is None and derived[field_name] is not None:
            setattr(instance, field_name, derived[field_name])
    return derived


def _validate_tenancy_relationships(instance, *, require_property=False, require_facility=False):
    errors = {}
    organization_id = getattr(instance, "organization_id", None)
    derived = _derive_tenancy_relationships(instance)

    for field_name in ("tenant_profile", "property", "unit", "facility", "facility_space"):
        related_obj = getattr(instance, field_name, None)
        if related_obj is not None and organization_id is not None and related_obj.organization_id != organization_id:
            errors[field_name] = [f"Selected {field_name.replace('_', ' ')} does not belong to this organization."]

    property_record = getattr(instance, "property", None) or derived["property"]
    facility = getattr(instance, "facility", None) or derived["facility"]
    unit = getattr(instance, "unit", None) or derived["unit"]
    facility_space = getattr(instance, "facility_space", None) or derived["facility_space"]

    if require_property and property_record is None:
        errors.setdefault("property", []).append("A lease relationship must link the tenant to a property.")

    if property_record is not None and require_facility and facility is None:
        errors.setdefault("facility", []).append("Selected property must belong to a facility.")

    if facility is not None and property_record is not None and facility.property_id != property_record.id:
        errors.setdefault("facility", []).append("Selected facility does not belong to the selected property.")

    if unit is not None and property_record is not None and unit.property_id != property_record.id:
        errors.setdefault("unit", []).append("Selected unit does not belong to the selected property.")

    if facility_space is not None:
        if facility is not None and facility_space.facility_id != facility.id:
            errors.setdefault("facility_space", []).append("Selected facility space does not belong to the selected facility.")
        if unit is not None and facility_space.unit_id != unit.id:
            errors.setdefault("facility_space", []).append("Selected facility space does not belong to the selected unit.")
        if property_record is not None and facility_space.facility.property_id != property_record.id:
            errors.setdefault("facility_space", []).append("Selected facility space does not belong to the selected property.")

    if errors:
        raise ValidationError(errors)


class TenantProfile(models.Model):
    """Tenant profile synced from facility allocations and CRM/finance records."""

    class TenantType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        CORPORATE = "corporate", "Corporate"

    class Status(models.TextChoices):
        PENDING_MOVE_IN = "pending_move_in", "Pending Move In"
        ACTIVE = "active", "Active"
        MOVED_OUT = "moved_out", "Moved Out"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_profiles",
    )
    customer = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    contact_account = models.ForeignKey(
        "crm.ContactAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    primary_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profiles",
    )
    tenant_type = models.CharField(
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.CORPORATE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_MOVE_IN,
    )
    display_name = models.CharField(max_length=255, blank=True)
    lease_start_date = models.DateField(null=True, blank=True)
    lease_end_date = models.DateField(null=True, blank=True)
    move_in_date = models.DateField(null=True, blank=True)
    move_out_date = models.DateField(null=True, blank=True)
    satisfaction_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    satisfaction_response_count = models.PositiveIntegerField(default=0)
    last_satisfaction_feedback_at = models.DateTimeField(null=True, blank=True)
    occupant_count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name", "id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_prof_org_status_idx"),
            models.Index(fields=["organization", "property"], name="tenant_prof_org_prop_idx"),
            models.Index(fields=["organization", "facility_space"], name="tenant_prof_org_space_idx"),
        ]

    def __str__(self):
        return self.resolved_display_name

    @builtin_property
    def resolved_display_name(self) -> str:
        if self.display_name:
            return self.display_name
        if self.customer_id and self.customer:
            return self.customer.name
        if self.contact_account_id and self.contact_account:
            return self.contact_account.display_name
        return f"Tenant {self.pk}"


class TenantCommunicationLog(models.Model):
    """Quick interaction history for tenant intelligence and recovery workflows."""

    class InteractionType(models.TextChoices):
        NOTE = "note", "Note"
        PHONE = "phone", "Phone Call"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        INVOICE_GENERATED = "invoice_generated", "Invoice Generated"
        PAYMENT_REMINDER = "payment_reminder", "Payment Reminder"
        EVICTION_NOTICE = "eviction_notice", "Eviction Notice"
        SYSTEM = "system", "System"

    class Channel(models.TextChoices):
        INTERNAL_NOTE = "internal_note", "Internal Note"
        PHONE = "phone", "Phone Call"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        SYSTEM = "system", "System"

    class Direction(models.TextChoices):
        INTERNAL = "internal", "Internal"
        OUTBOUND = "outbound", "Outbound"
        INBOUND = "inbound", "Inbound"

    class Status(models.TextChoices):
        RECORDED = "recorded", "Recorded"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_communication_logs",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="communication_logs",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_communication_logs",
    )
    interaction_type = models.CharField(
        max_length=30,
        choices=InteractionType.choices,
        default=InteractionType.NOTE,
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.INTERNAL_NOTE,
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.INTERNAL,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.RECORDED,
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    happened_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-happened_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "tenant_profile", "-happened_at"],
                name="tenant_comm_org_profile_idx",
            ),
            models.Index(
                fields=["organization", "interaction_type", "-happened_at"],
                name="tenant_comm_org_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.get_interaction_type_display()}"


class TenantIdentityDocument(models.Model):
    """Identity and compliance documents held against a tenant profile."""

    class DocumentType(models.TextChoices):
        NIN = "nin", "NIN"
        PASSPORT = "passport", "Passport"
        DRIVERS_LICENSE = "drivers_license", "Driver's License"
        NATIONAL_ID = "national_id", "National ID"
        RC_CERTIFICATE = "rc_certificate", "RC Certificate"
        TAX_ID = "tax_id", "Tax ID"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_identity_documents",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="identity_documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    document_number = models.CharField(max_length=120)
    holder_name = models.CharField(max_length=255, blank=True)
    issuing_country = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    scan_on_file = models.BooleanField(default=False)
    scan_reference = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "tenant_profile"],
                name="tent_iddoc_org_prof_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.get_document_type_display()}"


class TenantRelationshipContact(models.Model):
    """Next of kin and emergency contacts attached to a tenant profile."""

    class ContactRole(models.TextChoices):
        NEXT_OF_KIN = "next_of_kin", "Next of Kin"
        EMERGENCY = "emergency", "Emergency Contact"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_relationship_contacts",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="relationship_contacts",
    )
    contact_role = models.CharField(
        max_length=20,
        choices=ContactRole.choices,
        default=ContactRole.EMERGENCY,
    )
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=120)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["contact_role", "-is_primary", "full_name"]
        indexes = [
            models.Index(
                fields=["organization", "tenant_profile", "contact_role"],
                name="tent_rel_org_role_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.full_name}"


class TenantInventoryItem(models.Model):
    """Inventory checklist items handed over with the assigned unit/space."""

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"

    class Status(models.TextChoices):
        PROVIDED = "provided", "Provided"
        RETURNED = "returned", "Returned"
        MISSING = "missing", "Missing"
        DAMAGED = "damaged", "Damaged"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_inventory_items",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(
        max_length=10,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PROVIDED,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item_name", "id"]
        indexes = [
            models.Index(
                fields=["organization", "tenant_profile"],
                name="tent_inv_org_prof_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.item_name}"


class TenantIncidentRecord(models.Model):
    """Lease violations and tenant-linked operational incidents."""

    class IncidentType(models.TextChoices):
        LEASE_VIOLATION = "lease_violation", "Lease Violation"
        MAINTENANCE_ISSUE = "maintenance_issue", "Maintenance Issue"
        DAMAGE = "damage", "Damage"
        NOISE = "noise", "Noise Complaint"
        SECURITY = "security", "Security Incident"
        PAYMENT_BREACH = "payment_breach", "Payment Breach"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_incident_records",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="incident_records",
    )
    work_order = models.ForeignKey(
        "properties.WorkOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_incident_records",
    )
    incident_type = models.CharField(
        max_length=20,
        choices=IncidentType.choices,
        default=IncidentType.OTHER,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    occurred_at = models.DateField(default=timezone.localdate)
    resolved_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "tenant_profile", "status"],
                name="tent_inc_org_stat_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.title}"


class LeaseAgreement(models.Model):
    """Commercial lease contract and billing terms for a tenant profile."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        NOTICE_GIVEN = "notice_given", "Notice Given"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"
        TERMINATION_PENDING = "termination_pending", "Termination Pending"
        TERMINATED = "terminated", "Terminated"
        RENEWED = "renewed", "Renewed"
        ARCHIVED = "archived", "Archived"

    class PaymentFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        BIANNUAL = "biannual", "Biannual"
        ANNUAL = "annual", "Annual"

    class EscalationRule(models.TextChoices):
        NONE = "none", "None"
        FIXED = "fixed", "Fixed Amount"
        PERCENTAGE = "percentage", "Percentage"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lease_agreements",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="lease_agreements",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_agreements",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_agreements",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_agreements",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_agreements",
    )
    lease_code = models.CharField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    service_charge_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    security_deposit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default=get_default_currency_code)
    payment_frequency = models.CharField(
        max_length=20,
        choices=PaymentFrequency.choices,
        default=PaymentFrequency.MONTHLY,
    )
    escalation_rule = models.CharField(
        max_length=20,
        choices=EscalationRule.choices,
        default=EscalationRule.NONE,
    )
    escalation_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    escalation_frequency_months = models.PositiveIntegerField(default=12)
    notice_period_days = models.PositiveIntegerField(default=30)
    renewal_option = models.BooleanField(default=True)
    auto_generate_billing = models.BooleanField(default=True)
    next_billing_date = models.DateField(null=True, blank=True)
    last_billing_date = models.DateField(null=True, blank=True)
    last_escalation_date = models.DateField(null=True, blank=True)
    signed_on = models.DateField(null=True, blank=True)
    terminated_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["end_date", "tenant_profile__display_name", "id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_lease_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_lease_org_prof_idx"),
            models.Index(fields=["organization", "end_date"], name="tenant_lease_org_end_idx"),
        ]

    def __str__(self):
        return self.lease_code or f"Lease {self.pk}"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        if not self.lease_code:
            self.lease_code = self._generate_lease_code()
        super().save(**kwargs)

    @classmethod
    def _generate_lease_code(cls) -> str:
        import re

        last_numbers = cls.objects.filter(lease_code__regex=r"^LEASE-\d+$").values_list("lease_code", flat=True)
        max_seq = 0
        for code in last_numbers:
            match = re.search(r"LEASE-(\d+)$", code)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return f"LEASE-{max_seq + 1:05d}"


class OccupancyRecord(models.Model):
    """Move-in, notice, and move-out history for a tenant occupancy."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ACTIVE = "active", "Active"
        NOTICE_GIVEN = "notice_given", "Notice Given"
        VACATED = "vacated", "Vacated"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_occupancy_records",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="occupancy_records",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="occupancy_records",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_occupancy_records",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_occupancy_records",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_occupancy_records",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_occupancy_records",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
    )
    move_in_date = models.DateField()
    notice_date = models.DateField(null=True, blank=True)
    move_out_date = models.DateField(null=True, blank=True)
    vacated_on = models.DateField(null=True, blank=True)
    occupant_count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-move_in_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_occ_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_occ_org_prof_idx"),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} occupancy"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)
        errors = {}
        if self.move_out_date and self.move_in_date and self.move_out_date < self.move_in_date:
            errors["move_out_date"] = ["Move-out date cannot be before move-in date."]
        if self.vacated_on and self.move_in_date and self.vacated_on < self.move_in_date:
            errors["vacated_on"] = ["Vacated date cannot be earlier than the move-in date."]
        if errors:
            raise ValidationError(errors)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        super().save(**kwargs)


class LeaseRenewalRequest(models.Model):
    """Renewal workflow for expiring leases."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lease_renewal_requests",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="lease_renewal_requests",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="renewal_requests",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()
    proposed_rent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    proposed_service_charge_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    generated_automatically = models.BooleanField(default=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_renewals_requested",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_renewals_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["proposed_start_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_ren_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_ren_org_prof_idx"),
        ]

    def __str__(self):
        return f"Renewal {self.lease_agreement.lease_code}"


class LeaseTerminationRequest(models.Model):
    """Termination approval flow and notice tracking for leases."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lease_termination_requests",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="lease_termination_requests",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="termination_requests",
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.REQUESTED)
    requested_move_out_date = models.DateField()
    effective_date = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveIntegerField(default=30)
    reason = models.TextField(blank=True)
    generated_automatically = models.BooleanField(default=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_terminations_requested",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_terminations_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["requested_move_out_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_term_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_term_org_prof_idx"),
        ]

    def __str__(self):
        return f"Termination {self.lease_agreement.lease_code}"


class RecurringChargeRule(models.Model):
    """Automated recurring rent, service charge, utility, and concession rules."""

    class ChargeType(models.TextChoices):
        RENT = "rent", "Rent"
        SERVICE_CHARGE = "service_charge", "Service Charge"
        UTILITY = "utility", "Utility Bill"
        PENALTY = "penalty", "Penalty"
        DAMAGE = "damage", "Damage"
        DISCOUNT = "discount", "Discount"
        CONCESSION = "concession", "Concession"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ENDED = "ended", "Ended"

    class Frequency(models.TextChoices):
        ONCE = "once", "One-Time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        BIANNUAL = "biannual", "Biannual"
        ANNUAL = "annual", "Annual"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_recurring_charge_rules",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="recurring_charge_rules",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_charge_rules",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_recurring_charge_rules",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_recurring_charge_rules",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_recurring_charge_rules",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_recurring_charge_rules",
    )
    title = models.CharField(max_length=255)
    charge_type = models.CharField(max_length=20, choices=ChargeType.choices, default=ChargeType.RENT)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=10, default=get_default_currency_code)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_invoice_date = models.DateField(null=True, blank=True)
    last_invoiced_date = models.DateField(null=True, blank=True)
    applies_mid_period_proration = models.BooleanField(default=False)
    auto_invoice = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_invoice_date", "tenant_profile__display_name", "id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_charge_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_charge_org_prof_idx"),
            models.Index(fields=["organization", "next_invoice_date"], name="tenant_charge_org_next_idx"),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.title}"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": ["End date cannot be before the start date."]})

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        super().save(**kwargs)


class LeaseAccessProvisioning(models.Model):
    """Access activation state tied to a lease lifecycle."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lease_access_provisioning_records",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="lease_access_provisioning_records",
    )
    lease_agreement = models.OneToOneField(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="access_provisioning",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_access_provisioning_records",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_access_provisioning_records",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_access_provisioning_records",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_access_provisioning_records",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    facility_access_active = models.BooleanField(default=False)
    security_access_active = models.BooleanField(default=False)
    portal_access_active = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_access_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_access_org_profile_idx"),
        ]

    def __str__(self):
        return f"{self.lease_agreement.lease_code} access"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        if self.status == self.Status.ACTIVE and self.activated_at is None:
            self.activated_at = timezone.now()
        super().save(**kwargs)


class LeaseUtilityTracking(models.Model):
    """Utility tracking state tied to a lease lifecycle."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lease_utility_tracking_records",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="lease_utility_tracking_records",
    )
    lease_agreement = models.OneToOneField(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="utility_tracking",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_utility_tracking_records",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_utility_tracking_records",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_utility_tracking_records",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_utility_tracking_records",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    utility_tracking_active = models.BooleanField(default=False)
    tracked_utility_types = models.JSONField(default=list, blank=True)
    tracked_meter_count = models.PositiveIntegerField(default=0)
    visible_utility_bill_count = models.PositiveIntegerField(default=0)
    activated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tent_utktrk_org_stat_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tent_utktrk_org_prof_idx"),
        ]

    def __str__(self):
        return f"{self.lease_agreement.lease_code} utility tracking"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        if self.status == self.Status.ACTIVE and self.activated_at is None:
            self.activated_at = timezone.now()
        super().save(**kwargs)


class TenantVacancyRiskAlert(models.Model):
    """Forecasted vacancy risk for leases approaching expiry or exit."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATED = "mitigated", "Mitigated"
        RESOLVED = "resolved", "Resolved"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_vacancy_risk_alerts",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="vacancy_risk_alerts",
    )
    lease_agreement = models.OneToOneField(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="vacancy_risk_alert",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_vacancy_risk_alerts",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_vacancy_risk_alerts",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_vacancy_risk_alerts",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_vacancy_risk_alerts",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW)
    risk_score = models.PositiveSmallIntegerField(default=0)
    forecasted_vacancy_date = models.DateField(null=True, blank=True)
    days_to_vacancy = models.IntegerField(default=0)
    tenant_notified_at = models.DateTimeField(null=True, blank=True)
    admin_notified_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score", "forecasted_vacancy_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_vacancy_org_status_idx"),
            models.Index(fields=["organization", "risk_level"], name="tenant_vacancy_org_level_idx"),
            models.Index(fields=["organization", "forecasted_vacancy_date"], name="tenant_vacancy_org_date_idx"),
        ]

    def __str__(self):
        return f"{self.lease_agreement.lease_code} vacancy risk"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        if self.status == self.Status.RESOLVED:
            self.resolved_at = self.resolved_at or timezone.now()
        elif self.resolved_at is not None:
            self.resolved_at = None
        super().save(**kwargs)


class TenantDepositSettlement(models.Model):
    """Security deposit settlement state for terminated tenant leases."""

    class Status(models.TextChoices):
        PENDING_INSPECTION = "pending_inspection", "Pending Inspection"
        PENDING_REFUND = "pending_refund", "Pending Refund"
        PENDING_COLLECTION = "pending_collection", "Pending Collection"
        SETTLED = "settled", "Settled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_deposit_settlements",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="deposit_settlements",
    )
    lease_agreement = models.OneToOneField(
        "tenants.LeaseAgreement",
        on_delete=models.CASCADE,
        related_name="deposit_settlement",
    )
    inspection = models.ForeignKey(
        "tenants.TenantInspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deposit_settlements",
    )
    collection_invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_deposit_settlements",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_deposit_settlements",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_deposit_settlements",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_deposit_settlements",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_deposit_settlements",
    )
    move_out_date = models.DateField(null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    assessed_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    refundable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    additional_amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING_INSPECTION)
    ready_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "move_out_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_depstl_org_status_idx"),
            models.Index(fields=["organization", "move_out_date"], name="tenant_depstl_org_moveout_idx"),
        ]

    def __str__(self):
        return f"{self.lease_agreement.lease_code} deposit settlement"

    def sync_relationships(self):
        _apply_tenancy_relationship_defaults(self)

    def clean(self):
        super().clean()
        _validate_tenancy_relationships(self, require_property=True, require_facility=True)

    def save(self, **kwargs):
        self.sync_relationships()
        self.clean()
        if self.status == self.Status.SETTLED:
            self.settled_at = self.settled_at or timezone.now()
        elif self.settled_at is not None:
            self.settled_at = None
        if self.status != self.Status.PENDING_INSPECTION and self.ready_at is None:
            self.ready_at = timezone.now()
        elif self.status == self.Status.PENDING_INSPECTION:
            self.ready_at = None
        super().save(**kwargs)


class TenantDocumentRecord(models.Model):
    """Tenant contracts, KYC documents, receipts, and signed records."""

    class Category(models.TextChoices):
        LEASE_AGREEMENT = "lease_agreement", "Lease Agreement"
        ID_KYC = "id_kyc", "ID / KYC"
        PAYMENT_RECEIPT = "payment_receipt", "Payment Receipt"
        INSPECTION_REPORT = "inspection_report", "Inspection Report"
        SIGNED_DOCUMENT = "signed_document", "Signed Document"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING_SIGNATURE = "pending_signature", "Pending Signature"
        EXPIRED = "expired", "Expired"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_document_records",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="document_records",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_records",
    )
    inspection = models.ForeignKey(
        "tenants.TenantInspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_records",
    )
    invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_document_records",
    )
    payment = models.ForeignKey(
        "finance.InvoicePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_document_records",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=25, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    reference_number = models.CharField(max_length=120, blank=True)
    file_reference = models.CharField(max_length=255, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "category"], name="tenant_doc_org_cat_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_doc_org_prof_idx"),
            models.Index(fields=["organization", "status"], name="tenant_doc_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.title}"


class TenantInspection(models.Model):
    """Move-in, move-out, and periodic inspections for tenant spaces."""

    class InspectionType(models.TextChoices):
        MOVE_IN = "move_in", "Move-In"
        MOVE_OUT = "move_out", "Move-Out"
        PERIODIC = "periodic", "Periodic"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DISPUTED = "disputed", "Disputed"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_inspections",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="inspections",
    )
    lease_agreement = models.ForeignKey(
        "tenants.LeaseAgreement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspections",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_inspections",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_inspections",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_inspections",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_inspections",
    )
    inspection_type = models.CharField(max_length=20, choices=InspectionType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    title = models.CharField(max_length=255)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_inspections_handled",
    )
    checklist_summary = models.TextField(blank=True)
    damage_assessment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    security_deposit_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_date", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_insp_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_insp_org_prof_idx"),
            models.Index(fields=["organization", "scheduled_date"], name="tenant_insp_org_sched_idx"),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.title}"


class TenantComplaint(models.Model):
    """Tenant complaint and escalation workflow."""

    class Category(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance"
        BILLING = "billing", "Billing"
        SECURITY = "security", "Security"
        NOISE = "noise", "Noise"
        CLEANLINESS = "cleanliness", "Cleanliness"
        COMMUNICATION = "communication", "Communication"
        LEGAL = "legal", "Legal"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        ESCALATED = "escalated", "Escalated"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_complaints",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints",
    )
    service_request = models.ForeignKey(
        "properties.ServiceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_complaints_assigned",
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sla_target_hours = models.PositiveIntegerField(default=24)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    feedback_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_cmp_org_status_idx"),
            models.Index(fields=["organization", "tenant_profile"], name="tenant_cmp_org_prof_idx"),
            models.Index(fields=["organization", "sla_due_at"], name="tenant_cmp_org_sla_idx"),
        ]

    def __str__(self):
        return f"{self.tenant_profile.resolved_display_name} — {self.subject}"


class TenantBroadcast(models.Model):
    """Broadcast announcements and engagement messages to tenant audiences."""

    class AudienceType(models.TextChoices):
        ALL_TENANTS = "all_tenants", "All Tenants"
        PROPERTY = "property", "Specific Property"
        FACILITY = "facility", "Specific Facility"
        TENANT_TYPE = "tenant_type", "Tenant Type"
        DELINQUENT = "delinquent", "Delinquent Tenants"
        LEASE_EXPIRY = "lease_expiry", "Expiring Leases"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        PARTIAL = "partial", "Partially Sent"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tenant_broadcasts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_broadcasts_created",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_broadcasts",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_broadcasts",
    )
    audience_type = models.CharField(max_length=20, choices=AudienceType.choices, default=AudienceType.ALL_TENANTS)
    tenant_type_filter = models.CharField(
        max_length=20,
        choices=TenantProfile.TenantType.choices,
        blank=True,
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    send_email = models.BooleanField(default=True)
    send_whatsapp = models.BooleanField(default=False)
    send_in_app = models.BooleanField(default=True)
    recipient_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="tenant_brd_org_status_idx"),
            models.Index(fields=["organization", "audience_type"], name="tenant_brd_org_aud_idx"),
        ]

    def __str__(self):
        return self.subject
