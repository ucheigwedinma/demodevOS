from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admin_mixins import OrgScopedAdminMixin

from .models import (
    ActiveSubscriptionAddOn,
    Invitation,
    OAuthConnection,
    Organization,
    OrganizationSubscription,
    SubscriptionEvent,
    UserAuthSession,
    UserIntegrationConnection,
    UserProfile,
    UserSecurityEvent,
)


@admin.register(Organization)
class OrganizationAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "pk"
    list_display = ("name", "industry", "size", "created_by", "created_at")
    search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("user", "organization", "role", "has_completed_tour", "has_completed_onboarding")
    list_filter = ("role", "has_completed_tour", "has_completed_onboarding")
    raw_id_fields = ("user",)


@admin.register(Invitation)
class InvitationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("email", "organization", "invited_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("email",)


@admin.register(OAuthConnection)
class OAuthConnectionAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "user__profile__organization"
    list_display = ("user", "provider", "email", "connected_at", "last_login_at")
    list_filter = ("provider",)
    search_fields = ("user__email", "email", "provider_user_id")
    raw_id_fields = ("user",)


@admin.register(UserIntegrationConnection)
class UserIntegrationConnectionAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "user__profile__organization"
    list_display = ("user", "provider", "status", "account_label", "connected_at", "last_token_refresh_at")
    list_filter = ("provider", "status")
    search_fields = ("user__email", "account_label", "external_account_id")
    raw_id_fields = ("user",)


@admin.register(UserAuthSession)
class UserAuthSessionAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "user__profile__organization"
    list_display = (
        "user",
        "auth_provider",
        "device_label",
        "ip_address",
        "created_at",
        "last_seen_at",
        "revoked_at",
    )
    list_filter = ("auth_provider", "revoked_at")
    search_fields = ("user__email", "device_label", "ip_address")
    raw_id_fields = ("user",)


@admin.register(UserSecurityEvent)
class UserSecurityEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "user__profile__organization"
    list_display = (
        "event_type",
        "status",
        "user",
        "principal",
        "provider",
        "ip_address",
        "occurred_at",
    )
    list_filter = ("event_type", "status", "provider")
    search_fields = ("user__email", "principal", "ip_address", "device_label")
    raw_id_fields = ("user",)


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ("organization", "edition", "status", "billing_cycle", "current_period_end", "auto_renew")
    list_filter = ("status", "billing_cycle")
    search_fields = ("organization__name",)
    raw_id_fields = ("organization", "edition")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "subscription__organization"
    list_display = ("subscription", "event_type", "from_edition", "to_edition", "actor", "occurred_at")
    list_filter = ("event_type",)
    search_fields = ("subscription__organization__name",)
    raw_id_fields = ("subscription", "from_edition", "to_edition", "actor")
    readonly_fields = ("occurred_at",)


@admin.register(ActiveSubscriptionAddOn)
class ActiveSubscriptionAddOnAdmin(OrgScopedAdminMixin, ModelAdmin):
    org_lookup = "subscription__organization"
    list_display = ("subscription", "add_on", "activated_at")
    list_filter = ("add_on__add_on_type",)
    search_fields = ("subscription__organization__name", "add_on__name")
    raw_id_fields = ("subscription", "add_on")
    readonly_fields = ("activated_at",)
