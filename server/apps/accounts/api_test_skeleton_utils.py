from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework.test import APITestCase

from apps.accounts.models import Organization


class APISkeletonBaseTestCase(APITestCase):
    """Shared setup helpers for API skeleton tests."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.organization = Organization.objects.create(
            name="QA Skeleton Org",
        )

        cls.superuser = user_model.objects.create_user(
            username="qa-admin@example.com",
            email="qa-admin@example.com",
            password="StrongPass123!",
            is_superuser=True,
            is_staff=True,
        )
        super_profile = cls.superuser.profile
        super_profile.organization = cls.organization
        super_profile.role = "admin"
        super_profile.user_status = "active"
        super_profile.save(
            update_fields=["organization", "role", "user_status"]
        )

        cls.member = user_model.objects.create_user(
            username="qa-member@example.com",
            email="qa-member@example.com",
            password="StrongPass123!",
            is_staff=False,
        )
        member_profile = cls.member.profile
        member_profile.organization = cls.organization
        member_profile.role = "member"
        member_profile.user_status = "active"
        member_profile.save(
            update_fields=["organization", "role", "user_status"]
        )

    def authenticate_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)

    def authenticate_as_member(self):
        self.client.force_authenticate(user=self.member)

    def todo_case(self, case_id: str, title: str):
        self.skipTest(f"TODO {case_id}: {title}")


def build_todo_test(case_id: str, title: str):
    def _test(self):
        self.todo_case(case_id, title)

    method_name = f"test_{case_id.lower()}_{slugify(title).replace('-', '_')}"
    _test.__name__ = method_name
    _test.__doc__ = f"{case_id}: {title}"
    return method_name, _test
