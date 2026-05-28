from django.db import models

from apps.properties.models import Property, PropertyValuation


class ComparableSale(models.Model):
    """Market comparable sales used as reference data for property valuations."""

    class Source(models.TextChoices):
        MLS = "mls", "MLS Listing"
        PUBLIC_RECORDS = "public_records", "Public Records"
        BROKER = "broker", "Broker Report"
        AUCTION = "auction", "Auction"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_comparable_sales",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comparable_sales",
        help_text="Optional link to a property in the portfolio",
    )
    address = models.CharField(max_length=500)
    sale_date = models.DateField()
    sale_price = models.DecimalField(max_digits=15, decimal_places=2)
    property_type = models.CharField(
        max_length=20,
        choices=Property.PropertyType.choices,
        blank=True,
    )
    area_sqft = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_per_sqft = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    proximity_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance from reference property in km",
    )
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.PUBLIC_RECORDS
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sale_date"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="val_cs_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.address} - {self.sale_date} - {self.sale_price}"


class ValuationAppeal(models.Model):
    """Appeals or disputes on property valuations (tax assessments, insurance, etc.)."""

    class AppealType(models.TextChoices):
        TAX_ASSESSMENT = "tax_assessment", "Tax Assessment"
        INSURANCE = "insurance", "Insurance Valuation"
        DISPUTE = "dispute", "Valuation Dispute"

    class Status(models.TextChoices):
        FILED = "filed", "Filed"
        UNDER_REVIEW = "under_review", "Under Review"
        HEARING_SCHEDULED = "hearing_scheduled", "Hearing Scheduled"
        DECIDED = "decided", "Decided"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        UPHELD = "upheld", "Upheld"
        REDUCED = "reduced", "Reduced"
        INCREASED = "increased", "Increased"
        DISMISSED = "dismissed", "Dismissed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_valuation_appeals",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="valuation_appeals"
    )
    valuation = models.ForeignKey(
        PropertyValuation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appeals",
    )
    appeal_type = models.CharField(
        max_length=20, choices=AppealType.choices, default=AppealType.TAX_ASSESSMENT
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.FILED
    )
    filed_date = models.DateField()
    hearing_date = models.DateField(null=True, blank=True)
    decision_date = models.DateField(null=True, blank=True)
    assessed_value = models.DecimalField(max_digits=15, decimal_places=2)
    requested_value = models.DecimalField(max_digits=15, decimal_places=2)
    decided_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    filing_reference = models.CharField(max_length=100, blank=True)
    representative = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(
        max_length=20, choices=Outcome.choices, default=Outcome.PENDING
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-filed_date"]
        indexes = [
            models.Index(fields=["organization", "status"], name="val_app_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="val_app_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.get_appeal_type_display()} - {self.filed_date}"
