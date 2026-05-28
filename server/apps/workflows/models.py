from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

# ---------------------------------------------------------------------------
# 1. WorkflowTemplate — reusable blueprint for an approval chain
# ---------------------------------------------------------------------------

class WorkflowTemplate(models.Model):
    """Reusable workflow blueprint applicable to any content type."""

    class StepMode(models.TextChoices):
        SEQUENTIAL = "sequential", "Sequential"
        PARALLEL = "parallel", "Parallel"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="workflow_templates",
    )
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    applicable_content_types = models.ManyToManyField(
        ContentType,
        blank=True,
        related_name="workflow_templates",
        help_text="Content types this template can be attached to.",
    )
    default_step_mode = models.CharField(
        max_length=20,
        choices=StepMode.choices,
        default=StepMode.SEQUENTIAL,
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="wf_tmpl_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 2. WorkflowTemplateStep — individual approval stage in a template
# ---------------------------------------------------------------------------

class WorkflowTemplateStep(models.Model):
    """Ordered approval stage within a workflow template."""

    class StepType(models.TextChoices):
        APPROVAL = "approval", "Approval"
        NOTIFICATION = "notification", "Notification Only"
        CONDITION = "condition", "Conditional Branch"

    class ExecutionMode(models.TextChoices):
        SEQUENTIAL = "sequential", "Sequential"
        PARALLEL = "parallel", "Parallel"

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=160)
    step_type = models.CharField(
        max_length=20,
        choices=StepType.choices,
        default=StepType.APPROVAL,
    )
    execution_mode = models.CharField(
        max_length=20,
        choices=ExecutionMode.choices,
        default=ExecutionMode.SEQUENTIAL,
    )
    approver_role_slug = models.SlugField(
        max_length=120,
        blank=True,
        help_text="settings.Role slug for the approver.",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_template_steps",
        help_text="Specific user override (takes precedence over role).",
    )
    # SLA
    sla_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Hours to complete this step before escalation.",
    )
    escalation_role_slug = models.SlugField(
        max_length=120,
        blank=True,
        help_text="Role to escalate to when SLA breaches.",
    )
    # Conditional logic (for step_type=CONDITION)
    condition_field = models.CharField(
        max_length=100,
        blank=True,
        help_text="Field path on target object to evaluate.",
    )
    condition_operator = models.CharField(
        max_length=20,
        blank=True,
        help_text="Operator: gt, gte, lt, lte, eq, in.",
    )
    condition_value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Value to compare against (JSON-encoded for 'in').",
    )
    condition_true_step = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Sequence to jump to if condition is true.",
    )
    condition_false_step = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Sequence to jump to if condition is false.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["template", "sequence"]
        unique_together = [("template", "sequence")]

    def __str__(self):
        return f"{self.template.name} → Step {self.sequence}: {self.name}"


# ---------------------------------------------------------------------------
# 3. ApprovalPolicy — threshold-based routing rules
# ---------------------------------------------------------------------------

class ApprovalPolicy(models.Model):
    """Configurable threshold-based approval routing policy."""

    class PolicyType(models.TextChoices):
        FINANCIAL_THRESHOLD = "financial_threshold", "Financial Threshold"
        PROCUREMENT_THRESHOLD = "procurement_threshold", "Procurement Threshold"
        CONTRACT_REVIEW = "contract_review", "Contract Review Trigger"
        CHANGE_ORDER = "change_order", "Change Order Escalation"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="approval_policies",
    )
    name = models.CharField(max_length=200)
    policy_type = models.CharField(
        max_length=30,
        choices=PolicyType.choices,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Target model this policy applies to.",
    )
    amount_field = models.CharField(
        max_length=100,
        default="total_amount",
        help_text="Field path on target model for threshold evaluation.",
    )
    min_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    max_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="policies",
    )
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower number = evaluated first.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "name"]
        verbose_name_plural = "approval policies"
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="wf_apol_org_created_idx",
            ),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 4. WorkflowInstance — runtime workflow attached to any object
# ---------------------------------------------------------------------------

class WorkflowInstance(models.Model):
    """Runtime workflow attached to any model instance via GenericFK."""

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        IN_PROGRESS = "in_progress", "In Progress"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        ESCALATED = "escalated", "Escalated"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    matched_policy = models.ForeignKey(
        ApprovalPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.DRAFT,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_workflows",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["state", "created_at"]),
        ]

    def __str__(self):
        return f"Workflow #{self.pk} ({self.template.name}) — {self.state}"


# ---------------------------------------------------------------------------
# 5. WorkflowStep — runtime approval step
# ---------------------------------------------------------------------------

class WorkflowStep(models.Model):
    """Runtime approval step within a workflow instance."""

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SKIPPED = "skipped", "Skipped"
        ESCALATED = "escalated", "Escalated"

    class ExecutionMode(models.TextChoices):
        SEQUENTIAL = "sequential", "Sequential"
        PARALLEL = "parallel", "Parallel"

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=160)
    execution_mode = models.CharField(
        max_length=20,
        choices=ExecutionMode.choices,
        default=ExecutionMode.SEQUENTIAL,
    )
    approver_role_slug = models.SlugField(max_length=120, blank=True)
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_workflow_steps",
    )
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        default=Decision.PENDING,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_step_decisions",
    )
    acting_on_behalf_of = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_workflow_decisions",
        help_text="Original assignee if decision was made via delegation.",
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    # SLA tracking
    sla_deadline = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["workflow_instance", "sequence"]
        unique_together = [("workflow_instance", "sequence")]

    def __str__(self):
        return f"Step {self.sequence}: {self.name} ({self.decision})"


# ---------------------------------------------------------------------------
# 6. Process Authority Layer
# ---------------------------------------------------------------------------

class WorkflowRole(models.Model):
    """Process-specific authority role aligned to RACI governance."""

    class Responsibility(models.TextChoices):
        RESPONSIBLE = "responsible", "Responsible"
        ACCOUNTABLE = "accountable", "Accountable"
        CONSULTED = "consulted", "Consulted"
        INFORMED = "informed", "Informed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="workflow_roles",
    )
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=160)
    responsibility = models.CharField(
        max_length=20,
        choices=Responsibility.choices,
        default=Responsibility.RESPONSIBLE,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_roles"
        ordering = ["organization_id", "name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="wf_role_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_responsibility_display()})"


class ProcessWorkflowStep(models.Model):
    """
    Process-level authority step definition.
    Uses db_table='workflow_steps' for the layered-access authority model.
    """

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="process_workflow_steps",
    )
    process_key = models.SlugField(
        max_length=80,
        help_text="Business process key, e.g. procurement.",
    )
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=160)
    sequence = models.PositiveIntegerField()
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_workflow_steps",
    )
    template_step = models.ForeignKey(
        WorkflowTemplateStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_workflow_steps",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_steps"
        ordering = ["organization_id", "process_key", "sequence", "id"]
        unique_together = [
            ("organization", "process_key", "sequence"),
            ("organization", "process_key", "code"),
        ]
        indexes = [
            models.Index(fields=["organization", "process_key", "sequence"]),
            models.Index(fields=["template", "template_step"]),
        ]

    def __str__(self):
        return (
            f"{self.process_key} step {self.sequence}: {self.name}"
        )


class Approver(models.Model):
    """Authority actor resolved either by specific user or functional role."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="approvers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="process_approver_records",
    )
    role = models.ForeignKey(
        "settings.Role",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="process_approvers",
        help_text="Functional platform role used to resolve approvers.",
    )
    workflow_role = models.ForeignKey(
        WorkflowRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approvers",
    )
    title = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "approvers"
        ordering = ["organization_id", "id"]
        unique_together = [("organization", "user", "role", "workflow_role")]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="wf_appr_org_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(role__isnull=False),
                name="approvers_user_or_role_required",
            ),
        ]

    def __str__(self):
        if self.user_id:
            return f"{self.user}"
        if self.role_id:
            return self.role.name
        return f"Approver #{self.pk}"


class ProcessAuthority(models.Model):
    """Links process step + workflow role + approver (RACI authority edge)."""

    class AuthorityType(models.TextChoices):
        RESPONSIBLE = "responsible", "Responsible"
        ACCOUNTABLE = "accountable", "Accountable"
        CONSULTED = "consulted", "Consulted"
        INFORMED = "informed", "Informed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="process_authorities",
    )
    workflow_step = models.ForeignKey(
        ProcessWorkflowStep,
        on_delete=models.CASCADE,
        related_name="authorities",
    )
    workflow_role = models.ForeignKey(
        WorkflowRole,
        on_delete=models.CASCADE,
        related_name="authorities",
    )
    approver = models.ForeignKey(
        Approver,
        on_delete=models.CASCADE,
        related_name="authorities",
    )
    authority_type = models.CharField(
        max_length=20,
        choices=AuthorityType.choices,
        default=AuthorityType.RESPONSIBLE,
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "process_authority"
        ordering = ["workflow_step_id", "sort_order", "id"]
        unique_together = [
            ("workflow_step", "workflow_role", "approver", "authority_type"),
        ]
        indexes = [
            models.Index(fields=["organization", "authority_type", "is_active"]),
            models.Index(fields=["workflow_step", "is_active"]),
        ]

    def __str__(self):
        return (
            f"{self.workflow_step} -> {self.approver} "
            f"({self.get_authority_type_display()})"
        )


# ---------------------------------------------------------------------------
# 7. UserDelegation — temporary delegation of approval authority
# ---------------------------------------------------------------------------

class UserDelegation(models.Model):
    """Temporary delegation of approval authority with date range."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="delegations",
    )
    delegator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outgoing_delegations",
        help_text="User delegating their authority.",
    )
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incoming_delegations",
        help_text="User receiving delegated authority.",
    )
    role_scope = models.ForeignKey(
        "settings.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="If set, delegation only applies for this role's approvals.",
    )
    content_type_scope = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="If set, delegation only for this content type.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.TextField(blank=True, help_text="E.g. 'Out of office'.")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_delegations",
    )

    class Meta:
        ordering = ["-starts_at"]
        indexes = [
            models.Index(
                fields=["delegator", "status", "starts_at", "ends_at"],
            ),
            models.Index(
                fields=["delegate", "status", "starts_at", "ends_at"],
            ),
        ]

    def __str__(self):
        return f"{self.delegator} → {self.delegate} ({self.status})"


# ---------------------------------------------------------------------------
# 8. WorkflowAuditEvent — immutable audit trail
# ---------------------------------------------------------------------------

class WorkflowAuditEvent(models.Model):
    """Immutable audit log for workflow lifecycle events."""

    class EventType(models.TextChoices):
        WORKFLOW_CREATED = "workflow_created", "Workflow Created"
        WORKFLOW_SUBMITTED = "workflow_submitted", "Workflow Submitted"
        STEP_ASSIGNED = "step_assigned", "Step Assigned"
        STEP_DECISION = "step_decision", "Step Decision"
        STEP_ESCALATED = "step_escalated", "Step Escalated"
        STEP_DELEGATED = "step_delegated", "Step Delegated"
        WORKFLOW_APPROVED = "workflow_approved", "Workflow Approved"
        WORKFLOW_REJECTED = "workflow_rejected", "Workflow Rejected"
        WORKFLOW_CANCELLED = "workflow_cancelled", "Workflow Cancelled"
        SLA_BREACHED = "sla_breached", "SLA Breached"
        DELEGATION_CREATED = "delegation_created", "Delegation Created"
        DELEGATION_REVOKED = "delegation_revoked", "Delegation Revoked"

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow_instance", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("WorkflowAuditEvent is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("WorkflowAuditEvent is immutable.")
