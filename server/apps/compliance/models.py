from django.db import models

from apps.properties.models import Property


class ComplianceRequirement(models.Model):
    """Master registry of compliance requirement types."""

    class Category(models.TextChoices):
        REGULATORY = "regulatory", "Regulatory"
        ENVIRONMENTAL = "environmental", "Environmental"
        SAFETY = "safety", "Safety"
        BUILDING_CODE = "building_code", "Building Code"
        ZONING = "zoning", "Zoning"
        ACCESSIBILITY = "accessibility", "Accessibility"
        FIRE_SAFETY = "fire_safety", "Fire Safety"
        OCCUPATIONAL_HEALTH = "occupational_health", "Occupational Health"

    class RenewalFrequency(models.TextChoices):
        ONE_TIME = "one_time", "One-Time"
        ANNUAL = "annual", "Annual"
        BIANNUAL = "biannual", "Bi-Annual"
        QUARTERLY = "quarterly", "Quarterly"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_compliance_requirements",
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=25, choices=Category.choices)
    description = models.TextField(blank=True)
    regulatory_reference = models.CharField(
        max_length=255, blank=True,
        help_text="Legal or regulatory reference code",
    )
    renewal_frequency = models.CharField(
        max_length=15, choices=RenewalFrequency.choices,
        default=RenewalFrequency.ANNUAL,
    )
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="comp_req_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class PropertyCompliance(models.Model):
    """Tracks compliance status of a property against a requirement."""

    class Status(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"
        PENDING_REVIEW = "pending_review", "Pending Review"
        EXPIRED = "expired", "Expired"
        EXEMPT = "exempt", "Exempt"
        NOT_APPLICABLE = "not_applicable", "Not Applicable"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_property_compliances",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="compliance_records"
    )
    requirement = models.ForeignKey(
        ComplianceRequirement, on_delete=models.CASCADE,
        related_name="property_records",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    certificate_number = models.CharField(max_length=100, blank=True)
    issuing_authority = models.CharField(max_length=255, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    last_reviewed_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    responsible_person = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("property", "requirement")]
        indexes = [
            models.Index(fields=["organization", "status"], name="comp_pc_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.property.name} — {self.requirement.name} ({self.get_status_display()})"


class ComplianceViolation(models.Model):
    """Non-compliance issues and corrective actions."""

    class Severity(models.TextChoices):
        MINOR = "minor", "Minor"
        MODERATE = "moderate", "Moderate"
        MAJOR = "major", "Major"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        REMEDIATION = "remediation", "Remediation"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        APPEALED = "appealed", "Appealed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_compliance_violations",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE,
        related_name="compliance_violations",
    )
    compliance_item = models.ForeignKey(
        PropertyCompliance, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="violations",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    violation_type = models.CharField(
        max_length=25, choices=ComplianceRequirement.Category.choices,
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices,
        default=Severity.MODERATE,
    )
    status = models.CharField(
        max_length=15, choices=Status.choices,
        default=Status.OPEN,
    )
    reported_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    resolved_date = models.DateField(null=True, blank=True)
    corrective_action = models.TextField(blank=True)
    fine_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="comp_viol_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="comp_viol_org_created_idx"),
        ]

    def __str__(self):
        return f"VIO-{self.pk} {self.title}"


class ComplianceAudit(models.Model):
    """Formal compliance audits / reviews."""

    class AuditType(models.TextChoices):
        INTERNAL = "internal", "Internal"
        EXTERNAL = "external", "External"
        REGULATORY = "regulatory", "Regulatory"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class OverallRating(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        PARTIALLY_COMPLIANT = "partially_compliant", "Partially Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_compliance_audits",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE,
        related_name="compliance_audits",
    )
    title = models.CharField(max_length=255)
    audit_type = models.CharField(
        max_length=15, choices=AuditType.choices,
        default=AuditType.INTERNAL,
    )
    status = models.CharField(
        max_length=15, choices=Status.choices,
        default=Status.SCHEDULED,
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    auditor = models.CharField(max_length=255, blank=True)
    scope = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    overall_rating = models.CharField(
        max_length=25, choices=OverallRating.choices, blank=True,
    )
    follow_up_required = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="comp_aud_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="comp_aud_org_created_idx"),
        ]

    def __str__(self):
        return f"AUDIT-{self.pk} {self.title}"
