from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.crm.matching import generate_matches_for_property_launch, recompute_matches_for_lead
from apps.crm.models import Lead, LeadFinancialAssessment, LeadPropertyMatch, LeadUnitPreference
from apps.finance.models import PaymentPlan
from apps.projects.models import Project
from apps.properties.models import Property, Unit

User = get_user_model()


class PropertyMatchingEngineTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name=f"CRM Match Org {uuid4().hex[:6]}")
        self.org_2 = Organization.objects.create(name=f"CRM Match Org 2 {uuid4().hex[:6]}")

        self.user = self._create_user(self.org, role="admin")
        self.owner = self._create_user(self.org, role="member")
        self.admin_peer = self._create_user(self.org, role="admin")
        self.client.force_authenticate(self.user)

    def _create_user(self, organization: Organization, *, role: str) -> User:
        token = uuid4().hex[:8]
        email = f"user-{token}@example.com"
        user = User.objects.create_user(
            username=email,
            email=email,
            password="Pass123!",
        )
        profile = user.profile
        profile.organization = organization
        profile.role = role
        profile.user_status = UserProfile.UserStatus.ACTIVE
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        return user

    def _create_property(
        self,
        organization: Organization,
        *,
        is_active: bool = True,
        property_type: str = Property.PropertyType.BUILDING,
        address: str = "Lekki, Lagos",
    ) -> Property:
        token = uuid4().hex[:6]
        return Property.objects.create(
            organization=organization,
            name=f"Property {token}",
            property_type=property_type,
            address=address,
            classification=Property.Classification.OWNED,
            is_active=is_active,
        )

    def _create_unit(
        self,
        property_obj: Property,
        *,
        status: str = Unit.UnitStatus.AVAILABLE,
        category: str = Unit.UnitCategory.APARTMENT,
        asking_price: Decimal = Decimal("120000.00"),
        location_description: str = "Lekki Phase 1",
    ) -> Unit:
        token = uuid4().hex[:6]
        return Unit.objects.create(
            organization=property_obj.organization,
            property=property_obj,
            unit_number=f"U-{token}",
            area_sqft=Decimal("1000.00"),
            bedrooms=2,
            bathrooms=2,
            unit_category=category,
            asking_price=asking_price,
            status=status,
            location_description=location_description,
        )

    def _create_project(
        self,
        organization: Organization,
        *,
        property_obj: Property | None,
        location: str = "Lekki, Lagos",
        status_value: str = Project.Status.IN_PROGRESS,
        budget: Decimal = Decimal("125000.00"),
    ) -> Project:
        token = uuid4().hex[:6]
        return Project.objects.create(
            organization=organization,
            property=property_obj,
            name=f"Project {token}",
            status=status_value,
            location=location,
            budget=budget,
        )

    def _create_lead(
        self,
        organization: Organization,
        *,
        pipeline_stage: str = Lead.PipelineStage.INQUIRY,
        assigned_to: User | None = None,
        preferred_locations: list[str] | None = None,
        payment_capability: str = Lead.PaymentCapability.MORTGAGE,
        with_assessment: bool = True,
    ) -> Lead:
        token = uuid4().hex[:6]
        lead = Lead.objects.create(
            organization=organization,
            first_name="Ada",
            last_name=f"Lead-{token}",
            email=f"lead-{token}@example.com",
            phone=f"+23480{uuid4().hex[:8]}",
            status=Lead.Status.ACTIVE,
            pipeline_stage=pipeline_stage,
            assigned_to=assigned_to,
            budget_min=Decimal("100000.00"),
            budget_max=Decimal("150000.00"),
            payment_capability=payment_capability,
            preferred_locations=preferred_locations or ["Lekki"],
        )
        LeadUnitPreference.objects.create(
            lead=lead,
            unit_type=LeadUnitPreference.UnitType.APARTMENT,
        )
        if with_assessment:
            LeadFinancialAssessment.objects.create(
                lead=lead,
                recommended_plan=LeadFinancialAssessment.RecommendedPlan.MORTGAGE,
                max_affordable_price=Decimal("150000.00"),
            )
        return lead

    def _create_payment_plan(
        self,
        organization: Organization,
        *,
        unit: Unit | None = None,
        project: Project | None = None,
    ) -> PaymentPlan:
        token = uuid4().hex[:6]
        return PaymentPlan.objects.create(
            organization=organization,
            title=f"Plan {token}",
            status=PaymentPlan.Status.ACTIVE,
            direction=PaymentPlan.Direction.RECEIVABLE,
            plan_type=PaymentPlan.PlanType.FIXED_INSTALLMENT,
            frequency=PaymentPlan.Frequency.MONTHLY,
            unit=unit,
            project=project,
            total_amount=Decimal("120000.00"),
            start_date=timezone.localdate(),
            number_of_installments=12,
            created_by=self.user,
        )

    def test_qualified_lead_transition_generates_scored_unit_and_project_matches(self):
        lead = self._create_lead(self.org, pipeline_stage=Lead.PipelineStage.INQUIRY)
        property_obj = self._create_property(self.org, is_active=True)
        unit = self._create_unit(property_obj, status=Unit.UnitStatus.AVAILABLE)
        project = self._create_project(self.org, property_obj=property_obj)
        self._create_payment_plan(self.org, unit=unit)
        self._create_payment_plan(self.org, project=project)

        res = self.client.patch(
            f"/api/crm/leads/{lead.id}/",
            {"pipeline_stage": Lead.PipelineStage.QUALIFIED},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        active_matches = LeadPropertyMatch.objects.filter(lead=lead, is_active=True)
        self.assertTrue(
            active_matches.filter(candidate_type=LeadPropertyMatch.CandidateType.UNIT).exists()
        )
        self.assertTrue(
            active_matches.filter(candidate_type=LeadPropertyMatch.CandidateType.PROJECT).exists()
        )
        first_match = active_matches.order_by("-match_score").first()
        self.assertIsNotNone(first_match)
        self.assertIn("budget", first_match.score_breakdown)
        self.assertIn("location", first_match.score_breakdown)
        self.assertIn("unit_type", first_match.score_breakdown)
        self.assertIn("payment_eligibility", first_match.score_breakdown)

    def test_only_available_units_are_recommended(self):
        lead = self._create_lead(self.org, pipeline_stage=Lead.PipelineStage.QUALIFIED)
        property_obj = self._create_property(self.org, is_active=True)
        available_unit = self._create_unit(property_obj, status=Unit.UnitStatus.AVAILABLE)
        reserved_unit = self._create_unit(property_obj, status=Unit.UnitStatus.RESERVED)

        recompute_matches_for_lead(lead=lead, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)

        matched_unit_ids = set(
            LeadPropertyMatch.objects.filter(
                lead=lead,
                is_active=True,
                candidate_type=LeadPropertyMatch.CandidateType.UNIT,
            ).values_list("unit_id", flat=True)
        )
        self.assertIn(available_unit.id, matched_unit_ids)
        self.assertNotIn(reserved_unit.id, matched_unit_ids)

    def test_scoring_uses_40_25_20_15_weighting_with_breakdown(self):
        lead = self._create_lead(self.org, pipeline_stage=Lead.PipelineStage.QUALIFIED)
        property_obj = self._create_property(self.org, is_active=True, address="Mainland Axis")

        full_fit_unit = self._create_unit(
            property_obj,
            status=Unit.UnitStatus.AVAILABLE,
            category=Unit.UnitCategory.APARTMENT,
            asking_price=Decimal("120000.00"),
            location_description="Lekki Phase 1",
        )
        partial_fit_unit = self._create_unit(
            property_obj,
            status=Unit.UnitStatus.AVAILABLE,
            category=Unit.UnitCategory.WAREHOUSE,
            asking_price=Decimal("120000.00"),
            location_description="Yaba Mainland",
        )
        self._create_payment_plan(self.org, unit=full_fit_unit)

        recompute_matches_for_lead(lead=lead, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)

        full_match = LeadPropertyMatch.objects.get(
            lead=lead,
            candidate_type=LeadPropertyMatch.CandidateType.UNIT,
            unit=full_fit_unit,
        )
        self.assertEqual(full_match.match_score, Decimal("100.00"))
        self.assertEqual(full_match.score_breakdown["budget"], 40.0)
        self.assertEqual(full_match.score_breakdown["location"], 25.0)
        self.assertEqual(full_match.score_breakdown["unit_type"], 20.0)
        self.assertEqual(full_match.score_breakdown["payment_eligibility"], 15.0)

        partial_match = LeadPropertyMatch.objects.get(
            lead=lead,
            candidate_type=LeadPropertyMatch.CandidateType.UNIT,
            unit=partial_fit_unit,
        )
        self.assertEqual(partial_match.match_score, Decimal("40.00"))
        self.assertEqual(partial_match.score_breakdown["budget"], 40.0)
        self.assertEqual(partial_match.score_breakdown["location"], 0.0)
        self.assertEqual(partial_match.score_breakdown["unit_type"], 0.0)
        self.assertEqual(partial_match.score_breakdown["payment_eligibility"], 0.0)
        self.assertIn("Budget aligned", partial_match.reason_summary)

    def test_property_launch_signal_triggers_on_create_active_and_first_activation(self):
        with patch("apps.crm.matching.generate_matches_for_property_launch") as mock_launch:
            with self.captureOnCommitCallbacks(execute=True):
                self._create_property(self.org, is_active=True)
            self.assertEqual(mock_launch.call_count, 1)

            mock_launch.reset_mock()
            inactive_property = self._create_property(self.org, is_active=False)
            with self.captureOnCommitCallbacks(execute=True):
                inactive_property.is_active = True
                inactive_property.save(update_fields=["is_active"])
            self.assertEqual(mock_launch.call_count, 1)

    def test_property_launch_notifications_include_assigned_owner_and_admins(self):
        lead = self._create_lead(
            self.org,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            assigned_to=self.owner,
        )
        property_obj = self._create_property(self.org, is_active=True)
        self._create_unit(property_obj, status=Unit.UnitStatus.AVAILABLE)

        with patch("apps.notifications.services.dispatch_workflow_notification") as mock_dispatch:
            result = generate_matches_for_property_launch(property_obj=property_obj, actor=self.user)

        self.assertEqual(result["leads_refreshed"], 1)
        self.assertEqual(result["notifications_sent"], 1)
        self.assertTrue(mock_dispatch.called)

        recipients = {user.id for user in mock_dispatch.call_args.kwargs["recipients"]}
        self.assertIn(self.owner.id, recipients)
        admin_ids = set(
            UserProfile.objects.filter(
                organization=self.org,
                role="admin",
                user__is_active=True,
            ).values_list("user_id", flat=True)
        )
        self.assertTrue(admin_ids.issubset(recipients))
        self.assertEqual(
            lead.activities.filter(subject="Property launch match suggestions refreshed").count(),
            1,
        )

    def test_recompute_is_idempotent_without_duplicate_active_matches(self):
        lead = self._create_lead(self.org, pipeline_stage=Lead.PipelineStage.QUALIFIED)
        property_obj = self._create_property(self.org, is_active=True)
        self._create_unit(property_obj, status=Unit.UnitStatus.AVAILABLE)
        self._create_project(self.org, property_obj=property_obj)

        first = recompute_matches_for_lead(lead=lead, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)
        second = recompute_matches_for_lead(lead=lead, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)

        self.assertGreater(first["active_count"], 0)
        self.assertEqual(second["created_count"], 0)

        active_matches = LeadPropertyMatch.objects.filter(lead=lead, is_active=True)
        self.assertEqual(active_matches.count(), first["active_count"])
        unique_keys = {
            (row.candidate_type, row.unit_id, row.project_id)
            for row in active_matches
        }
        self.assertEqual(len(unique_keys), active_matches.count())

    def test_match_status_patch_transitions_persist(self):
        lead = self._create_lead(self.org, pipeline_stage=Lead.PipelineStage.QUALIFIED)
        property_obj = self._create_property(self.org, is_active=True)
        self._create_unit(property_obj, status=Unit.UnitStatus.AVAILABLE)
        recompute_matches_for_lead(lead=lead, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)

        match = LeadPropertyMatch.objects.filter(lead=lead, is_active=True).first()
        self.assertIsNotNone(match)

        res_shortlist = self.client.patch(
            f"/api/crm/property-matches/{match.id}/",
            {"status": LeadPropertyMatch.MatchStatus.SHORTLISTED},
            format="json",
        )
        self.assertEqual(res_shortlist.status_code, status.HTTP_200_OK, res_shortlist.data)
        match.refresh_from_db()
        self.assertEqual(match.status, LeadPropertyMatch.MatchStatus.SHORTLISTED)

        res_dismiss = self.client.patch(
            f"/api/crm/property-matches/{match.id}/",
            {"status": LeadPropertyMatch.MatchStatus.DISMISSED},
            format="json",
        )
        self.assertEqual(res_dismiss.status_code, status.HTTP_200_OK, res_dismiss.data)
        match.refresh_from_db()
        self.assertEqual(match.status, LeadPropertyMatch.MatchStatus.DISMISSED)

    def test_org_scoping_blocks_cross_org_property_matches_access(self):
        scoped_admin = self._create_user(self.org, role="admin")
        self.client.force_authenticate(scoped_admin)

        lead_org_2 = self._create_lead(
            self.org_2,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            preferred_locations=["Abuja"],
        )
        property_org_2 = self._create_property(self.org_2, is_active=True, address="Abuja")
        self._create_unit(property_org_2, status=Unit.UnitStatus.AVAILABLE, location_description="Abuja")
        recompute_matches_for_lead(lead=lead_org_2, source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH)

        list_res = self.client.get(
            "/api/crm/property-matches/",
            {"lead_id": lead_org_2.id},
            format="json",
        )
        self.assertEqual(list_res.status_code, status.HTTP_200_OK, list_res.data)
        self.assertEqual(list_res.data["count"], 0)

        refresh_res = self.client.post(
            "/api/crm/property-matches/refresh/",
            {"lead_id": lead_org_2.id},
            format="json",
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_404_NOT_FOUND, refresh_res.data)
