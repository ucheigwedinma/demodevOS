from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization
from apps.compliance.models import ComplianceViolation
from apps.hr.models import EmployeeRecord, PayrollRun, Payslip
from apps.inventory.models import InventoryItem, InventoryTransaction, Warehouse
from apps.procurement.models import PurchaseOrder, Vendor
from apps.projects.models import Project, ProjectCostEntry, ProjectPhase, ProjectTask
from apps.properties.models import Property


class CostTrackingHookIntegrationTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Cost Hook Org")
        self.property = Property.objects.create(
            organization=self.org,
            name="Hook Site",
            property_type=Property.PropertyType.LAND,
            address="12 Hook Avenue",
        )
        self.project = Project.objects.create(
            organization=self.org,
            property=self.property,
            name="Hook Project",
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Execution",
            sort_order=1,
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="payroll-user@example.com",
            email="payroll-user@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "member"
        profile.save(update_fields=["organization", "role"])

        self.employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=self.user,
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase,
            name="On-site supervision",
            assigned_user=self.user,
        )

    def test_procurement_purchase_order_hook_syncs_project_cost_entry(self):
        vendor = Vendor.objects.create(
            organization=self.org,
            name="BuildMax Supplies",
        )
        po = PurchaseOrder.objects.create(
            organization=self.org,
            vendor=vendor,
            project=self.project,
            issue_date=date(2026, 3, 1),
            total_amount=Decimal("125000.00"),
        )

        reference = f"HOOK:procurement_po:org:{self.org.id}:po:{po.id}"
        entry = ProjectCostEntry.objects.get(
            organization=self.org,
            reference_number=reference,
        )
        self.assertEqual(entry.phase.project_id, self.project.id)
        self.assertEqual(entry.category, ProjectCostEntry.Category.MATERIALS)
        self.assertEqual(entry.amount, Decimal("125000.00"))

        po.total_amount = Decimal("132500.00")
        po.save()
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("132500.00"))

        po.status = PurchaseOrder.Status.CANCELLED
        po.save(update_fields=["status", "updated_at"])
        self.assertFalse(
            ProjectCostEntry.objects.filter(
                organization=self.org,
                reference_number=reference,
            ).exists()
        )

    def test_hr_payroll_hook_syncs_project_staff_payroll_costs(self):
        payroll_run = PayrollRun.objects.create(
            organization=self.org,
            name="March Payroll",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            run_date=date(2026, 3, 31),
            status=PayrollRun.Status.DRAFT,
        )
        payslip = Payslip.objects.create(
            organization=self.org,
            employee=self.employee,
            payroll_run=payroll_run,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            net_salary=Decimal("5000.00"),
            gross_salary=Decimal("5000.00"),
            basic_salary=Decimal("5000.00"),
        )

        reference = (
            f"HOOK:hr_payroll_run:org:{self.org.id}:run:{payroll_run.id}:project:{self.project.id}"
        )
        self.assertFalse(
            ProjectCostEntry.objects.filter(
                organization=self.org,
                reference_number=reference,
            ).exists()
        )

        payroll_run.status = PayrollRun.Status.COMPLETED
        payroll_run.save(update_fields=["status", "updated_at"])
        entry = ProjectCostEntry.objects.get(
            organization=self.org,
            reference_number=reference,
        )
        self.assertEqual(entry.category, ProjectCostEntry.Category.LABOR)
        self.assertEqual(entry.amount, Decimal("5000.00"))

        payslip.net_salary = Decimal("7000.00")
        payslip.gross_salary = Decimal("7000.00")
        payslip.basic_salary = Decimal("7000.00")
        payslip.save(update_fields=["net_salary", "gross_salary", "basic_salary", "updated_at"])
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("7000.00"))

        payroll_run.status = PayrollRun.Status.CANCELLED
        payroll_run.save(update_fields=["status", "updated_at"])
        self.assertFalse(
            ProjectCostEntry.objects.filter(
                organization=self.org,
                reference_number=reference,
            ).exists()
        )

    def test_compliance_permit_fee_hook_syncs_project_cost_entry(self):
        violation = ComplianceViolation.objects.create(
            organization=self.org,
            property=self.property,
            title="Permit Fee Charge",
            violation_type="regulatory",
            reported_date=date(2026, 3, 2),
            fine_amount=Decimal("75000.00"),
        )

        reference = f"HOOK:compliance_violation:org:{self.org.id}:violation:{violation.id}"
        entry = ProjectCostEntry.objects.get(
            organization=self.org,
            reference_number=reference,
        )
        self.assertEqual(entry.phase.project_id, self.project.id)
        self.assertEqual(entry.category, ProjectCostEntry.Category.PERMITS)
        self.assertEqual(entry.amount, Decimal("75000.00"))

        violation.fine_amount = Decimal("88000.00")
        violation.save(update_fields=["fine_amount", "updated_at"])
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("88000.00"))

        violation.fine_amount = Decimal("0.00")
        violation.save(update_fields=["fine_amount", "updated_at"])
        self.assertFalse(
            ProjectCostEntry.objects.filter(
                organization=self.org,
                reference_number=reference,
            ).exists()
        )

    def test_inventory_material_usage_hook_syncs_project_cost_entry(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            code=f"WH-HOOK-{self.org.id}",
            name="Main Hook Warehouse",
        )
        item = InventoryItem.objects.create(
            organization=self.org,
            sku=f"HOOK-SKU-{self.org.id}",
            name="Cement Bags",
            category=InventoryItem.Category.CONSUMABLE,
        )
        txn = InventoryTransaction.objects.create(
            organization=self.org,
            warehouse=warehouse,
            item=item,
            project=self.project,
            transaction_type=InventoryTransaction.TransactionType.ISSUE,
            quantity=Decimal("10.000"),
            unit_cost=Decimal("120.00"),
            total_cost=Decimal("1200.00"),
            transaction_date=date(2026, 3, 3),
            source_module="inventory_manual",
            source_reference="ISSUE-1",
        )

        reference = f"HOOK:inventory_issue:org:{self.org.id}:txn:{txn.id}"
        entry = ProjectCostEntry.objects.get(
            organization=self.org,
            reference_number=reference,
        )
        self.assertEqual(entry.phase.project_id, self.project.id)
        self.assertEqual(entry.category, ProjectCostEntry.Category.MATERIALS)
        self.assertEqual(entry.amount, Decimal("1200.00"))

        txn.total_cost = Decimal("2000.00")
        txn.save(update_fields=["total_cost"])
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("2000.00"))

        txn.transaction_type = InventoryTransaction.TransactionType.RECEIPT
        txn.save(update_fields=["transaction_type"])
        self.assertFalse(
            ProjectCostEntry.objects.filter(
                organization=self.org,
                reference_number=reference,
            ).exists()
        )
