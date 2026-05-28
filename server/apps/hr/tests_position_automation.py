from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.automation import check_overdue_critical_position_vacancies
from apps.hr.models import (
    Candidate,
    EmployeeRecord,
    JobListing,
    JobOffer,
    JobRequisition,
    Position,
    PositionBudget,
    Promotion,
    Vacancy,
)
from apps.notifications.models import Notification
from apps.settings.models import CostCenter, Department, Division


class PositionAutomationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Automation Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create(
            username="automation-admin",
            email="automation-admin@example.com",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={"organization": self.org},
        )
        profile.organization = self.org
        profile.role = "admin"
        profile.save(update_fields=["organization", "role"])

        self.division = Division.objects.create(
            organization=self.org,
            name="Engineering",
            code="ENG",
            head=self.admin,
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Structural Engineering",
            code="STR",
            head=self.admin,
        )
        self.cost_center = CostCenter.objects.create(
            organization=self.org,
            code="CC-STR-001",
            name="Structural Engineering Cost Center",
            department=self.department,
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

    def _create_position(self, **overrides):
        defaults = {
            "organization": self.org,
            "title": "Lead Architect",
            "code": "POS-LA-001",
            "department": self.department,
            "employment_type": Position.EmploymentType.FULL_TIME,
            "level": Position.Level.LEAD,
            "status": Position.Status.ACTIVE,
            "slot_status": Position.SlotStatus.PROPOSED,
            "criticality_score": 60,
            "headcount_budget": 1,
            "is_active": True,
        }
        defaults.update(overrides)
        return Position.objects.create(**defaults)

    def test_hire_stage_requires_budget_compliant_salary_or_cfo_override(self):
        position = self._create_position(
            code="POS-LA-002",
            slot_status=Position.SlotStatus.VACANT,
        )
        requisition = JobRequisition.objects.create(
            organization=self.org,
            title="Lead Architect Requisition",
            position=position,
            vacancy=None,
            department=self.department,
            headcount_requested=1,
            priority=JobRequisition.Priority.MEDIUM,
            salary_range_min=Decimal("3000.00"),
            salary_range_max=Decimal("5000.00"),
            status=JobRequisition.Status.APPROVED,
            requested_by=self.admin,
        )
        listing = JobListing.objects.create(
            organization=self.org,
            requisition=requisition,
            title=position.title,
            status=JobListing.Status.ACTIVE,
            salary_display=JobListing.SalaryDisplay.RANGE,
            salary_min=Decimal("3000.00"),
            salary_max=Decimal("5000.00"),
        )
        candidate = Candidate.objects.create(
            organization=self.org,
            job_listing=listing,
            job_requisition=requisition,
            first_name="Ada",
            last_name="Wong",
            email="ada@example.com",
            expected_salary=Decimal("7000.00"),
            stage=Candidate.Stage.OFFER_PENDING,
        )
        offer = JobOffer.objects.create(
            organization=self.org,
            candidate=candidate,
            requisition=requisition,
            position=position,
            offered_salary=Decimal("7000.00"),
            status=JobOffer.Status.ACCEPTED,
        )

        non_cfo_user = get_user_model().objects.create(
            username="non-cfo-user",
            email="non-cfo@example.com",
            is_active=True,
        )
        non_cfo_profile, _ = UserProfile.objects.get_or_create(
            user=non_cfo_user,
            defaults={"organization": self.org},
        )
        non_cfo_profile.organization = self.org
        non_cfo_profile.role = "member"
        non_cfo_profile.job_title = "Recruiter"
        non_cfo_profile.save(update_fields=["organization", "role", "job_title"])

        self.client.force_authenticate(non_cfo_user)
        blocked = self.client.post(
            f"/api/hr/candidates/{candidate.id}/advance_stage/",
            {"stage": Candidate.Stage.HIRED},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("requires_cfo_override", blocked.json())

        self.client.force_authenticate(self.admin)
        override = self.client.post(
            f"/api/hr/job-offers/{offer.id}/cfo-override/",
            {"reason": "Strategic hire approved."},
            format="json",
        )
        self.assertEqual(override.status_code, 200)
        self.assertTrue(override.json()["cfo_override_approved"])

        hired = self.client.post(
            f"/api/hr/candidates/{candidate.id}/advance_stage/",
            {"stage": Candidate.Stage.HIRED},
            format="json",
        )
        self.assertEqual(hired.status_code, 200)
        self.assertEqual(hired.json()["stage"], Candidate.Stage.HIRED)

    def test_vacant_position_auto_creates_recruitment_draft(self):
        position = self._create_position(code="POS-LA-003", slot_status=Position.SlotStatus.VACANT)
        position.refresh_from_db()

        self.assertIsNotNone(position.vacant_since)
        self.assertTrue(
            JobListing.objects.filter(
                organization=self.org,
                requisition__position=position,
                status=JobListing.Status.DRAFT,
            ).exists()
        )
        self.assertTrue(
            Vacancy.objects.filter(
                organization=self.org,
                position=position,
                status=Vacancy.Status.OPEN,
            ).exists()
        )

    def test_critical_vacancy_alert_sent_after_30_days(self):
        position = self._create_position(
            code="POS-LA-004",
            slot_status=Position.SlotStatus.PROPOSED,
            criticality_score=92,
        )
        Position.objects.filter(id=position.id).update(
            slot_status=Position.SlotStatus.VACANT,
            vacant_since=timezone.localdate() - timedelta(days=31),
            vacancy_alert_sent_at=None,
        )

        alerted = check_overdue_critical_position_vacancies(organization_id=self.org.id)
        self.assertGreaterEqual(alerted, 1)
        self.assertTrue(
            Notification.objects.filter(
                organization=self.org,
                recipient=self.admin,
                severity=Notification.Severity.CRITICAL,
                category=Notification.Category.HR_LIFECYCLE,
                title__icontains=position.title,
            ).exists()
        )

    def test_hiring_freeze_blocks_position_creation_when_business_unit_variance_hits_zero(self):
        PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            fiscal_period_label=f"FY {timezone.localdate().year}",
            fiscal_year=timezone.localdate().year,
            budget_source=PositionBudget.BudgetSource.CORPORATE_OVERHEAD,
            currency="NGN",
            approved_headcount=1,
            filled_headcount=1,
            budget_amount=Decimal("100.00"),
            status=PositionBudget.Status.APPROVED,
        )

        guardrail_response = self.client.get("/api/hr/positions/budget-guardrails/")
        self.assertEqual(guardrail_response.status_code, 200)
        self.assertTrue(
            any(
                row.get("division_id") == self.division.id and row.get("hiring_freeze")
                for row in guardrail_response.json().get("business_units", [])
            )
        )

        create_response = self.client.post(
            "/api/hr/positions/",
            {
                "title": "Quantity Surveyor",
                "code": "POS-QS-001",
                "department": self.department.id,
                "cost_center": self.cost_center.id,
                "employment_type": Position.EmploymentType.FULL_TIME,
                "level": Position.Level.SENIOR,
                "status": Position.Status.ACTIVE,
                "slot_status": Position.SlotStatus.PROPOSED,
                "headcount_budget": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 400)
        payload = create_response.json()
        self.assertTrue(payload.get("requires_budget_increase"))
        self.assertEqual(payload.get("business_unit"), self.division.name)

    def test_promotion_raise_over_merit_pool_requires_board_approval(self):
        employee_user = get_user_model().objects.create(
            username="promotion-employee",
            email="promotion-employee@example.com",
            first_name="Mina",
            last_name="Stone",
            is_active=True,
        )
        employee_profile, _ = UserProfile.objects.get_or_create(
            user=employee_user,
            defaults={"organization": self.org},
        )
        employee_profile.organization = self.org
        employee_profile.department = self.department
        employee_profile.role = "member"
        employee_profile.save(update_fields=["organization", "department", "role"])
        employee_record = EmployeeRecord.objects.create(
            organization=self.org,
            user=employee_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            fiscal_period_label="FY 2026",
            fiscal_year=2026,
            budget_source=PositionBudget.BudgetSource.CORPORATE_OVERHEAD,
            currency="NGN",
            approved_headcount=1,
            filled_headcount=0,
            budget_amount=Decimal("100.00"),
            status=PositionBudget.Status.APPROVED,
        )

        blocked_response = self.client.post(
            "/api/hr/promotions/",
            {
                "employee": employee_record.id,
                "to_position": "Senior Site Engineer",
                "effective_date": "2026-03-15",
                "salary_adjustment": "250.00",
                "status": Promotion.Status.PENDING,
            },
            format="json",
        )
        self.assertEqual(blocked_response.status_code, 400)
        blocked_payload = blocked_response.json()
        self.assertTrue(blocked_payload.get("requires_board_approval"))
        self.assertEqual(Decimal(str(blocked_payload.get("unallocated_budget"))), Decimal("100"))

        allowed_response = self.client.post(
            "/api/hr/promotions/",
            {
                "employee": employee_record.id,
                "to_position": "Senior Site Engineer",
                "effective_date": "2026-03-15",
                "salary_adjustment": "50.00",
                "status": Promotion.Status.PENDING,
            },
            format="json",
        )
        self.assertEqual(allowed_response.status_code, 201)
