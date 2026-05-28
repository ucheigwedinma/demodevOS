from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Lead Source
# ---------------------------------------------------------------------------


class LeadSource(models.Model):
    """Configurable source channels where leads originate."""

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="lead_sources"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="crm_lsrc_org_created_idx"),
        ]
        verbose_name = "Lead Source"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------


class Broker(models.Model):
    """External sales agent or broker who refers leads."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="brokers"
    )
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Default commission percentage",
    )
    tier = models.ForeignKey(
        "crm.BrokerTier", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="brokers",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "status"], name="crm_brkr_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="crm_brkr_org_created_idx"),
        ]
        verbose_name = "Broker"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Broker Tier
# ---------------------------------------------------------------------------


class BrokerTier(models.Model):
    """Tiering system for brokers — performance-based classification."""

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="broker_tiers"
    )
    name = models.CharField(max_length=100, help_text="e.g. Platinum, Gold, Silver, Bronze")
    code = models.CharField(max_length=50, blank=True)
    min_deals = models.PositiveIntegerField(
        default=0, help_text="Minimum closed deals to qualify",
    )
    min_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Minimum revenue generated to qualify",
    )
    commission_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.00,
        help_text="Multiplier applied to base commission (e.g. 1.2 = 20% bonus)",
    )
    bonus_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Additional bonus percentage on top of commission",
    )
    evaluation_period_months = models.PositiveIntegerField(
        default=12, help_text="Rolling period in months for tier qualification",
    )
    benefits = models.TextField(blank=True, help_text="Text description of tier benefits")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color for UI badge")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="crm_btier_org_created_idx"),
        ]
        verbose_name = "Broker Tier"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------


class Lead(models.Model):
    """A prospective buyer/tenant moving through the sales pipeline."""

    class PipelineStage(models.TextChoices):
        INQUIRY = "inquiry", "Inquiry"
        QUALIFIED = "qualified", "Qualified"
        SITE_VISIT = "site_visit", "Site Visit"
        OFFER_MADE = "offer_made", "Offer Made"
        RESERVATION = "reservation", "Reservation"
        SPA_ISSUED = "spa_issued", "SPA Issued"
        CLOSED = "closed", "Closed"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        DISQUALIFIED = "disqualified", "Disqualified"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class PaymentCapability(models.TextChoices):
        CASH = "cash", "Cash Buyer"
        MORTGAGE = "mortgage", "Mortgage / Bank Finance"
        INSTALLMENT = "installment", "Installment Plan"
        MIXED = "mixed", "Mixed (Cash + Finance)"
        UNDETERMINED = "undetermined", "Undetermined"

    class LeadType(models.TextChoices):
        BUYER = "buyer", "Buyer"
        TENANT = "tenant", "Tenant"
        INVESTOR = "investor", "Investor"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="leads"
    )

    # Contact information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    secondary_phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    # Pipeline
    pipeline_stage = models.CharField(
        max_length=20, choices=PipelineStage.choices, default=PipelineStage.INQUIRY
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    lead_type = models.CharField(
        max_length=10, choices=LeadType.choices, default=LeadType.BUYER
    )

    # Source & attribution
    source = models.ForeignKey(
        LeadSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    broker = models.ForeignKey(
        Broker, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    referral_name = models.CharField(max_length=255, blank=True)

    # Budget & payment capability
    budget_min = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    budget_max = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    payment_capability = models.CharField(
        max_length=20, choices=PaymentCapability.choices, default=PaymentCapability.UNDETERMINED
    )

    # Assignment
    assigned_to = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_leads",
    )

    # Key dates
    inquiry_date = models.DateField(default=date.today)
    qualified_date = models.DateField(null=True, blank=True)
    site_visit_date = models.DateField(null=True, blank=True)
    offer_date = models.DateField(null=True, blank=True)
    reservation_date = models.DateField(null=True, blank=True)
    spa_issued_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)

    # Conversion
    converted_customer = models.ForeignKey(
        "finance.Customer", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="source_lead",
    )

    # Outcome
    lost_reason = models.TextField(blank=True)
    score = models.PositiveIntegerField(
        default=0, help_text="Lead score 0-100"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Lead labels, e.g. ["high net worth", "mortgage needed"]',
    )
    preferred_locations = models.JSONField(
        default=list,
        blank=True,
        help_text='Preferred locations for matching, e.g. ["Lekki", "Victoria Island"]',
    )

    notes = models.TextField(blank=True)

    # Archival (read-only once migrated to ERP entity)
    is_archived = models.BooleanField(default=False, help_text="Read-only once migrated to ERP entity")
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_reason = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="crm_lead_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="crm_lead_org_created_idx"),
        ]
        verbose_name = "Lead"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def days_in_pipeline(self):
        end = self.closed_date or date.today()
        return (end - self.inquiry_date).days


# ---------------------------------------------------------------------------
# Lead ↔ Project Interest (M2M with metadata)
# ---------------------------------------------------------------------------


class LeadProjectInterest(models.Model):
    """Which projects/developments a lead is interested in."""

    class InterestLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="project_interests")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="lead_interests"
    )
    interest_level = models.CharField(
        max_length=10, choices=InterestLevel.choices, default=InterestLevel.MEDIUM
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("lead", "project")]
        indexes = [
            models.Index(fields=["lead", "-created_at"], name="crm_lpi_lead_created_idx"),
        ]
        verbose_name = "Lead Project Interest"

    def __str__(self):
        return f"{self.lead} → {self.project}"


# ---------------------------------------------------------------------------
# Lead Unit Preference
# ---------------------------------------------------------------------------


class LeadUnitPreference(models.Model):
    """Preferred unit characteristics for a lead."""

    class UnitType(models.TextChoices):
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

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="unit_preferences")
    unit_type = models.CharField(
        max_length=20, choices=UnitType.choices, default=UnitType.APARTMENT
    )
    min_bedrooms = models.PositiveIntegerField(null=True, blank=True)
    max_bedrooms = models.PositiveIntegerField(null=True, blank=True)
    min_area_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_area_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    floor_preference = models.CharField(max_length=100, blank=True, help_text="e.g. High floor, Ground, 5-10")
    view_preference = models.CharField(max_length=200, blank=True, help_text="e.g. Sea view, Garden, City")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"], name="crm_lup_lead_created_idx"),
        ]
        verbose_name = "Lead Unit Preference"

    def __str__(self):
        return f"{self.lead} — {self.get_unit_type_display()}"


# ---------------------------------------------------------------------------
# Lead Property Match
# ---------------------------------------------------------------------------


class LeadPropertyMatch(models.Model):
    """Persisted recommendation generated by the property matching engine."""

    class CandidateType(models.TextChoices):
        UNIT = "unit", "Unit"
        PROJECT = "project", "Project"

    class MatchStatus(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        VIEWED = "viewed", "Viewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        DISMISSED = "dismissed", "Dismissed"
        CONVERTED = "converted", "Converted"

    class MatchSource(models.TextChoices):
        QUALIFIED_LEAD = "qualified_lead", "Qualified Lead"
        PROPERTY_LAUNCH = "property_launch", "Property Launch"
        MANUAL_REFRESH = "manual_refresh", "Manual Refresh"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="lead_property_matches",
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="property_matches",
    )
    candidate_type = models.CharField(max_length=20, choices=CandidateType.choices)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_matches",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_matches",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_matches",
    )
    match_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    score_breakdown = models.JSONField(default=dict, blank=True)
    reason_summary = models.TextField(blank=True)
    budget_fit = models.BooleanField(default=False)
    location_fit = models.BooleanField(default=False)
    unit_type_fit = models.BooleanField(default=False)
    payment_eligibility_fit = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.SUGGESTED,
    )
    source = models.CharField(
        max_length=20,
        choices=MatchSource.choices,
        default=MatchSource.MANUAL_REFRESH,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["lead", "unit"],
                condition=models.Q(candidate_type="unit") & models.Q(unit__isnull=False),
                name="crm_lpm_unique_lead_unit",
            ),
            models.UniqueConstraint(
                fields=["lead", "project"],
                condition=models.Q(candidate_type="project") & models.Q(project__isnull=False),
                name="crm_lpm_unique_lead_project",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "lead", "is_active"], name="crm_lpm_org_lead_act_idx"),
            models.Index(fields=["organization", "status", "is_active"], name="crm_lpm_org_status_idx"),
            models.Index(fields=["organization", "-match_score"], name="crm_lpm_org_score_idx"),
            models.Index(fields=["organization", "-updated_at"], name="crm_lpm_org_updated_idx"),
        ]
        verbose_name = "Lead Property Match"
        verbose_name_plural = "Lead Property Matches"

    def __str__(self):
        target = self.unit or self.project or self.property
        return f"{self.lead.full_name} -> {target} ({self.match_score})"


# ---------------------------------------------------------------------------
# Lead Activity
# ---------------------------------------------------------------------------


class LeadActivity(models.Model):
    """Interaction / activity log for a lead."""

    class ActivityType(models.TextChoices):
        CALL = "call", "Phone Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        SITE_VISIT = "site_visit", "Site Visit"
        NOTE = "note", "Note"
        FOLLOW_UP = "follow_up", "Follow-up"
        DOCUMENT = "document", "Document Sent"
        OTHER = "other", "Other"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(
        max_length=20, choices=ActivityType.choices, default=ActivityType.NOTE
    )
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    performed_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="lead_activities"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"], name="crm_lact_lead_created_idx"),
        ]
        verbose_name = "Lead Activity"
        verbose_name_plural = "Lead Activities"

    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.subject}"


# ---------------------------------------------------------------------------
# Lead Stage Transition (for sales velocity tracking)
# ---------------------------------------------------------------------------


class LeadStageTransition(models.Model):
    """Records each pipeline stage change for velocity metrics."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="stage_transitions")
    from_stage = models.CharField(max_length=20, choices=Lead.PipelineStage.choices)
    to_stage = models.CharField(max_length=20, choices=Lead.PipelineStage.choices)
    transitioned_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    transitioned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-transitioned_at"]
        indexes = [
            models.Index(fields=["lead", "-transitioned_at"], name="crm_lst_lead_trans_idx"),
        ]
        verbose_name = "Lead Stage Transition"

    def __str__(self):
        return f"{self.lead} : {self.from_stage} → {self.to_stage}"


# ---------------------------------------------------------------------------
# Financial Pre-Assessment
# ---------------------------------------------------------------------------


class LeadFinancialAssessment(models.Model):
    """
    Financial pre-assessment for a lead — affordability scoring,
    mortgage pre-qualification, risk scoring, and payment plan modeling.
    Prevents onboarding high-risk buyers blindly.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"

    class EmploymentStatus(models.TextChoices):
        EMPLOYED = "employed", "Employed"
        SELF_EMPLOYED = "self_employed", "Self-Employed"
        BUSINESS_OWNER = "business_owner", "Business Owner"
        RETIRED = "retired", "Retired"
        UNEMPLOYED = "unemployed", "Unemployed"
        OTHER = "other", "Other"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class RecommendedPlan(models.TextChoices):
        CASH = "cash", "Cash Purchase"
        MORTGAGE = "mortgage", "Mortgage / Bank Finance"
        INSTALLMENT = "installment", "Developer Installment Plan"
        MIXED = "mixed", "Mixed (Cash + Finance)"

    lead = models.OneToOneField(
        Lead, on_delete=models.CASCADE, related_name="financial_assessment"
    )

    # --- Financial Profile ---
    monthly_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    monthly_expenses = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    existing_liabilities = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Outstanding loans, debts, credit card balances",
    )
    liquid_assets = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Cash, savings, liquid investments",
    )
    net_worth = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )

    # --- Employment ---
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, blank=True,
    )
    employment_duration_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Months in current employment",
    )
    employer_name = models.CharField(max_length=255, blank=True)

    # --- Affordability ---
    affordability_score = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Affordability score 0-100 (auto-computed or manual override)",
    )
    max_affordable_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Maximum property price the lead can afford",
    )
    debt_to_income_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="DTI ratio as percentage",
    )

    # --- Mortgage Pre-Qualification ---
    mortgage_prequalified = models.BooleanField(default=False)
    mortgage_prequalification_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    mortgage_provider = models.CharField(max_length=255, blank=True)
    mortgage_tenure_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Pre-approved mortgage tenure in months",
    )
    mortgage_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Annual interest rate %",
    )
    mortgage_notes = models.TextField(blank=True)

    # --- Risk Assessment ---
    risk_score = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Risk score 0-100 (higher = riskier)",
    )
    risk_level = models.CharField(
        max_length=10, choices=RiskLevel.choices, blank=True,
    )
    risk_factors = models.JSONField(
        default=list, blank=True,
        help_text="List of identified risk factors",
    )

    # --- Payment Plan Recommendation ---
    recommended_plan = models.CharField(
        max_length=20, choices=RecommendedPlan.choices, blank=True,
    )
    recommended_down_payment_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    recommended_monthly_payment = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )

    # --- Assessment Metadata ---
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    assessment_date = models.DateField(null=True, blank=True)
    assessed_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="financial_assessments",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="crm_lfa_status_created_idx"),
        ]
        verbose_name = "Lead Financial Assessment"

    def __str__(self):
        return f"Assessment: {self.lead}"

    @property
    def disposable_income(self):
        """Monthly disposable income after expenses and liabilities."""
        if self.monthly_income is None:
            return None
        expenses = self.monthly_expenses or 0
        liabilities = self.existing_liabilities or 0
        return self.monthly_income - expenses - liabilities

    def compute_affordability(self):
        """Compute affordability score (0-100). Higher = more affordable."""
        score = 50  # baseline

        # DTI ratio impact
        if self.monthly_income and self.monthly_income > 0:
            total_obligations = (self.monthly_expenses or 0) + (self.existing_liabilities or 0)
            dti = float(total_obligations / self.monthly_income) * 100
            self.debt_to_income_ratio = round(dti, 2)
            if dti < 30:
                score += 20
            elif dti < 40:
                score += 10
            elif dti < 50:
                score += 0
            elif dti < 60:
                score -= 10
            else:
                score -= 25
        else:
            score -= 15

        # Liquid assets vs budget
        if self.liquid_assets and self.lead.budget_min:
            coverage = float(self.liquid_assets / self.lead.budget_min)
            if coverage >= 1.0:
                score += 15
            elif coverage >= 0.5:
                score += 10
            elif coverage >= 0.2:
                score += 5
            else:
                score -= 5

        # Employment stability
        if self.employment_duration_months:
            if self.employment_duration_months >= 36:
                score += 10
            elif self.employment_duration_months >= 12:
                score += 5
            else:
                score -= 5

        # Mortgage pre-qualification bonus
        if self.mortgage_prequalified:
            score += 10

        self.affordability_score = max(0, min(100, score))

        # Max affordable price (rough: 5x annual income - liabilities)
        if self.monthly_income:
            annual = float(self.monthly_income) * 12
            liabilities = float(self.existing_liabilities or 0)
            self.max_affordable_price = max(0, round(annual * 5 - liabilities, 2))

        return self.affordability_score

    def compute_risk(self):
        """Compute risk score (0-100). Higher = riskier."""
        score = 20  # baseline
        factors = []

        if self.debt_to_income_ratio and self.debt_to_income_ratio > 50:
            score += 20
            factors.append("High debt-to-income ratio (>50%)")
        elif self.debt_to_income_ratio and self.debt_to_income_ratio > 40:
            score += 10
            factors.append("Elevated debt-to-income ratio (>40%)")

        if not self.monthly_income:
            score += 15
            factors.append("No income data provided")

        if self.liquid_assets is not None and self.lead.budget_min:
            if float(self.liquid_assets) < float(self.lead.budget_min) * 0.1:
                score += 15
                factors.append("Liquid assets below 10% of budget")

        if self.employment_status == self.EmploymentStatus.UNEMPLOYED:
            score += 20
            factors.append("Currently unemployed")
        elif self.employment_duration_months and self.employment_duration_months < 6:
            score += 10
            factors.append("Employment < 6 months")

        if (self.lead.payment_capability in (
            Lead.PaymentCapability.MORTGAGE, Lead.PaymentCapability.MIXED
        ) and not self.mortgage_prequalified):
            score += 10
            factors.append("Mortgage-dependent but not pre-qualified")

        if self.max_affordable_price and self.lead.budget_min:
            if float(self.lead.budget_min) > float(self.max_affordable_price):
                score += 15
                factors.append("Target budget exceeds affordable price")

        self.risk_score = max(0, min(100, score))
        self.risk_factors = factors

        if self.risk_score >= 70:
            self.risk_level = self.RiskLevel.CRITICAL
        elif self.risk_score >= 50:
            self.risk_level = self.RiskLevel.HIGH
        elif self.risk_score >= 30:
            self.risk_level = self.RiskLevel.MEDIUM
        else:
            self.risk_level = self.RiskLevel.LOW

        return self.risk_score


class LeadPaymentScenario(models.Model):
    """Payment plan modeling — what-if scenarios for a lead's assessment."""

    class PlanType(models.TextChoices):
        CASH = "cash", "Cash Purchase"
        MORTGAGE = "mortgage", "Mortgage"
        INSTALLMENT = "installment", "Installment Plan"
        MIXED = "mixed", "Mixed"

    assessment = models.ForeignKey(
        LeadFinancialAssessment, on_delete=models.CASCADE, related_name="scenarios"
    )
    label = models.CharField(
        max_length=200,
        help_text="e.g. 'Scenario A — 20% down + mortgage'",
    )
    plan_type = models.CharField(
        max_length=20, choices=PlanType.choices, default=PlanType.MORTGAGE
    )
    property_price = models.DecimalField(max_digits=15, decimal_places=2)
    down_payment_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=20,
        help_text="Down payment percentage",
    )
    financed_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Annual interest rate %",
    )
    tenure_months = models.PositiveIntegerField(
        default=240, help_text="Repayment period in months",
    )
    monthly_payment = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    total_cost = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Total cost including interest over full tenure",
    )
    is_recommended = models.BooleanField(default=False)
    is_affordable = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["assessment", "-created_at"], name="crm_lps_assess_created_idx"),
        ]
        verbose_name = "Lead Payment Scenario"

    def __str__(self):
        return f"{self.assessment.lead} — {self.label}"

    @property
    def down_payment_amount(self):
        return round(float(self.property_price) * float(self.down_payment_pct) / 100, 2)

    def compute(self):
        """Calculate financed_amount, monthly_payment, total_cost."""
        dp = self.down_payment_amount
        self.financed_amount = round(float(self.property_price) - dp, 2)

        if self.plan_type == self.PlanType.CASH:
            self.monthly_payment = 0
            self.total_cost = float(self.property_price)
        elif self.financed_amount and self.tenure_months and self.interest_rate:
            r = float(self.interest_rate) / 100 / 12
            n = self.tenure_months
            p = float(self.financed_amount)
            if r > 0:
                self.monthly_payment = round(p * r * (1 + r) ** n / ((1 + r) ** n - 1), 2)
            else:
                self.monthly_payment = round(p / n, 2)
            self.total_cost = round(dp + float(self.monthly_payment) * n, 2)
        elif self.financed_amount and self.tenure_months:
            self.monthly_payment = round(float(self.financed_amount) / self.tenure_months, 2)
            self.total_cost = float(self.property_price)

        # Check affordability against assessment
        assessment = self.assessment
        if assessment.disposable_income is not None and self.monthly_payment:
            self.is_affordable = float(self.monthly_payment) <= float(assessment.disposable_income) * 0.4

        return self


# ---------------------------------------------------------------------------
# Broker Commission Structure
# ---------------------------------------------------------------------------


class BrokerCommissionStructure(models.Model):
    """Configurable commission rules — org-wide defaults or per-broker/project overrides."""

    class CommissionType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage of Deal Value"
        FIXED = "fixed", "Fixed Amount"
        TIERED = "tiered", "Tiered (by deal value brackets)"

    class TriggerStage(models.TextChoices):
        RESERVATION = "reservation", "On Reservation"
        SPA_ISSUED = "spa_issued", "On SPA Issuance"
        CLOSED = "closed", "On Deal Close"
        MILESTONE = "milestone", "Milestone-Based"

    class PaymentSplit(models.TextChoices):
        UPFRONT = "upfront", "100% Upfront at Trigger"
        SPLIT_50_50 = "split_50_50", "50% at Trigger / 50% on Completion"
        SPLIT_30_70 = "split_30_70", "30% at Trigger / 70% on Completion"
        MILESTONE = "milestone", "Milestone-Based Payments"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="commission_structures",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    commission_type = models.CharField(
        max_length=20, choices=CommissionType.choices, default=CommissionType.PERCENTAGE,
    )
    base_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.00,
        help_text="Base commission rate (percentage)",
    )
    fixed_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Fixed commission amount (when type = fixed)",
    )
    tiered_brackets = models.JSONField(
        default=list, blank=True,
        help_text="Brackets for tiered commissions: [{min: 0, max: 500000, rate: 3}, ...]",
    )

    trigger_stage = models.CharField(
        max_length=20, choices=TriggerStage.choices, default=TriggerStage.CLOSED,
    )
    payment_split = models.CharField(
        max_length=20, choices=PaymentSplit.choices, default=PaymentSplit.UPFRONT,
    )

    # Scope: null = org-wide default; set = override for specific broker/project
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE,
        null=True, blank=True, related_name="commission_structures",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="commission_structures",
    )

    is_default = models.BooleanField(
        default=False,
        help_text="If true, applies as org-wide default when no specific structure matches",
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="crm_bcs_org_created_idx"),
        ]
        verbose_name = "Commission Structure"

    def __str__(self):
        scope = "Default"
        if self.broker:
            scope = self.broker.name
        if self.project:
            scope += f" / {self.project.name}"
        return f"{self.name} ({scope})"

    def compute_commission(self, deal_value):
        """Compute commission amount for a given deal value."""
        if self.commission_type == self.CommissionType.FIXED:
            return float(self.fixed_amount or 0)
        elif self.commission_type == self.CommissionType.TIERED:
            for bracket in self.tiered_brackets:
                if bracket.get("min", 0) <= deal_value <= bracket.get("max", float("inf")):
                    return round(deal_value * bracket.get("rate", 0) / 100, 2)
            return round(deal_value * float(self.base_rate) / 100, 2)
        else:
            return round(deal_value * float(self.base_rate) / 100, 2)


# ---------------------------------------------------------------------------
# Broker Commission Earning
# ---------------------------------------------------------------------------


class BrokerCommissionEarning(models.Model):
    """Actual commission record when a deal progresses to a trigger stage."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        PROCESSING = "processing", "Processing Payment"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name="commission_earnings",
    )
    lead = models.ForeignKey(
        "crm.Lead", on_delete=models.CASCADE, related_name="commission_earnings",
    )
    commission_structure = models.ForeignKey(
        BrokerCommissionStructure, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="earnings",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="commission_earnings",
    )

    # Financial
    deal_value = models.DecimalField(max_digits=15, decimal_places=2)
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Actual commission rate applied",
    )
    base_commission = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Commission before tier multiplier and bonus",
    )
    tier_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.00,
    )
    bonus_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
    )
    total_commission = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Final commission = base * multiplier + bonus",
    )

    # Trigger
    trigger_stage = models.CharField(
        max_length=20, choices=BrokerCommissionStructure.TriggerStage.choices,
    )
    triggered_at = models.DateTimeField(default=timezone.now)

    # Status & payment
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_commissions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["broker", "status"], name="crm_bce_broker_status_idx"),
            models.Index(fields=["broker", "-created_at"], name="crm_bce_broker_created_idx"),
        ]
        verbose_name = "Commission Earning"

    def __str__(self):
        return f"{self.broker.name} — {self.total_commission} ({self.get_status_display()})"

    def compute(self):
        """Compute commission amounts from structure and tier."""
        if self.commission_structure:
            self.base_commission = self.commission_structure.compute_commission(
                float(self.deal_value)
            )
            self.commission_rate = self.commission_structure.base_rate
        else:
            self.base_commission = round(
                float(self.deal_value) * float(self.commission_rate) / 100, 2
            )

        # Apply tier multiplier
        self.tier_multiplier = (
            self.broker.tier.commission_multiplier
            if self.broker.tier
            else Decimal("1.00")
        )
        tier_bonus_pct = (
            self.broker.tier.bonus_pct if self.broker.tier else Decimal("0")
        )
        self.bonus_amount = round(
            float(self.base_commission) * float(tier_bonus_pct) / 100, 2
        )
        self.total_commission = round(
            float(self.base_commission) * float(self.tier_multiplier)
            + float(self.bonus_amount),
            2,
        )
        return self


# ---------------------------------------------------------------------------
# Communication Log
# ---------------------------------------------------------------------------


class CommunicationLog(models.Model):
    """
    Rich communication record — captures WhatsApp, email, call, SMS, in-app,
    and in-person interactions with leads. Extends beyond LeadActivity by storing
    channel-specific metadata (message IDs, recording URLs, read receipts).
    """

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        IN_APP = "in_app", "In-App"
        PHONE = "phone", "Phone Call"
        VIDEO_CALL = "video_call", "Video Call"
        IN_PERSON = "in_person", "In-Person"
        OTHER = "other", "Other"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"
        FAILED = "failed", "Failed"
        RECEIVED = "received", "Received"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="communication_logs",
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="communication_logs",
    )

    channel = models.CharField(max_length=20, choices=Channel.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices, default=Direction.OUTBOUND)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SENT)

    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    summary = models.TextField(blank=True, help_text="Brief summary or notes about the interaction")

    # Channel-specific metadata
    external_message_id = models.CharField(
        max_length=255, blank=True,
        help_text="External ID from WhatsApp/email/SMS provider",
    )
    from_address = models.CharField(max_length=255, blank=True, help_text="Sender email/phone")
    to_address = models.CharField(max_length=255, blank=True, help_text="Recipient email/phone")
    cc = models.TextField(blank=True, help_text="CC addresses (comma-separated)")
    attachments = models.JSONField(
        default=list, blank=True,
        help_text="List of attachment references [{name, url, size}]",
    )

    # Linked activity (optional — auto-created when logging creates a LeadActivity)
    activity = models.OneToOneField(
        LeadActivity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="communication_log",
    )

    # Campaign link (if sent as part of a campaign)
    campaign = models.ForeignKey(
        "crm.Campaign", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="communication_logs",
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="crm_communications",
    )
    communicated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-communicated_at"]
        indexes = [
            models.Index(fields=["lead", "-communicated_at"]),
            models.Index(fields=["channel", "-communicated_at"]),
        ]
        verbose_name = "Communication Log"

    def __str__(self):
        return f"{self.get_channel_display()} — {self.lead} ({self.get_direction_display()})"


# ---------------------------------------------------------------------------
# Call Recording
# ---------------------------------------------------------------------------


class CallRecording(models.Model):
    """Call recording metadata — linked to a CommunicationLog of type phone/video_call."""

    class Disposition(models.TextChoices):
        ANSWERED = "answered", "Answered"
        NO_ANSWER = "no_answer", "No Answer"
        VOICEMAIL = "voicemail", "Voicemail"
        BUSY = "busy", "Busy"
        WRONG_NUMBER = "wrong_number", "Wrong Number"
        DROPPED = "dropped", "Dropped"

    communication = models.OneToOneField(
        CommunicationLog, on_delete=models.CASCADE, related_name="call_recording",
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    recording_url = models.URLField(max_length=500, blank=True)
    recording_storage_path = models.CharField(max_length=500, blank=True)
    disposition = models.CharField(
        max_length=20, choices=Disposition.choices, default=Disposition.ANSWERED,
    )
    caller_number = models.CharField(max_length=50, blank=True)
    callee_number = models.CharField(max_length=50, blank=True)
    transcription = models.TextField(blank=True)
    call_started_at = models.DateTimeField(null=True, blank=True)
    call_ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Call Recording"

    def __str__(self):
        return f"Call ({self.get_disposition_display()}) — {self.duration_display}"

    @property
    def duration_display(self):
        mins, secs = divmod(self.duration_seconds, 60)
        return f"{mins}m {secs}s"


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class Campaign(models.Model):
    """
    Marketing / outreach campaign targeting a set of leads.
    Leverages existing NotificationTemplate from settings for content,
    and CommunicationBrandingSettings for styling.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class CampaignType(models.TextChoices):
        EMAIL_BLAST = "email_blast", "Email Blast"
        WHATSAPP_CAMPAIGN = "whatsapp_campaign", "WhatsApp Campaign"
        SMS_BLAST = "sms_blast", "SMS Blast"
        DIGITAL_ADS = "digital_ads", "Digital Ads"
        DRIP = "drip", "Drip Campaign"
        FOLLOW_UP = "follow_up", "Follow-up Sequence"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="crm_campaigns",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=25, choices=CampaignType.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)

    # Channel & content — references existing NotificationTemplate
    channel = models.CharField(max_length=20, choices=CommunicationLog.Channel.choices)
    notification_template = models.ForeignKey(
        "settings.NotificationTemplate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="crm_campaigns",
        help_text="Template from notification engine to use for campaign content",
    )
    subject = models.CharField(max_length=255, blank=True, help_text="Override template subject")
    body = models.TextField(blank=True, help_text="Override template body")

    # Targeting
    target_pipeline_stages = models.JSONField(
        default=list, blank=True,
        help_text="Pipeline stages to target, e.g. ['inquiry', 'qualified']",
    )
    target_lead_sources = models.JSONField(
        default=list, blank=True,
        help_text="Lead source IDs to target",
    )
    target_projects = models.JSONField(
        default=list, blank=True,
        help_text="Project IDs to target leads interested in",
    )
    target_lead_types = models.JSONField(
        default=list, blank=True,
        help_text="Lead types to target, e.g. ['buyer', 'investor']",
    )

    # Launch automation
    auto_create_leads_on_launch = models.BooleanField(
        default=False,
        help_text="Automatically create campaign leads when launched",
    )
    auto_create_leads_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of leads to auto-create on launch",
    )
    auto_create_lead_type = models.CharField(
        max_length=10,
        choices=Lead.LeadType.choices,
        default=Lead.LeadType.BUYER,
        help_text="Lead type assigned to auto-created campaign leads",
    )
    auto_created_leads_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized count of leads auto-created by this campaign",
    )

    # Schedule
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metrics (denormalized for dashboard)
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    spend_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total campaign spend for ROI tracking",
    )
    revenue_attributed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Attributed revenue from this campaign",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="crm_camp_org_status_idx"),
            models.Index(fields=["organization", "-created_at"], name="crm_camp_org_created_idx"),
        ]
        verbose_name = "Campaign"

    def __str__(self):
        return f"{self.name} ({self.get_campaign_type_display()})"

    @property
    def open_rate(self):
        return round(self.opened_count / self.delivered_count * 100, 1) if self.delivered_count else 0

    @property
    def click_rate(self):
        return round(self.clicked_count / self.delivered_count * 100, 1) if self.delivered_count else 0

    @property
    def delivery_rate(self):
        return round(self.delivered_count / self.sent_count * 100, 1) if self.sent_count else 0

    @property
    def roi_percent(self):
        spend = Decimal(self.spend_amount or 0)
        if spend <= 0:
            return 0.0
        revenue = Decimal(self.revenue_attributed or 0)
        return round(float((revenue - spend) / spend * 100), 1)


# ---------------------------------------------------------------------------
# Campaign Recipient
# ---------------------------------------------------------------------------


class CampaignRecipient(models.Model):
    """Tracks individual lead delivery within a campaign."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        OPENED = "opened", "Opened"
        CLICKED = "clicked", "Clicked"
        BOUNCED = "bounced", "Bounced"
        FAILED = "failed", "Failed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="recipients",
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="campaign_recipients",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.TextField(blank=True)

    # Link to the actual communication log entry
    communication_log = models.ForeignKey(
        CommunicationLog, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="campaign_recipient",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("campaign", "lead")]
        indexes = [
            models.Index(fields=["campaign", "status"], name="crm_crec_camp_status_idx"),
        ]
        verbose_name = "Campaign Recipient"

    def __str__(self):
        return f"{self.campaign.name} → {self.lead}"


# ---------------------------------------------------------------------------
# Follow-Up Rule (SLA-driven)
# ---------------------------------------------------------------------------


class FollowUpRule(models.Model):
    """
    Configurable follow-up rule tied to pipeline stages.
    References SlaSeverityTier from settings for escalation behavior.
    Generates FollowUpTask instances when leads enter the target stage.
    """

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="follow_up_rules",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Trigger
    trigger_stage = models.CharField(
        max_length=20, choices=Lead.PipelineStage.choices,
        help_text="Follow-up is required when a lead enters this stage",
    )
    follow_up_within_hours = models.PositiveIntegerField(
        default=24, help_text="SLA: follow up within this many hours",
    )

    # Escalation — references existing SlaSeverityTier
    sla_severity = models.ForeignKey(
        "settings.SlaSeverityTier", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="follow_up_rules",
        help_text="SLA severity tier for escalation behavior",
    )

    # Action
    required_activity_type = models.CharField(
        max_length=20, choices=LeadActivity.ActivityType.choices,
        default=LeadActivity.ActivityType.FOLLOW_UP,
        help_text="Activity type that satisfies this follow-up requirement",
    )
    auto_assign_to_owner = models.BooleanField(
        default=True, help_text="Auto-assign task to the lead's assigned_to user",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trigger_stage", "follow_up_within_hours"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="crm_frul_org_created_idx"),
        ]
        verbose_name = "Follow-Up Rule"

    def __str__(self):
        return f"{self.name} ({self.get_trigger_stage_display()} — {self.follow_up_within_hours}h)"


# ---------------------------------------------------------------------------
# Follow-Up Task (generated from rules, with SLA tracking)
# ---------------------------------------------------------------------------


class FollowUpTask(models.Model):
    """
    Generated follow-up task with SLA tracking.
    Linked to FollowUpRule + Lead. Tracks breach status.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        BREACHED = "breached", "SLA Breached"
        ESCALATED = "escalated", "Escalated"
        CANCELLED = "cancelled", "Cancelled"

    rule = models.ForeignKey(
        FollowUpRule, on_delete=models.CASCADE, related_name="tasks",
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="follow_up_tasks",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="follow_up_tasks",
    )

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    due_at = models.DateTimeField(help_text="SLA deadline")
    completed_at = models.DateTimeField(null=True, blank=True)
    breached_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    # Satisfying activity
    completed_activity = models.ForeignKey(
        LeadActivity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="satisfied_follow_ups",
        help_text="The activity that satisfied this follow-up requirement",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at"]
        indexes = [
            models.Index(fields=["status", "due_at"]),
            models.Index(fields=["lead", "-due_at"]),
        ]
        verbose_name = "Follow-Up Task"

    def __str__(self):
        return f"{self.rule.name} → {self.lead} (due {self.due_at})"

    @property
    def is_overdue(self):
        return self.status in (self.Status.PENDING, self.Status.IN_PROGRESS) and timezone.now() > self.due_at

    @property
    def time_remaining(self):
        if self.status in (self.Status.COMPLETED, self.Status.CANCELLED):
            return None
        delta = self.due_at - timezone.now()
        return delta if delta.total_seconds() > 0 else timedelta(0)


# ---------------------------------------------------------------------------
# Document Tracking Event (CRM layer on top of DocumentAuditEvent)
# ---------------------------------------------------------------------------


class LeadDocumentEvent(models.Model):
    """
    CRM-level document tracking — records when a lead views, downloads,
    or receives a document (proposal, SPA, brochure). References the
    existing DocumentAuditEvent for the immutable audit trail.
    """

    class EventType(models.TextChoices):
        PROPOSAL_SENT = "proposal_sent", "Proposal Sent"
        PROPOSAL_VIEWED = "proposal_viewed", "Proposal Viewed"
        SPA_SENT = "spa_sent", "SPA Sent"
        SPA_DOWNLOADED = "spa_downloaded", "SPA Downloaded"
        SPA_SIGNED = "spa_signed", "SPA Signed"
        BROCHURE_SENT = "brochure_sent", "Brochure Sent"
        BROCHURE_VIEWED = "brochure_viewed", "Brochure Viewed"
        PRICE_LIST_SENT = "price_list_sent", "Price List Sent"
        PRICE_LIST_VIEWED = "price_list_viewed", "Price List Viewed"
        FLOOR_PLAN_SENT = "floor_plan_sent", "Floor Plan Sent"
        FLOOR_PLAN_VIEWED = "floor_plan_viewed", "Floor Plan Viewed"
        CONTRACT_SENT = "contract_sent", "Contract Sent"
        CONTRACT_DOWNLOADED = "contract_downloaded", "Contract Downloaded"
        OTHER = "other", "Other"

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="document_events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    document_name = models.CharField(max_length=255)
    document = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="lead_tracking_events",
    )
    audit_event = models.ForeignKey(
        "documents.DocumentAuditEvent", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="lead_document_events",
        help_text="Reference to the immutable document audit trail",
    )

    # Delivery metadata
    delivered_via = models.CharField(
        max_length=20, choices=CommunicationLog.Channel.choices, blank=True,
    )
    delivered_to = models.CharField(max_length=255, blank=True, help_text="Email/phone the doc was sent to")
    viewed_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="lead_document_events",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]
        verbose_name = "Lead Document Event"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.document_name} ({self.lead})"


# ---------------------------------------------------------------------------
# Meeting Record (detailed meeting history)
# ---------------------------------------------------------------------------


class MeetingRecord(models.Model):
    """
    Detailed meeting history for a lead — extends the basic LeadActivity
    meeting type with structured attendees, location, outcomes, and minutes.
    """

    class MeetingType(models.TextChoices):
        IN_PERSON = "in_person", "In-Person"
        VIDEO_CALL = "video_call", "Video Call"
        PHONE_CONFERENCE = "phone_conference", "Phone Conference"
        SITE_VISIT = "site_visit", "Site Visit"

    class Outcome(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"
        FOLLOW_UP_NEEDED = "follow_up_needed", "Follow-Up Needed"
        NO_SHOW = "no_show", "No Show"

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="meeting_records",
    )
    activity = models.OneToOneField(
        LeadActivity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="meeting_record",
    )

    title = models.CharField(max_length=255)
    meeting_type = models.CharField(max_length=20, choices=MeetingType.choices)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)

    # Schedule
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    # Location
    location = models.CharField(max_length=500, blank=True)
    meeting_link = models.URLField(max_length=500, blank=True, help_text="Video call link")

    # Participants
    attendees = models.JSONField(
        default=list, blank=True,
        help_text="List of attendees [{name, email, role}]",
    )
    organized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="organized_meetings",
    )

    # Content
    agenda = models.TextField(blank=True)
    minutes = models.TextField(blank=True, help_text="Meeting minutes / notes")
    action_items = models.JSONField(
        default=list, blank=True,
        help_text="Action items from meeting [{description, assignee, due_date}]",
    )

    # Context
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="crm_meetings",
    )
    property_unit = models.ForeignKey(
        "properties.Unit", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="crm_meetings",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["lead", "-scheduled_start"], name="crm_meet_lead_sched_idx"),
        ]
        verbose_name = "Meeting Record"

    def __str__(self):
        return f"{self.title} — {self.lead} ({self.scheduled_start.date()})"

    @property
    def duration_minutes(self):
        start = self.actual_start or self.scheduled_start
        end = self.actual_end or self.scheduled_end
        if start and end:
            return int((end - start).total_seconds() / 60)
        return None


# ---------------------------------------------------------------------------
# Unit Reservation (CRM ↔ Property Inventory handshake)
# ---------------------------------------------------------------------------


class UnitReservation(models.Model):
    """
    Links a CRM Lead to a specific properties.Unit and orchestrates
    the reservation-to-conversion lifecycle. This is the critical
    handshake between CRM and property inventory.

    NOTE: This concerns *property* inventory (sellable/leasable units),
    NOT procurement inventory (materials/supplies in the inventory app).
    """

    class Status(models.TextChoices):
        HOLD = "hold", "Hold"
        RESERVED = "reserved", "Reserved"
        PAYMENT_PENDING = "payment_pending", "Payment Pending"
        PAID = "paid", "Paid"
        CONVERTING = "converting", "Converting"
        CONVERTED = "converted", "Converted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="unit_reservations",
    )
    reservation_number = models.CharField(max_length=100, unique=True, blank=True)

    # Core relationships
    lead = models.ForeignKey(
        Lead, on_delete=models.PROTECT, related_name="reservations",
    )
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.PROTECT, related_name="reservations",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservations",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.HOLD,
    )

    # Financial
    total_price = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Agreed unit price",
    )
    deposit_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Required deposit / earnest money",
    )
    reservation_fee = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Non-refundable reservation fee",
    )

    # SLA timers
    hold_expires_at = models.DateTimeField(
        help_text="When the temporary hold expires if not confirmed",
    )
    payment_deadline = models.DateTimeField(
        null=True, blank=True,
        help_text="When deposit payment must be received",
    )

    # Key dates
    reservation_date = models.DateField(null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)

    # Conversion / outcome
    converted_customer = models.ForeignKey(
        "finance.Customer", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservations",
    )
    payment_plan = models.ForeignKey(
        "finance.PaymentPlan", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservation",
    )
    reservation_agreement = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservations",
    )
    allocation_letter = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="allocation_reservations",
    )

    # Cancellation
    cancelled_reason = models.TextField(blank=True)

    # Attribution
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="performed_reservations",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["lead", "-created_at"]),
            models.Index(fields=["unit", "status"]),
            models.Index(fields=["status", "hold_expires_at"]),
        ]
        verbose_name = "Unit Reservation"

    def __str__(self):
        return f"{self.reservation_number} — {self.lead} → {self.unit}"

    def save(self, **kwargs):
        if not self.reservation_number:
            self.reservation_number = self._generate_reservation_number()
        super().save(**kwargs)

    @staticmethod
    def _generate_reservation_number():
        last = (
            UnitReservation.objects
            .filter(reservation_number__startswith="RES-")
            .order_by("-reservation_number")
            .values_list("reservation_number", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split("-", 1)[1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"RES-{seq:05d}"

    @property
    def is_terminal(self):
        return self.status in (
            self.Status.CONVERTED,
            self.Status.EXPIRED,
            self.Status.CANCELLED,
        )


# ---------------------------------------------------------------------------
# Reservation Event (audit trail)
# ---------------------------------------------------------------------------


class ReservationEvent(models.Model):
    """Append-only audit trail for reservation lifecycle events."""

    class EventType(models.TextChoices):
        HOLD_PLACED = "hold_placed", "Hold Placed"
        HOLD_EXTENDED = "hold_extended", "Hold Extended"
        RESERVATION_CONFIRMED = "reservation_confirmed", "Reservation Confirmed"
        FORM_GENERATED = "form_generated", "Reservation Form Generated"
        PAYMENT_INSTRUCTION_SENT = "payment_instruction_sent", "Payment Instruction Sent"
        DEPOSIT_RECEIVED = "deposit_received", "Deposit Received"
        FULL_PAYMENT_RECEIVED = "full_payment_received", "Full Payment Received"
        CUSTOMER_CREATED = "customer_created", "Customer Created"
        UNIT_TRANSFERRED = "unit_transferred", "Unit Transferred"
        HOLD_EXPIRED = "hold_expired", "Hold Expired"
        CANCELLED = "cancelled", "Cancelled"
        NOTE_ADDED = "note_added", "Note Added"

    reservation = models.ForeignKey(
        UnitReservation, on_delete=models.CASCADE, related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservation_events",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reservation", "-created_at"]),
        ]
        verbose_name = "Reservation Event"

    def __str__(self):
        return f"{self.reservation.reservation_number} — {self.get_event_type_display()}"


# ---------------------------------------------------------------------------
# Contact & Account Management
# ---------------------------------------------------------------------------


class ContactAccount(models.Model):
    """Structured contact profile for individuals and organizations."""

    class EntityType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        ORGANIZATION = "organization", "Organization"

    class KYCStatus(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Not Submitted"
        PENDING_REVIEW = "pending_review", "Pending Review"
        UNDER_REVIEW = "under_review", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class RiskProfile(models.TextChoices):
        UNDISCLOSED = "undisclosed", "Undisclosed"
        CONSERVATIVE = "conservative", "Conservative"
        BALANCED = "balanced", "Balanced"
        AGGRESSIVE = "aggressive", "Aggressive"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="contact_accounts",
    )
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        default=EntityType.INDIVIDUAL,
    )

    # Individual profile
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    # Organization profile
    legal_name = models.CharField(max_length=255, blank=True)
    trade_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_identification_number = models.CharField(max_length=100, blank=True)
    primary_contact_name = models.CharField(max_length=255, blank=True)

    # Contact information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    secondary_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # KYC
    kyc_status = models.CharField(
        max_length=20,
        choices=KYCStatus.choices,
        default=KYCStatus.NOT_SUBMITTED,
    )
    kyc_reference_number = models.CharField(max_length=100, blank=True)
    kyc_last_uploaded_at = models.DateTimeField(null=True, blank=True)

    # Financial capacity
    annual_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_worth = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    liquidity_estimate = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    budget_min = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    risk_profile = models.CharField(
        max_length=20,
        choices=RiskProfile.choices,
        default=RiskProfile.UNDISCLOSED,
    )

    # Preferences
    preferred_locations = models.JSONField(default=list, blank=True)
    preferred_property_types = models.JSONField(default=list, blank=True)
    preference_notes = models.TextField(blank=True)

    interaction_summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Finance sync
    finance_customer = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_contact_accounts",
    )
    finance_synced_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_contact_accounts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_contact_accounts",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "entity_type"], name="crm_cnt_org_entity_idx"),
            models.Index(fields=["organization", "kyc_status"], name="crm_cnt_org_kyc_idx"),
            models.Index(fields=["organization", "-created_at"], name="crm_cnt_org_created_idx"),
        ]
        verbose_name = "Contact Account"
        verbose_name_plural = "Contact Accounts"

    def __str__(self):
        return self.display_name

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.primary_contact_name.strip()

    @property
    def display_name(self):
        if self.entity_type == self.EntityType.ORGANIZATION:
            return self.legal_name or self.trade_name or self.primary_contact_name or "Unnamed Organization"
        return self.full_name or self.email or self.phone or "Unnamed Contact"


class ContactInteraction(models.Model):
    """Timeline of contact engagements."""

    class InteractionType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        SITE_VISIT = "site_visit", "Site Visit"
        WHATSAPP = "whatsapp", "WhatsApp"
        NOTE = "note", "Note"

    contact = models.ForeignKey(
        ContactAccount,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=InteractionType.choices,
        default=InteractionType.NOTE,
    )
    subject = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    happened_at = models.DateTimeField(default=timezone.now)
    follow_up_required = models.BooleanField(default=False)
    follow_up_due_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_interactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-happened_at", "-created_at"]
        indexes = [
            models.Index(fields=["contact", "-happened_at"], name="crm_cint_contact_time_idx"),
        ]
        verbose_name = "Contact Interaction"

    def __str__(self):
        return f"{self.contact.display_name}: {self.subject}"


class ContactDealLink(models.Model):
    """Deals linked to a contact across CRM entities."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        ON_HOLD = "on_hold", "On Hold"

    contact = models.ForeignKey(
        ContactAccount,
        on_delete=models.CASCADE,
        related_name="deal_links",
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_deal_links",
    )
    reservation = models.ForeignKey(
        UnitReservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_deal_links",
    )
    deal_name = models.CharField(max_length=255, blank=True)
    stage = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    deal_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    close_probability = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-linked_at"]
        indexes = [
            models.Index(fields=["contact", "status"], name="crm_cdl_contact_status_idx"),
        ]
        verbose_name = "Contact Deal Link"

    def __str__(self):
        return f"{self.contact.display_name} — {self.deal_name or 'Linked Deal'}"


class ContactPropertyLink(models.Model):
    """Properties/projects/units linked to a contact profile."""

    class RelationshipType(models.TextChoices):
        INTERESTED = "interested", "Interested"
        SHORTLISTED = "shortlisted", "Shortlisted"
        RESERVED = "reserved", "Reserved"
        PURCHASED = "purchased", "Purchased"
        LEASED = "leased", "Leased"
        INVESTOR_TARGET = "investor_target", "Investor Target"

    contact = models.ForeignKey(
        ContactAccount,
        on_delete=models.CASCADE,
        related_name="property_links",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_property_links",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_property_links",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_property_links",
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=RelationshipType.choices,
        default=RelationshipType.INTERESTED,
    )
    budget_estimate = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-linked_at"]
        indexes = [
            models.Index(fields=["contact", "relationship_type"], name="crm_cpl_contact_rel_idx"),
        ]
        verbose_name = "Contact Property Link"

    def __str__(self):
        return f"{self.contact.display_name} — {self.get_relationship_type_display()}"


class ContactDocument(models.Model):
    """Documents attached to a contact, including KYC artifacts."""

    class DocumentType(models.TextChoices):
        ID_CARD = "id_card", "National ID"
        PASSPORT = "passport", "Passport"
        COMPANY_REGISTRATION = "company_registration", "Company Registration"
        PROOF_OF_FUNDS = "proof_of_funds", "Proof of Funds"
        UTILITY_BILL = "utility_bill", "Utility Bill"
        OTHER = "other", "Other"

    contact = models.ForeignKey(
        ContactAccount,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    is_kyc_document = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_documents",
    )
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["contact", "is_kyc_document"], name="crm_cdoc_contact_kyc_idx"),
            models.Index(fields=["expires_at"], name="crm_cdoc_expiry_idx"),
        ]
        verbose_name = "Contact Document"

    def __str__(self):
        return f"{self.contact.display_name} — {self.file_name}"


class ContactComplianceReview(models.Model):
    """Compliance review queue generated from KYC submissions."""

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    contact = models.ForeignKey(
        ContactAccount,
        on_delete=models.CASCADE,
        related_name="compliance_reviews",
    )
    document = models.ForeignKey(
        ContactDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_reviews",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_contact_compliance_reviews",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_contact_compliance_reviews",
    )
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["contact", "status"], name="crm_ccr_contact_status_idx"),
            models.Index(fields=["status", "-requested_at"], name="crm_ccr_status_requested_idx"),
        ]
        verbose_name = "Contact Compliance Review"

    def __str__(self):
        return f"{self.contact.display_name} — {self.get_status_display()}"
