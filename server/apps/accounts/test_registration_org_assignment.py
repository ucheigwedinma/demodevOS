from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Invitation, Organization
from apps.accounts.serializers import RegisterSerializer
from apps.properties.models import Property

User = get_user_model()


class RegisterOrganizationAssignmentTests(TestCase):
    def setUp(self):
        self.invited_org = Organization.objects.create(name="Invited Org")
        self.inviter = User.objects.create_user(
            username="inviter@example.com",
            email="inviter@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        inviter_profile = self.inviter.profile
        inviter_profile.organization = self.invited_org
        inviter_profile.role = "admin"
        inviter_profile.save(update_fields=["organization", "role"])

    @patch("apps.accounts.serializers.send_verification_email")
    def test_register_without_invitation_token_stays_in_bootstrap_workspace(self, _mock_email):
        invitation = Invitation.objects.create(
            email="newuser@example.com",
            organization=self.invited_org,
            invited_by=self.inviter,
            status="pending",
        )

        serializer = RegisterSerializer(
            data={
                "full_name": "New User",
                "email": "newuser@example.com",
                "password": "StrongPass123!",
                "org_name": "",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user = User.objects.get(email="newuser@example.com")
        expected_workspace_name = f"Workspace-{user.pk}"

        self.assertEqual(user.profile.organization.name, expected_workspace_name)
        self.assertNotEqual(user.profile.organization_id, self.invited_org.id)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "pending")

    def test_register_with_invitation_token_joins_invited_org(self):
        invitation = Invitation.objects.create(
            email="invitee@example.com",
            organization=self.invited_org,
            invited_by=self.inviter,
            status="pending",
        )

        serializer = RegisterSerializer(
            data={
                "full_name": "Invitee User",
                "email": "invitee@example.com",
                "password": "StrongPass123!",
                "invitation_token": str(invitation.token),
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user = User.objects.get(email="invitee@example.com")
        self.assertEqual(user.profile.organization_id, self.invited_org.id)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")

        bootstrap_workspace_name = f"Workspace-{user.pk}"
        self.assertFalse(Organization.objects.filter(name=bootstrap_workspace_name).exists())

    @patch("apps.accounts.serializers.send_verification_email")
    def test_register_avoids_attaching_to_preexisting_workspace_name_collision(self, _mock_email):
        next_user_pk = (User.objects.order_by("-id").first().id if User.objects.exists() else 0) + 1
        colliding_workspace_name = f"Workspace-{next_user_pk}"

        foreign_org = Organization.objects.create(name=colliding_workspace_name)
        Property.objects.create(
            organization=foreign_org,
            name="Legacy Property",
            property_type=Property.PropertyType.BUILDING,
            address="1 Legacy Street",
        )

        serializer = RegisterSerializer(
            data={
                "full_name": "Collision User",
                "email": "collision@example.com",
                "password": "StrongPass123!",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user = User.objects.get(email="collision@example.com")
        self.assertNotEqual(user.profile.organization_id, foreign_org.id)
        self.assertEqual(
            Property.objects.filter(organization=user.profile.organization).count(),
            0,
        )
