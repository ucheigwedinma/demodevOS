import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def property_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1]
    return f"properties/{instance.property_id}/images/{uuid.uuid4().hex}.{ext}"


def property_document_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1]
    return f"properties/{instance.property_id}/documents/{uuid.uuid4().hex}.{ext}"


class Property(models.Model):
    """Land parcels, buildings, and developments."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_properties",
    )

    class PropertyType(models.TextChoices):
        LAND = "land", "Land Parcel"
        BUILDING = "building", "Building"
        MIXED = "mixed", "Mixed-Use"
        ESTATE = "estate", "Estate"
        WAREHOUSE = "warehouse", "Warehouse"
        INDUSTRIAL = "industrial", "Industrial"

    class Classification(models.TextChoices):
        OWNED = "owned", "Owned"
        LEASE = "lease", "Lease"
        CONCESSION = "concession", "Concession"
        UNDER_DEVELOPMENT = "under_development", "Under Development"

    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    classification = models.CharField(
        max_length=20, choices=Classification.choices, default=Classification.OWNED
    )
    address = models.TextField()
    description = models.TextField(blank=True)
    gps_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Latitude in decimal degrees (-90 to 90)",
    )
    gps_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Longitude in decimal degrees (-180 to 180)",
    )
    plot_number = models.CharField(max_length=100, blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="prop_prop_org_created_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def facility(self):
        return getattr(self, "facility_registry", None)


class PropertyOwnership(models.Model):
    """Ownership records for a property. Supports multiple owners (e.g. 60/40 JV)."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_ownerships",
    )

    class OwnershipStructure(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        CORPORATE = "corporate", "Corporate"
        TRUST = "trust", "Trust"
        JOINT_VENTURE = "joint_venture", "Joint Venture"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="ownerships"
    )
    legal_owner_name = models.CharField(max_length=255)
    ownership_structure = models.CharField(
        max_length=20,
        choices=OwnershipStructure.choices,
        default=OwnershipStructure.INDIVIDUAL,
    )
    ownership_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Percentage of ownership (0.00 - 100.00)",
    )
    title_deed_number = models.CharField(max_length=100)
    registration_authority = models.CharField(max_length=255)
    date_of_registration = models.DateField()
    deed_expiry = models.DateField(
        null=True, blank=True, help_text="Applicable for leasehold properties"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ownership_percentage"]
        verbose_name_plural = "property ownerships"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="prop_own_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.legal_owner_name} ({self.ownership_percentage}%)"


class PropertyEncumbrance(models.Model):
    """Encumbrances (mortgages, liens, disputes) attached to a property."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_encumbrances",
    )

    class EncumbranceType(models.TextChoices):
        MORTGAGE = "mortgage", "Mortgage"
        LIEN = "lien", "Lien"
        LEGAL_DISPUTE = "legal_dispute", "Legal Dispute"
        COURT_CASE = "court_case", "Court Case"
        TAX_ARREARS = "tax_arrears", "Tax Arrears"

    class EncumbranceStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"
        PENDING = "pending", "Pending"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="encumbrances"
    )
    encumbrance_type = models.CharField(
        max_length=20, choices=EncumbranceType.choices
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=EncumbranceStatus.choices,
        default=EncumbranceStatus.ACTIVE,
    )
    date_filed = models.DateField()
    date_resolved = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_filed"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="prop_enc_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-created_at"],
                name="prop_enc_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.title} ({self.get_status_display()})"


class Unit(models.Model):
    """Individual sellable/leasable units within a property."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_units",
    )

    class UnitStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        LEASED = "leased", "Leased"

    class UnitCategory(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        VILLA = "villa", "Villa"
        TOWNHOUSE = "townhouse", "Townhouse"
        PENTHOUSE = "penthouse", "Penthouse"
        STUDIO = "studio", "Studio"
        DUPLEX = "duplex", "Duplex"
        OFFICE = "office", "Office"
        RETAIL = "retail", "Retail"
        WAREHOUSE = "warehouse", "Warehouse"
        LAND = "land", "Land"
        OTHER = "other", "Other"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_number = models.CharField(max_length=50)
    floor = models.IntegerField(null=True, blank=True)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    unit_category = models.CharField(
        max_length=20,
        choices=UnitCategory.choices,
        default=UnitCategory.APARTMENT,
    )
    asking_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gps_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Latitude in decimal degrees (-90 to 90)",
    )
    gps_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Longitude in decimal degrees (-180 to 180)",
    )
    location_description = models.CharField(
        max_length=255, blank=True,
        help_text="Textual location within the property (e.g., Block A, Level 3, East Wing)",
    )
    status = models.CharField(max_length=20, choices=UnitStatus.choices, default=UnitStatus.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["property", "unit_number"]
        ordering = ["property", "unit_number"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prop_unit_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="prop_unit_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.unit_number}"


class PropertyImage(models.Model):
    """Photo gallery image for a property."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_images",
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=property_image_path)
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-uploaded_at"]
        indexes = [
            models.Index(
                fields=["organization", "-uploaded_at"],
                name="prop_img_org_uploaded_idx",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - Image {self.pk}"


class PropertyDocument(models.Model):
    """Attached document for a property (deeds, contracts, surveys, etc.)."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_documents",
    )

    class DocumentType(models.TextChoices):
        DEED = "deed", "Deed"
        CONTRACT = "contract", "Contract"
        SURVEY = "survey", "Survey"
        PERMIT = "permit", "Permit"
        INSPECTION = "inspection", "Inspection Report"
        APPRAISAL = "appraisal", "Appraisal"
        INSURANCE = "insurance", "Insurance"
        TAX = "tax", "Tax Document"
        CERTIFICATE_OF_OCCUPANCY = "certificate_of_occupancy", "Certificate of Occupancy"
        LEASE_AGREEMENT = "lease_agreement", "Lease Agreement"
        EASEMENT = "easement", "Easement"
        MORTGAGE = "mortgage", "Mortgage"
        GOVERNMENT_APPROVAL = "government_approval", "Government Approval"
        OTHER = "other", "Other"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=property_document_path)
    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(
                fields=["organization", "-uploaded_at"],
                name="prop_doc_org_uploaded_idx",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.title}"


class MaintenanceVendor(models.Model):
    """Vendor / contractor for maintenance and facilities work."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_maintenance_vendors",
    )

    class Specialization(models.TextChoices):
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        HVAC = "hvac", "HVAC"
        STRUCTURAL = "structural", "Structural"
        MECHANICAL = "mechanical", "Mechanical"
        FIRE_SAFETY = "fire_safety", "Fire & Safety"
        ELEVATOR = "elevator", "Elevators"
        GENERATOR = "generator", "Generators"
        WATER_SYSTEMS = "water_systems", "Water Systems"
        SECURITY = "security", "Security Systems"
        CLEANING = "cleaning", "Cleaning"
        LANDSCAPING = "landscaping", "Landscaping"
        PAINTING = "painting", "Painting"
        GENERAL = "general", "General"

    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    specialization = models.CharField(
        max_length=20, choices=Specialization.choices, default=Specialization.GENERAL
    )
    license_number = models.CharField(max_length=100, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True,
        help_text="Vendor rating (0.0 - 5.0)",
    )
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="prop_mven_org_created_idx"),
        ]

    def __str__(self):
        return self.name


class AssetComponent(models.Model):
    """Physical asset / equipment tracked in the asset component register."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_asset_components",
    )

    class Category(models.TextChoices):
        STRUCTURAL = "structural", "Structural"
        ELECTRICAL = "electrical", "Electrical"
        MECHANICAL = "mechanical", "Mechanical"
        PLUMBING = "plumbing", "Plumbing"
        HVAC = "hvac", "HVAC"
        FIRE_SAFETY = "fire_safety", "Fire & Safety"
        ELEVATOR = "elevator", "Elevators"
        GENERATOR = "generator", "Generators"
        WATER_SYSTEMS = "water_systems", "Water Systems"
        SECURITY = "security", "Security Systems"

    class ConditionRating(models.TextChoices):
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        CRITICAL = "critical", "Critical"

    class LifecycleStage(models.TextChoices):
        INSTALL = "install", "Install"
        OPERATE = "operate", "Operate"
        MAINTAIN = "maintain", "Maintain"
        RETIRE = "retire", "Retire"

    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = "straight_line", "Straight Line"

    class IoTStatus(models.TextChoices):
        NOT_CONNECTED = "not_connected", "Not Connected"
        CONNECTED = "connected", "Connected"
        OFFLINE = "offline", "Offline"
        FAULT = "fault", "Fault"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="asset_components"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    unit = models.ForeignKey(
        "Unit", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="asset_components",
    )
    vendor = models.ForeignKey(
        MaintenanceVendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_components",
    )
    component_id = models.CharField(
        max_length=50, unique=True,
        help_text="Unique asset identifier (e.g. AST-0001)",
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)
    location_description = models.CharField(
        max_length=255, blank=True,
        help_text="Physical location within the property",
    )
    manufacturer = models.CharField(max_length=255, blank=True)
    model_number = models.CharField(max_length=255, blank=True)
    serial_number = models.CharField(max_length=255, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    commissioned_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    expected_useful_life_years = models.PositiveIntegerField(null=True, blank=True)
    maintenance_frequency = models.CharField(
        max_length=15,
        choices=(
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("biweekly", "Bi-Weekly"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi_annual", "Semi-Annual"),
            ("annual", "Annual"),
        ),
        blank=True,
    )
    maintenance_next_due_date = models.DateField(null=True, blank=True)
    auto_schedule_maintenance = models.BooleanField(default=True)
    lifecycle_stage = models.CharField(
        max_length=10,
        choices=LifecycleStage.choices,
        default=LifecycleStage.OPERATE,
    )
    retired_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    salvage_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    depreciation_enabled = models.BooleanField(default=False)
    depreciation_method = models.CharField(
        max_length=20,
        choices=DepreciationMethod.choices,
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    depreciation_start_date = models.DateField(null=True, blank=True)
    last_depreciation_sync_at = models.DateTimeField(null=True, blank=True)
    amc_vendor = models.ForeignKey(
        MaintenanceVendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amc_assets",
    )
    amc_start_date = models.DateField(null=True, blank=True)
    amc_end_date = models.DateField(null=True, blank=True)
    amc_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amc_reference = models.CharField(max_length=120, blank=True)
    amc_notes = models.TextField(blank=True)
    is_iot_enabled = models.BooleanField(default=False)
    iot_device_id = models.CharField(max_length=120, blank=True)
    iot_status = models.CharField(
        max_length=20,
        choices=IoTStatus.choices,
        default=IoTStatus.NOT_CONNECTED,
    )
    iot_last_seen_at = models.DateTimeField(null=True, blank=True)
    condition_rating = models.CharField(
        max_length=10, choices=ConditionRating.choices, default=ConditionRating.GOOD
    )
    last_inspection_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["component_id"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="prop_ac_org_created_idx",
            ),
            models.Index(
                fields=["organization", "facility"],
                name="prop_ac_org_facility_idx",
            ),
            models.Index(
                fields=["organization", "lifecycle_stage"],
                name="prop_ac_org_lifecycle_idx",
            ),
            models.Index(
                fields=["organization", "maintenance_next_due_date"],
                name="prop_ac_org_maint_due_idx",
            ),
        ]

    def __str__(self):
        return f"{self.component_id} — {self.name}"


class WorkOrder(models.Model):
    """Corrective (reactive) maintenance work order."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_work_orders",
    )

    class Category(models.TextChoices):
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        HVAC = "hvac", "HVAC"
        STRUCTURAL = "structural", "Structural"
        MECHANICAL = "mechanical", "Mechanical"
        CLEANING = "cleaning", "Cleaning"
        LANDSCAPING = "landscaping", "Landscaping"
        SECURITY = "security", "Security"
        PAINTING = "painting", "Painting"
        FIRE_SAFETY = "fire_safety", "Fire Safety"
        ELEVATOR = "elevator", "Elevator"
        GENERATOR = "generator", "Generator"
        WATER_SYSTEMS = "water_systems", "Water Systems"
        GENERAL = "general", "General"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        VERIFIED = "verified", "Verified"
        CANCELLED = "cancelled", "Cancelled"

    class MaintenanceMode(models.TextChoices):
        CORRECTIVE = "corrective", "Corrective"
        PREVENTIVE = "preventive", "Preventive"
        PREDICTIVE = "predictive", "Predictive"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="work_orders"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_orders",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_orders",
    )
    unit = models.ForeignKey(
        "Unit", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="work_orders",
    )
    asset_component = models.ForeignKey(
        AssetComponent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="work_orders",
    )
    vendor = models.ForeignKey(
        MaintenanceVendor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="work_orders",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    maintenance_mode = models.CharField(
        max_length=20, choices=MaintenanceMode.choices, default=MaintenanceMode.CORRECTIVE
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.OPEN
    )
    reported_by = models.CharField(max_length=255, blank=True)
    assigned_to = models.CharField(max_length=255, blank=True)
    reported_date = models.DateField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    sla_target_hours = models.PositiveIntegerField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True)
    verification_notes = models.TextField(blank=True)
    preventive_schedule = models.ForeignKey(
        "PreventiveSchedule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_work_orders",
    )
    is_breakdown = models.BooleanField(default=False)
    root_cause = models.TextField(blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prop_wo_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="prop_wo_org_created_idx"),
            models.Index(fields=["organization", "maintenance_mode"], name="prop_wo_org_mode_idx"),
            models.Index(fields=["organization", "facility"], name="prop_wo_org_facility_idx"),
        ]

    def __str__(self):
        return f"WO-{self.pk} {self.title}"


class PreventiveSchedule(models.Model):
    """Planned / preventive maintenance schedule."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_preventive_schedules",
    )

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUAL = "annual", "Annual"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="preventive_schedules"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preventive_schedules",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preventive_schedules",
    )
    asset_component = models.ForeignKey(
        AssetComponent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="preventive_schedules",
    )
    vendor = models.ForeignKey(
        MaintenanceVendor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="preventive_schedules",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=WorkOrder.Category.choices, default=WorkOrder.Category.GENERAL
    )
    frequency = models.CharField(max_length=15, choices=Frequency.choices)
    priority = models.CharField(
        max_length=10, choices=WorkOrder.Priority.choices, default=WorkOrder.Priority.MEDIUM
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    next_due_date = models.DateField()
    last_completed_date = models.DateField(null=True, blank=True)
    sla_target_hours = models.PositiveIntegerField(null=True, blank=True)
    generate_days_before = models.PositiveIntegerField(default=0)
    auto_create_work_orders = models.BooleanField(default=True)
    last_work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_generated_date = models.DateField(null=True, blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    auto_generated = models.BooleanField(default=False)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_due_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prop_ps_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="prop_ps_org_created_idx"),
            models.Index(fields=["organization", "facility"], name="prop_ps_org_facility_idx"),
        ]

    def __str__(self):
        return f"PM — {self.title} ({self.get_frequency_display()})"


class PredictiveMaintenanceRule(models.Model):
    """Rule used to raise predictive maintenance alerts and work orders."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_predictive_maintenance_rules",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="predictive_maintenance_rules"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_rules",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_rules",
    )
    asset_component = models.ForeignKey(
        AssetComponent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_rules",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, choices=WorkOrder.Priority.choices, default=WorkOrder.Priority.HIGH
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    sla_target_hours = models.PositiveIntegerField(null=True, blank=True)
    runtime_hours_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cycle_threshold = models.PositiveIntegerField(null=True, blank=True)
    runtime_hours_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cycle_reading = models.PositiveIntegerField(null=True, blank=True)
    alert_on_offline = models.BooleanField(default=True)
    alert_on_fault = models.BooleanField(default=True)
    auto_create_work_order = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "id"]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="prop_pr_org_active_idx"),
            models.Index(fields=["organization", "facility"], name="prop_pr_org_facility_idx"),
        ]

    def __str__(self):
        return self.title


class PredictiveMaintenanceAlert(models.Model):
    """Raised predictive alert that can optionally create a work order."""

    class TriggerType(models.TextChoices):
        IOT_OFFLINE = "iot_offline", "IoT Offline"
        IOT_FAULT = "iot_fault", "IoT Fault"
        RUNTIME_HOURS = "runtime_hours", "Runtime Hours"
        CYCLE_COUNT = "cycle_count", "Cycle Count"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        WORK_ORDER_CREATED = "work_order_created", "Work Order Created"
        RESOLVED = "resolved", "Resolved"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_predictive_maintenance_alerts",
    )
    rule = models.ForeignKey(
        "PredictiveMaintenanceRule",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="predictive_maintenance_alerts"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_alerts",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_alerts",
    )
    asset_component = models.ForeignKey(
        AssetComponent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_alerts",
    )
    work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictive_alerts",
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, choices=WorkOrder.Priority.choices, default=WorkOrder.Priority.HIGH
    )
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPEN)
    runtime_hours_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cycle_reading = models.PositiveIntegerField(null=True, blank=True)
    iot_status = models.CharField(max_length=20, blank=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-triggered_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prop_pa_org_status_idx"),
            models.Index(fields=["organization", "rule"], name="prop_pa_org_rule_idx"),
        ]

    def __str__(self):
        return self.title


class Inspection(models.Model):
    """Property / asset inspection record."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_inspections",
    )

    class InspectionType(models.TextChoices):
        ROUTINE = "routine", "Routine"
        SAFETY = "safety", "Safety"
        COMPLIANCE = "compliance", "Compliance"
        PRE_HANDOVER = "pre_handover", "Pre-Handover"
        POST_INCIDENT = "post_incident", "Post-Incident"
        CONDITION_SURVEY = "condition_survey", "Condition Survey"
        FIRE_SAFETY = "fire_safety", "Fire Safety"
        ELECTRICAL = "electrical", "Electrical Inspection"
        STRUCTURAL_INTEGRITY = "structural_integrity", "Structural Integrity"
        ELEVATOR_CERTIFICATION = "elevator_certification", "Elevator Certification"
        ENVIRONMENTAL_AUDIT = "environmental_audit", "Environmental Audit"
        HEALTH_SAFETY = "health_safety", "Health & Safety"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Rating(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        CONDITIONAL = "conditional", "Conditional Pass"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"
        PARTIALLY_COMPLIANT = "partially_compliant", "Partially Compliant"
        PENDING_REVIEW = "pending_review", "Pending Review"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="inspections"
    )
    unit = models.ForeignKey(
        "Unit", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inspections",
    )
    asset_component = models.ForeignKey(
        AssetComponent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inspections",
    )
    title = models.CharField(max_length=255)
    inspection_type = models.CharField(
        max_length=25, choices=InspectionType.choices, default=InspectionType.ROUTINE
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.SCHEDULED
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    inspector = models.CharField(max_length=255, blank=True)
    findings = models.TextField(blank=True)
    rating = models.CharField(
        max_length=15, choices=Rating.choices, blank=True
    )
    risk_level = models.CharField(
        max_length=10, choices=RiskLevel.choices, blank=True
    )
    corrective_action_required = models.BooleanField(default=False)
    compliance_status = models.CharField(
        max_length=20, choices=ComplianceStatus.choices, blank=True
    )
    expiry_date = models.DateField(null=True, blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="prop_insp_org_created_idx"),
        ]

    def __str__(self):
        return f"INSP — {self.title}"


class ServiceRequest(models.Model):
    """Internal facility service request logged by employees or app users."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_service_requests",
    )

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        IN_PROGRESS = "in_progress", "In Progress"
        ESCALATED = "escalated", "Escalated"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="service_requests"
    )
    facility = models.ForeignKey(
        "facility_management.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    facility_space = models.ForeignKey(
        "facility_management.FacilityUnitSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    unit = models.ForeignKey(
        "Unit", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="service_requests",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=WorkOrder.Category.choices, default=WorkOrder.Category.GENERAL
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.OPEN
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests_submitted",
    )
    tenant_profile = models.ForeignKey(
        "tenants.TenantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    requested_by = models.CharField(max_length=255)
    class SourceChannel(models.TextChoices):
        WEB = "web", "Web"
        MOBILE = "mobile", "Mobile"

    source_channel = models.CharField(
        max_length=10,
        choices=SourceChannel.choices,
        default=SourceChannel.WEB,
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests_assigned",
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    requested_date = models.DateField(auto_now_add=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    sla_target_hours = models.PositiveIntegerField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    resolved_date = models.DateField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="service_requests",
        help_text="Work order created from this service request",
    )
    feedback_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    feedback_comment = models.TextField(blank=True)
    feedback_submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="prop_sr_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="prop_sr_org_created_idx"),
            models.Index(fields=["organization", "facility"], name="prop_sr_org_facility_idx"),
            models.Index(fields=["organization", "sla_due_at"], name="prop_sr_org_sla_idx"),
        ]

    def __str__(self):
        return f"SR-{self.pk} {self.title}"


class PropertyValuation(models.Model):
    """Historical valuation / appraisal record for a property."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_valuations",
    )

    class ValuationType(models.TextChoices):
        APPRAISAL = "appraisal", "Professional Appraisal"
        INTERNAL = "internal", "Internal Estimate"
        MARKET = "market", "Market Comparable"
        TAX = "tax", "Tax Assessment"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="valuations")
    valuation_date = models.DateField()
    value = models.DecimalField(max_digits=15, decimal_places=2)
    valuation_type = models.CharField(
        max_length=20, choices=ValuationType.choices, default=ValuationType.INTERNAL
    )
    appraiser = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valuation_date"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="prop_val_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.valuation_date} - {self.value}"


class PropertyInventory(models.Model):
    """
    Authoritative inventory status record for a unit. One-to-one with Unit.
    Unit.status is a denormalized mirror kept in sync via signals.
    """

    class InventoryStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        HELD = "held", "Held"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        LEASED = "leased", "Leased"
        UNAVAILABLE = "unavailable", "Unavailable"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_inventories",
    )
    unit = models.OneToOneField(
        Unit, on_delete=models.CASCADE, related_name="inventory",
    )
    status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.AVAILABLE,
    )
    held_by = models.CharField(
        max_length=255, blank=True,
        help_text="Name or identifier of who placed the hold",
    )
    held_until = models.DateTimeField(
        null=True, blank=True,
        help_text="When the hold automatically expires",
    )
    reservation = models.ForeignKey(
        "crm.UnitReservation",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="inventory_records",
    )
    allocated_to = models.CharField(
        max_length=255, blank=True,
        help_text="Buyer or tenant name",
    )
    allocated_on = models.DateField(null=True, blank=True)
    list_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Current listing price (may differ from Unit.asking_price catalog price)",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Property Inventory"
        verbose_name_plural = "Property Inventories"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="prop_inv_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-updated_at"],
                name="prop_inv_org_updated_idx",
            ),
        ]

    def __str__(self):
        return f"{self.unit} — {self.get_status_display()}"


class PropertyInventoryEvent(models.Model):
    """Append-only audit trail for property inventory status changes."""

    class EventType(models.TextChoices):
        LISTED = "listed", "Listed"
        HELD = "held", "Held"
        HOLD_RELEASED = "hold_released", "Hold Released"
        HOLD_EXPIRED = "hold_expired", "Hold Expired"
        RESERVED = "reserved", "Reserved"
        RESERVATION_CANCELLED = "reservation_cancelled", "Reservation Cancelled"
        SOLD = "sold", "Sold"
        LEASED = "leased", "Leased"
        MADE_UNAVAILABLE = "made_unavailable", "Made Unavailable"
        MADE_AVAILABLE = "made_available", "Made Available"
        PRICE_CHANGED = "price_changed", "Price Changed"
        NOTE_ADDED = "note_added", "Note Added"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_inventory_events",
    )
    inventory = models.ForeignKey(
        PropertyInventory,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    actor_name = models.CharField(max_length=255, blank=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="property_inventory_events",
    )
    reservation = models.ForeignKey(
        "crm.UnitReservation",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="inventory_events",
    )
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Flexible data (e.g., price change details, hold duration)",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Inventory Event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="prop_inv_evt_org_created_idx",
            ),
            models.Index(
                fields=["inventory", "-created_at"],
                name="prop_inv_evt_inv_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.inventory.unit} — {self.get_event_type_display()}"
