import os
from uuid import uuid4

from django.conf import settings
from django.db import models


def facility_document_path(instance, filename):
    """Upload path for facility-scoped document records."""

    ext = os.path.splitext(filename or "")[1]
    facility_token = f"facility_{instance.facility_id}" if instance.facility_id else "facility_unassigned"
    return (
        f"facility_documents/org_{instance.organization_id}/{facility_token}/"
        f"{instance.document_type}/{uuid4().hex}{ext}"
    )


class Facility(models.Model):
    """Facility registry record mapped to a managed property."""

    class FacilityClassification(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        COMMERCIAL = "commercial", "Commercial"
        INDUSTRIAL = "industrial", "Industrial"
        MIXED_USE = "mixed_use", "Mixed Use"

    class OwnershipType(models.TextChoices):
        OWNED = "owned", "Owned"
        LEASED = "leased", "Leased"
        MANAGED = "managed", "Managed"
        MIXED = "mixed", "Mixed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_registry",
    )
    property = models.OneToOneField(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_registry",
    )
    facility_code = models.CharField(max_length=50)
    facility_classification = models.CharField(
        max_length=20,
        choices=FacilityClassification.choices,
        default=FacilityClassification.RESIDENTIAL,
    )
    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.OWNED,
    )
    lease_start_date = models.DateField(null=True, blank=True)
    lease_end_date = models.DateField(null=True, blank=True)
    lease_party_name = models.CharField(max_length=255, blank=True)
    lease_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    lease_terms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["property__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "facility_code"],
                name="fac_reg_org_code_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "facility_classification"],
                name="fac_reg_org_class_idx",
            ),
            models.Index(
                fields=["organization", "ownership_type"],
                name="fac_reg_org_owner_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility_code} — {self.property.name}"


class FacilityFloor(models.Model):
    """Floor definition within a facility."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_floors",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.CASCADE,
        related_name="floors",
    )
    name = models.CharField(max_length=150)
    floor_code = models.CharField(max_length=50, blank=True)
    floor_number = models.IntegerField()
    gross_area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_type = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility", "floor_number", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "floor_number"],
                name="fac_floor_unique_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "facility"],
                name="fac_floor_org_fac_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility.facility_code} / Floor {self.floor_number}"


class FacilityZone(models.Model):
    """Zone within a facility floor."""

    class ZoneType(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        COMMERCIAL = "commercial", "Commercial"
        INDUSTRIAL = "industrial", "Industrial"
        COMMON = "common", "Common Area"
        AMENITY = "amenity", "Amenity"
        SERVICE = "service", "Service"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_zones",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.CASCADE,
        related_name="zones",
    )
    floor = models.ForeignKey(
        "facility_management.FacilityFloor",
        on_delete=models.CASCADE,
        related_name="zones",
    )
    name = models.CharField(max_length=150)
    zone_code = models.CharField(max_length=50)
    zone_type = models.CharField(
        max_length=20,
        choices=ZoneType.choices,
        default=ZoneType.OTHER,
    )
    gross_area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility", "floor", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["floor", "zone_code"],
                name="fac_zone_floor_code_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "facility"],
                name="fac_zone_org_fac_idx",
            ),
            models.Index(
                fields=["organization", "zone_type"],
                name="fac_zone_org_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility.facility_code} / {self.zone_code}"


class FacilityUnitSpace(models.Model):
    """Mapping of units/spaces to a zone within the facility hierarchy."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_unit_spaces",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.CASCADE,
        related_name="unit_spaces",
    )
    zone = models.ForeignKey(
        "facility_management.FacilityZone",
        on_delete=models.CASCADE,
        related_name="unit_spaces",
    )
    unit = models.OneToOneField(
        "properties.Unit",
        on_delete=models.CASCADE,
        related_name="facility_space",
    )
    space_label = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility", "zone", "unit__unit_number"]
        indexes = [
            models.Index(
                fields=["organization", "facility"],
                name="fac_space_org_fac_idx",
            ),
            models.Index(
                fields=["organization", "zone"],
                name="fac_space_org_zone_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility.facility_code} / {self.unit.unit_number}"


class FacilitySpaceProfile(models.Model):
    """Occupancy and booking configuration for a mapped facility space."""

    class SpaceType(models.TextChoices):
        DESK = "desk", "Desk"
        ROOM = "room", "Room"
        MEETING_ROOM = "meeting_room", "Meeting Room"
        TENANT_SUITE = "tenant_suite", "Tenant Suite"
        HOT_DESK = "hot_desk", "Hot Desk"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MAINTENANCE = "maintenance", "Maintenance"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_space_profiles",
    )
    facility_space = models.OneToOneField(
        "facility_management.FacilityUnitSpace",
        on_delete=models.CASCADE,
        related_name="occupancy_profile",
    )
    space_type = models.CharField(
        max_length=20,
        choices=SpaceType.choices,
        default=SpaceType.ROOM,
    )
    capacity = models.PositiveIntegerField(default=1)
    is_bookable = models.BooleanField(default=False)
    booking_requires_approval = models.BooleanField(default=False)
    requires_check_in = models.BooleanField(default=False)
    default_booking_duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility_space__facility__facility_code", "facility_space__unit__unit_number"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_occ_prof_org_status_idx",
            ),
            models.Index(
                fields=["organization", "space_type"],
                name="fac_occ_prof_org_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility_space} occupancy profile"


class SpaceAllocation(models.Model):
    """Allocation of a facility space to employees, departments, or tenants."""

    class AllocationType(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        DEPARTMENT = "department", "Department"
        TENANT = "tenant", "Tenant"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        ENDING_SOON = "ending_soon", "Ending Soon"
        ENDED = "ended", "Ended"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_space_allocations",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.CASCADE,
        related_name="space_allocations",
    )
    allocation_type = models.CharField(
        max_length=20,
        choices=AllocationType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_allocations",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_allocations",
    )
    tenant_customer = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_allocations",
    )
    tenant_contact_account = models.ForeignKey(
        "crm.ContactAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_allocations",
    )
    occupant_count = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="space_allocations_created",
    )
    released_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "facility_space__unit__unit_number", "id"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_space_alloc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "facility_space"],
                name="fac_space_alloc_org_space_idx",
            ),
            models.Index(
                fields=["organization", "allocation_type"],
                name="fac_space_alloc_org_type_idx",
            ),
            models.Index(
                fields=["organization", "end_date"],
                name="fac_space_alloc_org_end_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility_space} allocation ({self.allocation_type})"


class SpaceBooking(models.Model):
    """Desk or room booking for corporate facility spaces."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_space_bookings",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.CASCADE,
        related_name="space_bookings",
    )
    title = models.CharField(max_length=255)
    purpose = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_bookings_requested",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_space_bookings_approved",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    attendee_count = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at", "facility_space__unit__unit_number", "id"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_space_book_org_status_idx",
            ),
            models.Index(
                fields=["organization", "facility_space"],
                name="fac_space_book_org_space_idx",
            ),
            models.Index(
                fields=["organization", "start_at"],
                name="fac_space_book_org_start_idx",
            ),
            models.Index(
                fields=["organization", "end_at"],
                name="fac_space_book_org_end_idx",
            ),
        ]

    def __str__(self):
        return f"{self.facility_space} booking — {self.title}"


class UtilityConsumption(models.Model):
    """Utility and energy readings used for facilities trend analysis."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_utility_readings",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        related_name="facility_utility_readings",
        null=True,
        blank=True,
    )
    reading_date = models.DateField()
    electricity_kwh = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    water_m3 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    diesel_liters = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gas_m3 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reading_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-reading_date"],
                name="fac_util_org_reading_idx",
            ),
        ]

    def __str__(self):
        property_label = self.property.name if self.property_id else "Portfolio"
        return f"{property_label} utility @ {self.reading_date}"


class UtilityMeter(models.Model):
    """Utility meter installed against a managed facility property."""

    class UtilityType(models.TextChoices):
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        GAS = "gas", "Gas"
        DIESEL = "diesel", "Diesel"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_utility_meters",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_utility_meters",
    )
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        related_name="utility_meters",
        null=True,
        blank=True,
    )
    meter_number = models.CharField(max_length=120)
    utility_type = models.CharField(
        max_length=20,
        choices=UtilityType.choices,
        default=UtilityType.ELECTRICITY,
    )
    unit_of_measure = models.CharField(max_length=30, blank=True)
    location_label = models.CharField(max_length=255, blank=True)
    provider_name = models.CharField(max_length=255, blank=True)
    installed_at = models.DateField(null=True, blank=True)
    is_smart_meter = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_reading_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["property__name", "utility_type", "meter_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "meter_number"],
                name="fac_util_meter_org_number_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "utility_type"],
                name="fac_util_meter_org_type_idx",
            ),
            models.Index(
                fields=["organization", "property"],
                name="fac_util_meter_org_prop_idx",
            ),
        ]

    def __str__(self):
        return f"{self.meter_number} ({self.get_utility_type_display()})"


class UtilityMeterReading(models.Model):
    """Reading captured from a utility meter."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_utility_meter_readings",
    )
    meter = models.ForeignKey(
        "facility_management.UtilityMeter",
        on_delete=models.CASCADE,
        related_name="readings",
    )
    reading_at = models.DateTimeField()
    reading_date = models.DateField()
    reading_value = models.DecimalField(max_digits=16, decimal_places=3)
    consumption_delta = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="facility_utility_meter_readings_entered",
        null=True,
        blank=True,
    )
    is_estimated = models.BooleanField(default=False)
    is_anomaly = models.BooleanField(default=False)
    anomaly_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reading_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "meter"],
                name="fac_util_read_org_meter_idx",
            ),
            models.Index(
                fields=["organization", "-reading_at"],
                name="fac_util_read_org_at_idx",
            ),
            models.Index(
                fields=["organization", "is_anomaly"],
                name="fac_util_read_org_anom_idx",
            ),
        ]

    def __str__(self):
        return f"{self.meter.meter_number} @ {self.reading_at:%Y-%m-%d %H:%M}"


class UtilityBill(models.Model):
    """Utility bill captured for finance sync and operating cost analytics."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        OVERDUE = "overdue", "Overdue"
        PAID = "paid", "Paid"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_utility_bills",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_utility_bills",
    )
    meter = models.ForeignKey(
        "facility_management.UtilityMeter",
        on_delete=models.SET_NULL,
        related_name="bills",
        null=True,
        blank=True,
    )
    vendor = models.ForeignKey(
        "procurement.Vendor",
        on_delete=models.SET_NULL,
        related_name="utility_bills",
        null=True,
        blank=True,
    )
    finance_bill = models.OneToOneField(
        "finance.Bill",
        on_delete=models.SET_NULL,
        related_name="utility_bill_record",
        null=True,
        blank=True,
    )
    provider_name = models.CharField(max_length=255, blank=True)
    utility_type = models.CharField(
        max_length=20,
        choices=UtilityMeter.UtilityType.choices,
        default=UtilityMeter.UtilityType.ELECTRICITY,
    )
    bill_number = models.CharField(max_length=120)
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    issue_date = models.DateField()
    due_date = models.DateField()
    usage_quantity = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    unit_rate = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-billing_period_end", "-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "bill_number"],
                name="fac_util_bill_org_number_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_util_bill_org_status_idx",
            ),
            models.Index(
                fields=["organization", "utility_type"],
                name="fac_util_bill_org_type_idx",
            ),
            models.Index(
                fields=["organization", "property"],
                name="fac_util_bill_org_prop_idx",
            ),
            models.Index(
                fields=["organization", "due_date"],
                name="fac_util_bill_org_due_idx",
            ),
        ]

    def __str__(self):
        return f"{self.bill_number} - {self.provider_name or self.get_utility_type_display()}"


class FacilityIncident(models.Model):
    """Operational safety and security incidents in managed facilities."""

    class Category(models.TextChoices):
        SAFETY = "safety", "Safety"
        SECURITY = "security", "Security"
        FIRE = "fire", "Fire"
        ENVIRONMENTAL = "environmental", "Environmental"
        HEALTH = "health", "Health"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_incidents",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        related_name="facility_incidents",
        null=True,
        blank=True,
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        related_name="incidents",
        null=True,
        blank=True,
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        related_name="incidents",
        null=True,
        blank=True,
    )
    work_order = models.ForeignKey(
        "properties.WorkOrder",
        on_delete=models.SET_NULL,
        related_name="facility_incidents",
        null=True,
        blank=True,
    )
    follow_up_inspection = models.ForeignKey(
        "properties.Inspection",
        on_delete=models.SET_NULL,
        related_name="facility_incident_follow_ups",
        null=True,
        blank=True,
    )
    incident_code = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    occurred_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    reported_by = models.CharField(max_length=255, blank=True)
    assigned_to = models.CharField(max_length=255, blank=True)
    requires_regulatory_report = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_inc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "severity"],
                name="fac_inc_org_severity_idx",
            ),
            models.Index(
                fields=["organization", "-occurred_at"],
                name="fac_inc_org_occurred_idx",
            ),
            models.Index(
                fields=["organization", "facility"],
                name="fac_inc_org_fac_idx",
            ),
            models.Index(
                fields=["organization", "incident_code"],
                name="fac_inc_org_code_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_severity_display()} incident: {self.title}"


class FacilityComplianceChecklist(models.Model):
    """Recurring or one-off compliance checklist tracked at facility level."""

    class ChecklistType(models.TextChoices):
        SAFETY = "safety", "Safety"
        FIRE_SAFETY = "fire_safety", "Fire Safety"
        ELECTRICAL = "electrical", "Electrical"
        ENVIRONMENTAL = "environmental", "Environmental"
        OCCUPATIONAL_HEALTH = "occupational_health", "Occupational Health"
        REGULATORY = "regulatory", "Regulatory"
        HOUSEKEEPING = "housekeeping", "Housekeeping"
        INCIDENT_FOLLOW_UP = "incident_follow_up", "Incident Follow-Up"

    class Frequency(models.TextChoices):
        ONE_TIME = "one_time", "One-Time"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_compliance_checklists",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_compliance_checklists",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        related_name="compliance_checklists",
        null=True,
        blank=True,
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        related_name="compliance_checklists",
        null=True,
        blank=True,
    )
    linked_incident = models.ForeignKey(
        "facility_management.FacilityIncident",
        on_delete=models.SET_NULL,
        related_name="compliance_checklists",
        null=True,
        blank=True,
    )
    linked_inspection = models.ForeignKey(
        "properties.Inspection",
        on_delete=models.SET_NULL,
        related_name="facility_compliance_checklists",
        null=True,
        blank=True,
    )
    compliance_requirement = models.ForeignKey(
        "compliance.ComplianceRequirement",
        on_delete=models.SET_NULL,
        related_name="facility_compliance_checklists",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    checklist_type = models.CharField(
        max_length=25,
        choices=ChecklistType.choices,
        default=ChecklistType.SAFETY,
    )
    frequency = models.CharField(
        max_length=15,
        choices=Frequency.choices,
        default=Frequency.ONE_TIME,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    responsible_person = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    last_completed_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    compliant_items_count = models.PositiveIntegerField(default=0)
    total_items_count = models.PositiveIntegerField(default=0)
    auto_create_violation = models.BooleanField(default=True)
    auto_create_follow_up_inspection = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "title", "id"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_chk_org_status_idx",
            ),
            models.Index(
                fields=["organization", "due_date"],
                name="fac_chk_org_due_idx",
            ),
            models.Index(
                fields=["organization", "checklist_type"],
                name="fac_chk_org_type_idx",
            ),
            models.Index(
                fields=["organization", "facility"],
                name="fac_chk_org_fac_idx",
            ),
        ]

    def __str__(self):
        return self.title


class FacilityComplianceChecklistItem(models.Model):
    """Checklist line items captured under a facility compliance checklist."""

    checklist = models.ForeignKey(
        "facility_management.FacilityComplianceChecklist",
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    is_compliant = models.BooleanField(null=True, blank=True)
    response_note = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class FacilityRegulatoryDocument(models.Model):
    """Facility-scoped regulatory document metadata layered on top of property documents."""

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        VALID = "valid", "Valid"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"
        SUPERSEDED = "superseded", "Superseded"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_regulatory_documents",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_regulatory_documents",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        related_name="regulatory_documents",
        null=True,
        blank=True,
    )
    property_document = models.OneToOneField(
        "properties.PropertyDocument",
        on_delete=models.CASCADE,
        related_name="facility_regulatory_record",
    )
    compliance_requirement = models.ForeignKey(
        "compliance.ComplianceRequirement",
        on_delete=models.SET_NULL,
        related_name="facility_regulatory_documents",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    issuing_authority = models.CharField(max_length=255, blank=True)
    reference_number = models.CharField(max_length=120, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="facility_regulatory_documents_uploaded",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fac_regdoc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "expiry_date"],
                name="fac_regdoc_org_exp_idx",
            ),
            models.Index(
                fields=["organization", "facility"],
                name="fac_regdoc_org_fac_idx",
            ),
        ]

    def __str__(self):
        return self.property_document.title


class FacilitySafetyAuditLog(models.Model):
    """Append-only audit trail for health, safety, and compliance workflows."""

    class EntityType(models.TextChoices):
        INCIDENT = "incident", "Incident"
        INSPECTION = "inspection", "Inspection"
        CHECKLIST = "checklist", "Checklist"
        DOCUMENT = "document", "Document"
        COMPLIANCE = "compliance", "Compliance"
        WORKFLOW = "workflow", "Workflow"

    class EventType(models.TextChoices):
        INCIDENT_REPORTED = "incident_reported", "Incident Reported"
        INCIDENT_RESOLVED = "incident_resolved", "Incident Resolved"
        FOLLOW_UP_INSPECTION_CREATED = "follow_up_inspection_created", "Follow-Up Inspection Created"
        CORRECTIVE_WORK_ORDER_CREATED = "corrective_work_order_created", "Corrective Work Order Created"
        INSPECTION_SCHEDULED = "inspection_scheduled", "Inspection Scheduled"
        INSPECTION_COMPLETED = "inspection_completed", "Inspection Completed"
        CHECKLIST_CREATED = "checklist_created", "Checklist Created"
        CHECKLIST_COMPLETED = "checklist_completed", "Checklist Completed"
        VIOLATION_CREATED = "violation_created", "Compliance Violation Created"
        REGULATORY_DOCUMENT_UPLOADED = "regulatory_document_uploaded", "Regulatory Document Uploaded"
        REGULATORY_DOCUMENT_FLAGGED = "regulatory_document_flagged", "Regulatory Document Flagged"
        COMPLIANCE_SYNCED = "compliance_synced", "Compliance Synced"
        WORKFLOW_SYNCED = "workflow_synced", "Workflow Synced"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_safety_audit_logs",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        related_name="facility_safety_audit_logs",
        null=True,
        blank=True,
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        related_name="safety_audit_logs",
        null=True,
        blank=True,
    )
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="facility_safety_audit_events",
        null=True,
        blank=True,
    )
    summary = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "created_at"],
                name="fac_hsc_audit_org_at_idx",
            ),
            models.Index(
                fields=["organization", "event_type"],
                name="fac_hsc_audit_org_evt_idx",
            ),
            models.Index(
                fields=["organization", "entity_type"],
                name="fac_hsc_audit_org_ent_idx",
            ),
        ]

    def __str__(self):
        return self.summary


class FacilityDocument(models.Model):
    """Central facility document register for drawings, manuals, logs, and certificates."""

    class DocumentType(models.TextChoices):
        BLUEPRINT = "blueprint", "Facility Blueprint"
        DRAWING = "drawing", "Technical Drawing"
        EQUIPMENT_MANUAL = "equipment_manual", "Equipment Manual"
        MAINTENANCE_LOG = "maintenance_log", "Maintenance Log"
        COMPLIANCE_CERTIFICATE = "compliance_certificate", "Compliance Certificate"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVIEW_DUE = "review_due", "Review Due"
        EXPIRED = "expired", "Expired"
        ARCHIVED = "archived", "Archived"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual Upload"
        GENERATED = "generated", "Generated"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="facility_documents",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="facility_documents",
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
    )
    asset_component = models.ForeignKey(
        "properties.AssetComponent",
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
    )
    linked_work_order = models.ForeignKey(
        "properties.WorkOrder",
        on_delete=models.SET_NULL,
        related_name="document_records",
        null=True,
        blank=True,
    )
    linked_inspection = models.ForeignKey(
        "properties.Inspection",
        on_delete=models.SET_NULL,
        related_name="document_records",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file = models.FileField(upload_to=facility_document_path, blank=True)
    description = models.TextField(blank=True)
    version_label = models.CharField(max_length=50, blank=True)
    reference_number = models.CharField(max_length=120, blank=True)
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    generated_summary = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="facility_documents_uploaded",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type", "title", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "document_type"],
                name="fac_doc_org_type_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="fac_doc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "facility"],
                name="fac_doc_org_fac_idx",
            ),
            models.Index(
                fields=["organization", "review_due_date"],
                name="fac_doc_org_review_idx",
            ),
            models.Index(
                fields=["organization", "expiry_date"],
                name="fac_doc_org_exp_idx",
            ),
        ]

    def __str__(self):
        return self.title
