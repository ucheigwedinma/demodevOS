from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import ContactAccount
from apps.finance.models import Customer, Invoice
from apps.partners.models import (
    BudgetScope,
    OnboardingTemplate,
    PartnerEntitlement,
    PartnerOnboardingCase,
    PartnerType,
    PortalRole,
)
from apps.properties.models import Property
from apps.support_desk.models import SupportTicket

User = get_user_model()


class SupportDeskCustomerTicketingAutomationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Support Desk CRM Integration Org")
        self.admin = User.objects.create_superuser(
            username="support-admin@example.com",
            email="support-admin@example.com",
            password="Pass123!",
        )
        profile = self.admin.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.admin)

        self.customer = Customer.objects.create(
            organization=self.org,
            name="Ayo Investments",
            contact_person="Ayo Danjuma",
            email="ayo.customer@example.com",
            phone="+2348011110000",
            support_ticketing_enabled=False,
        )
        self.property = Property.objects.create(
            organization=self.org,
            name="Ayo Business Park",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="14 Admiralty Way, Lekki",
        )
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            property=self.property,
            invoice_number="INV-SD-1001",
            status=Invoice.Status.SENT,
            issue_date="2026-03-01",
            due_date="2026-03-15",
            subtotal=Decimal("125000.00"),
            total_amount=Decimal("125000.00"),
        )
        self.contact = ContactAccount.objects.create(
            organization=self.org,
            entity_type=ContactAccount.EntityType.INDIVIDUAL,
            first_name="Ayo",
            last_name="Danjuma",
            email="ayo.customer@example.com",
            phone="+2348011110000",
            finance_customer=self.customer,
            kyc_status=ContactAccount.KYCStatus.VERIFIED,
        )

        self.template = OnboardingTemplate.objects.create(
            organization=self.org,
            partner_type=PartnerType.CLIENT,
            code="client_ticketing_automation_v1",
            name="Client Ticketing Automation Template",
            description="Template for support ticketing enablement checks.",
            is_active=True,
            is_default=False,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.case = PartnerOnboardingCase.objects.create(
            organization=self.org,
            partner_type=PartnerType.CLIENT,
            status=PartnerOnboardingCase.Status.APPROVED,
            template=self.template,
            title="Ayo Client Onboarding",
            contact_name="Ayo Danjuma",
            contact_email="ayo.customer@example.com",
            customer=self.customer,
            created_by=self.admin,
            updated_by=self.admin,
        )
        PartnerEntitlement.objects.create(
            case=self.case,
            organization=self.org,
            portal_role=PortalRole.CLIENT,
            budget_scope=BudgetScope.NONE,
            is_active=True,
            created_by=self.admin,
        )

    def test_complaint_ticket_requires_linked_customer_profile(self):
        response = self.client.post(
            "/api/support-desk/tickets/",
            {
                "subject": "Complaint without profile link",
                "description": "Customer profile was not attached.",
                "category": SupportTicket.Category.COMPLAINT,
                "priority": SupportTicket.Priority.MEDIUM,
                "status": SupportTicket.Status.OPEN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("linked to a customer profile", str(response.data))

    def test_grant_portal_access_enables_ticketing_and_complaint_links_customer(self):
        blocked = self.client.post(
            "/api/support-desk/tickets/",
            {
                "subject": "Delayed allocation complaint",
                "description": "Allocation timeline was missed.",
                "category": SupportTicket.Category.COMPLAINT,
                "priority": SupportTicket.Priority.HIGH,
                "status": SupportTicket.Status.OPEN,
                "contact_account": self.contact.id,
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST, blocked.data)
        self.assertIn("Support ticketing is not enabled", str(blocked.data))

        grant = self.client.post(
            f"/api/partners/cases/{self.case.id}/grant-portal-access/",
            {},
            format="json",
        )
        self.assertEqual(grant.status_code, status.HTTP_200_OK, grant.data)

        self.customer.refresh_from_db()
        self.assertTrue(self.customer.support_ticketing_enabled)
        self.assertIsNotNone(self.customer.support_ticketing_enabled_at)

        created = self.client.post(
            "/api/support-desk/tickets/",
            {
                "subject": "Delayed allocation complaint",
                "description": "Allocation timeline was missed.",
                "category": SupportTicket.Category.COMPLAINT,
                "priority": SupportTicket.Priority.HIGH,
                "status": SupportTicket.Status.OPEN,
                "contact_account": self.contact.id,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

        ticket = SupportTicket.objects.get(id=created.data["id"])
        self.assertEqual(ticket.contact_account_id, self.contact.id)
        self.assertEqual(ticket.customer_id, self.customer.id)
        self.assertEqual(ticket.category, SupportTicket.Category.COMPLAINT)

        detail = self.client.get(f"/api/support-desk/tickets/{ticket.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertEqual(detail.data["customer"], self.customer.id)
        self.assertEqual(detail.data["contact_account"], self.contact.id)
        self.assertEqual(detail.data["customer_name"], self.customer.name)
        self.assertEqual(detail.data["contact_account_name"], self.contact.display_name)

    def test_billing_ticket_can_link_invoice_and_defaults_customer(self):
        created = self.client.post(
            "/api/support-desk/tickets/",
            {
                "subject": "Invoice reconciliation request",
                "description": "Need a copy of the billed utility breakdown.",
                "category": SupportTicket.Category.BILLING,
                "priority": SupportTicket.Priority.MEDIUM,
                "status": SupportTicket.Status.OPEN,
                "invoice": self.invoice.id,
                "contact_account": self.contact.id,
            },
            format="json",
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

        ticket = SupportTicket.objects.get(id=created.data["id"])
        self.assertEqual(ticket.invoice_id, self.invoice.id)
        self.assertEqual(ticket.customer_id, self.customer.id)

        detail = self.client.get(f"/api/support-desk/tickets/{ticket.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertEqual(detail.data["invoice"], self.invoice.id)
        self.assertEqual(detail.data["invoice_number"], self.invoice.invoice_number)
