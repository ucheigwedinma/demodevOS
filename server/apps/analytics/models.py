from django.conf import settings
from django.db import models


class PortfolioSnapshot(models.Model):
    """
    Daily pre-computed snapshot of portfolio analytics for an organization.
    One row per organization per date.
    """

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_portfolio_snapshots",
    )
    snapshot_date = models.DateField()

    # Scalar KPIs
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_acquisition = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    property_count = models.IntegerField(default=0)
    total_area_sqft = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_price_per_sqft = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unrealized_gain = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Structured data
    type_distribution = models.JSONField(default=list)
    classification_breakdown = models.JSONField(default=list)
    valuation_history = models.JSONField(default=list)
    unit_occupancy = models.JSONField(default=list)
    project_budget_summary = models.JSONField(default=list)
    top_appreciating = models.JSONField(default=list)
    top_depreciating = models.JSONField(default=list)
    encumbrance_summary = models.JSONField(default=dict)

    # Freshness
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["organization", "snapshot_date"]
        ordering = ["-snapshot_date"]
        indexes = [
            models.Index(
                fields=["organization", "-snapshot_date"],
                name="ana_port_org_date_idx",
            ),
        ]

    def __str__(self):
        return f"PortfolioSnapshot org={self.organization_id} date={self.snapshot_date}"


class BoardKpiSnapshot(models.Model):
    """
    Hourly pre-computed snapshot of board-level KPIs for an organization.
    One row per organization per hour.
    """

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_board_kpi_snapshots",
    )
    snapshot_hour = models.DateTimeField()

    # KPI fields (each stores {value, count/sample_size, unit})
    procurement_cycle_time_days = models.JSONField(default=dict)
    cost_variance_per_project_pct = models.JSONField(default=dict)
    vendor_reliability_score = models.JSONField(default=dict)
    emergency_purchases_pct = models.JSONField(default=dict)
    budget_overrun_frequency_pct = models.JSONField(default=dict)
    average_approval_time_hours = models.JSONField(default=dict)

    # Period context
    period_start = models.DateField()
    period_end = models.DateField()

    # Freshness
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["organization", "snapshot_hour"]
        ordering = ["-snapshot_hour"]
        indexes = [
            models.Index(
                fields=["organization", "-snapshot_hour"],
                name="ana_bkpi_org_hour_idx",
            ),
        ]

    def __str__(self):
        return f"BoardKpiSnapshot org={self.organization_id} hour={self.snapshot_hour}"


class CustomDashboard(models.Model):
    """
    User-defined dashboard layout.
    Stores widget selection, positions, and per-widget configuration as JSON.
    Scoped to individual users (not org-level).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_dashboards",
    )
    name = models.CharField(max_length=200)
    is_default = models.BooleanField(
        default=False,
        help_text="If True, this dashboard loads on login for this user.",
    )
    layout = models.JSONField(
        default=list,
        help_text=(
            "List of widget configs: "
            '[{"widget_type": "board_kpi_card", "kpi_key": "procurement_cycle_time_days", '
            '"position": {"x": 0, "y": 0, "w": 4, "h": 2}, "config": {}}]'
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["user", "-updated_at"],
                name="ana_cdash_user_updated_idx",
            ),
        ]

    def __str__(self):
        return f"CustomDashboard user={self.user_id} name={self.name}"


class RiskAlertAcknowledgement(models.Model):
    """
    User-facing acknowledgement state overlaid on computed risk alerts.

    Risk alerts are derived live from many source modules (projects, finance,
    procurement, etc.) and have synthetic IDs like "project-risk-123". This
    model lets users mark "I've seen this", "I'm working on it", or "this is
    handled" without mutating the underlying domain records.

    One row per (organization, alert_id). Upserted on action.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="risk_alert_acknowledgements",
    )
    alert_id = models.CharField(
        max_length=128,
        help_text="Composite alert id (e.g. 'project-risk-123', 'workflow-step-77').",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACKNOWLEDGED,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_risk_alerts",
    )
    note = models.TextField(blank=True, default="")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_alert_acks_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_alert_acks_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "alert_id")]
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="ana_riskack_org_status_idx",
            ),
            models.Index(
                fields=["organization", "-updated_at"],
                name="ana_riskack_org_updated_idx",
            ),
        ]

    def __str__(self):
        return f"RiskAlertAck org={self.organization_id} alert={self.alert_id} status={self.status}"
