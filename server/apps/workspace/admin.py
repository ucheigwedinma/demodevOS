from django.contrib import admin

from .models import Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    raw_id_fields = ("user", "invited_by")
    fields = ("user", "role", "joined_at", "notify_realtime", "digest_frequency")
    readonly_fields = ("joined_at",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "purpose",
        "visibility",
        "is_archived",
        "created_at",
    )
    list_filter = ("purpose", "visibility", "is_archived")
    search_fields = ("name", "slug", "description")
    raw_id_fields = ("organization", "project", "created_by")
    readonly_fields = ("slug", "created_at", "updated_at", "archived_at")
    inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("team__name", "user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("team", "user", "invited_by")
    readonly_fields = ("joined_at", "updated_at")
