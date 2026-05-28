from django.apps import AppConfig


class SettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.settings"
    verbose_name = "Settings"

    def ready(self):
        import apps.settings.signals  # noqa: F401
        self._register_auditlog()

    @staticmethod
    def _register_auditlog():
        from auditlog.registry import auditlog

        # -- Accounts --
        from apps.accounts.models import APIKey, Invitation, Organization, ServiceAccount

        # -- Compliance --
        from apps.compliance.models import (
            ComplianceAudit,
            ComplianceRequirement,
            ComplianceViolation,
            PropertyCompliance,
        )

        # -- CRM --
        from apps.crm.models import Broker, BrokerCommissionEarning, Lead, UnitReservation

        # -- Documents --
        from apps.documents.models import Document, DocumentApproval, DocumentComment, DocumentVersion

        # -- Finance --
        from apps.finance.models import (
            Account,
            Bill,
            BillPayment,
            Budget,
            Invoice,
            InvoicePayment,
            JournalEntry,
            PaymentInstallment,
            PaymentPlan,
        )

        # -- HR --
        from apps.hr.models import (
            CompensationRecord,
            DisciplinaryRecord,
            EmployeeRecord,
            ExitManagement,
            JobOffer,
            LeaveRequest,
            PayrollRun,
            Payslip,
            Promotion,
            RoleChange,
            Transfer,
        )

        # -- Procurement --
        from apps.procurement.models import (
            GoodsReceipt,
            PurchaseOrder,
            PurchaseRequisition,
            RequestForQuotation,
            Vendor,
        )

        # -- Projects --
        from apps.projects.models import Project

        # -- Properties --
        from apps.properties.models import Property, PropertyOwnership, PropertyValuation, Unit, WorkOrder

        # -- Workflows --
        from apps.workflows.models import ApprovalPolicy, WorkflowInstance, WorkflowStep

        # -- Settings (RBAC) --
        from .models import DataScope, Role, RolePermission, RoleScope, SecuritySettings, UserScopeAssignment

        for model in (
            # Accounts & access
            Organization,
            Invitation,
            APIKey,
            ServiceAccount,
            # Properties & units
            Property,
            Unit,
            PropertyOwnership,
            PropertyValuation,
            WorkOrder,
            # Projects
            Project,
            # Finance
            Bill,
            BillPayment,
            Invoice,
            InvoicePayment,
            Budget,
            Account,
            JournalEntry,
            PaymentPlan,
            PaymentInstallment,
            # Procurement
            PurchaseOrder,
            PurchaseRequisition,
            Vendor,
            GoodsReceipt,
            RequestForQuotation,
            # Documents
            Document,
            DocumentVersion,
            DocumentApproval,
            DocumentComment,
            # HR
            EmployeeRecord,
            CompensationRecord,
            LeaveRequest,
            PayrollRun,
            Payslip,
            Promotion,
            Transfer,
            RoleChange,
            DisciplinaryRecord,
            ExitManagement,
            JobOffer,
            # Compliance
            ComplianceRequirement,
            PropertyCompliance,
            ComplianceViolation,
            ComplianceAudit,
            # Workflows
            WorkflowInstance,
            WorkflowStep,
            ApprovalPolicy,
            # CRM
            Lead,
            UnitReservation,
            Broker,
            BrokerCommissionEarning,
            # Settings (RBAC)
            Role,
            RolePermission,
            DataScope,
            RoleScope,
            UserScopeAssignment,
            SecuritySettings,
        ):
            auditlog.register(model)
