from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import Lead, LeadActivity
from apps.finance.models import Bill, BillLineItem
from apps.procurement.models import PurchaseRequisition, PurchaseRequisitionItem, Vendor


class NestedResourceOrgScopingTests(APITestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A")
        self.org_b = Organization.objects.create(name="Org B")

        self.user_a = self._create_org_admin(
            username="org-a-admin@example.com",
            email="org-a-admin@example.com",
            organization=self.org_a,
        )
        self._create_org_admin(
            username="org-b-admin@example.com",
            email="org-b-admin@example.com",
            organization=self.org_b,
        )

        self.vendor_a = Vendor.objects.create(name="Vendor A", organization=self.org_a)
        self.vendor_b = Vendor.objects.create(name="Vendor B", organization=self.org_b)

        self.bill_a = Bill.objects.create(
            organization=self.org_a,
            vendor=self.vendor_a,
            issue_date=date.today(),
            due_date=date.today(),
        )
        self.bill_b = Bill.objects.create(
            organization=self.org_b,
            vendor=self.vendor_b,
            issue_date=date.today(),
            due_date=date.today(),
        )

        self.req_a = PurchaseRequisition.objects.create(
            organization=self.org_a,
            title="Org A requisition",
            requester="Ops",
            required_date=date.today(),
        )
        self.req_b = PurchaseRequisition.objects.create(
            organization=self.org_b,
            title="Org B requisition",
            requester="Ops",
            required_date=date.today(),
        )

        self.lead_a = Lead.objects.create(
            organization=self.org_a,
            first_name="Ava",
            last_name="Tenant",
        )
        self.lead_b = Lead.objects.create(
            organization=self.org_b,
            first_name="Ben",
            last_name="Tenant",
        )

    def _create_org_admin(self, *, username: str, email: str, organization: Organization):
        user = get_user_model().objects.create_user(
            username=username,
            email=email,
            password="StrongPass123!",
            is_staff=True,
        )
        profile = user.profile
        profile.organization = organization
        profile.role = "admin"
        profile.user_status = "active"
        profile.save(update_fields=["organization", "role", "user_status"])
        return user

    def test_finance_bill_line_items_block_cross_tenant_parent(self):
        self.client.force_authenticate(user=self.user_a)

        local_list = self.client.get(f"/api/finance/bills/{self.bill_a.pk}/line-items/")
        self.assertEqual(local_list.status_code, status.HTTP_200_OK)

        foreign_list = self.client.get(f"/api/finance/bills/{self.bill_b.pk}/line-items/")
        self.assertEqual(foreign_list.status_code, status.HTTP_404_NOT_FOUND)

        local_create = self.client.post(
            f"/api/finance/bills/{self.bill_a.pk}/line-items/",
            {
                "description": "Test line item",
                "quantity": "2",
                "unit_price": "25.00",
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(local_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BillLineItem.objects.filter(bill=self.bill_a).count(), 1)

        foreign_create = self.client.post(
            f"/api/finance/bills/{self.bill_b.pk}/line-items/",
            {
                "description": "Cross-tenant attempt",
                "quantity": "1",
                "unit_price": "10.00",
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(foreign_create.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(BillLineItem.objects.filter(bill=self.bill_b).count(), 0)

    def test_procurement_requisition_items_block_cross_tenant_parent(self):
        self.client.force_authenticate(user=self.user_a)

        local_list = self.client.get(f"/api/procurement/requisitions/{self.req_a.pk}/items/")
        self.assertEqual(local_list.status_code, status.HTTP_200_OK)

        foreign_list = self.client.get(f"/api/procurement/requisitions/{self.req_b.pk}/items/")
        self.assertEqual(foreign_list.status_code, status.HTTP_404_NOT_FOUND)

        local_create = self.client.post(
            f"/api/procurement/requisitions/{self.req_a.pk}/items/",
            {
                "description": "Paper",
                "quantity": "3",
                "unit_of_measure": "box",
                "estimated_unit_price": "12.00",
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(local_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseRequisitionItem.objects.filter(requisition=self.req_a).count(), 1)

        foreign_create = self.client.post(
            f"/api/procurement/requisitions/{self.req_b.pk}/items/",
            {
                "description": "Cross-tenant attempt",
                "quantity": "1",
                "unit_of_measure": "ea",
                "estimated_unit_price": "10.00",
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(foreign_create.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(PurchaseRequisitionItem.objects.filter(requisition=self.req_b).count(), 0)

    def test_crm_lead_activities_block_cross_tenant_parent(self):
        self.client.force_authenticate(user=self.user_a)

        local_list = self.client.get(f"/api/crm/leads/{self.lead_a.pk}/activities/")
        self.assertEqual(local_list.status_code, status.HTTP_200_OK)

        foreign_list = self.client.get(f"/api/crm/leads/{self.lead_b.pk}/activities/")
        self.assertEqual(foreign_list.status_code, status.HTTP_404_NOT_FOUND)

        local_create = self.client.post(
            f"/api/crm/leads/{self.lead_a.pk}/activities/",
            {
                "activity_type": "call",
                "subject": "Initial qualification call",
                "description": "Captured needs and timeline.",
                "is_completed": False,
            },
            format="json",
        )
        self.assertEqual(local_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LeadActivity.objects.filter(lead=self.lead_a).count(), 1)

        foreign_create = self.client.post(
            f"/api/crm/leads/{self.lead_b.pk}/activities/",
            {
                "activity_type": "call",
                "subject": "Cross-tenant attempt",
                "description": "Should not be allowed.",
                "is_completed": False,
            },
            format="json",
        )
        self.assertEqual(foreign_create.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(LeadActivity.objects.filter(lead=self.lead_b).count(), 0)
