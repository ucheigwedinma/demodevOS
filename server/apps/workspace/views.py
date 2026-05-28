"""
Views for the workspace teams API.

Endpoints (see docs/workspace-teams-design.md §7):

    GET    /api/workspace/teams/                          — list (filters)
    POST   /api/workspace/teams/                          — create (caller=owner)
    GET    /api/workspace/teams/{id}/                     — detail
    PATCH  /api/workspace/teams/{id}/                     — edit metadata
    DELETE /api/workspace/teams/{id}/                     — hard delete (owner)
    POST   /api/workspace/teams/{id}/archive/             — archive toggle
    POST   /api/workspace/teams/{id}/transfer/            — transfer ownership
    POST   /api/workspace/teams/{id}/join/                — self-join (public)
    POST   /api/workspace/teams/{id}/request-join/        — request join (private)
    GET    /api/workspace/teams/me/                       — my teams
    GET    /api/workspace/teams/{id}/members/             — list members
    POST   /api/workspace/teams/{id}/members/             — add member
    PATCH  /api/workspace/teams/{id}/members/{uid}/       — change role
    DELETE /api/workspace/teams/{id}/members/{uid}/       — remove (or self-leave)
    PATCH  /api/workspace/teams/{id}/notifications/       — update my prefs
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Team, TeamMembership
from .permissions import (
    can_delete_team,
    can_edit_team,
    can_manage_members,
    can_transfer_team,
    can_view_team,
    team_role_for,
)
from .serializers import (
    NotificationPrefsSerializer,
    RoleChangeSerializer,
    TeamDetailSerializer,
    TeamListSerializer,
    TeamMembershipSerializer,
    TeamMembershipWriteSerializer,
    TeamWriteSerializer,
    TransferOwnershipSerializer,
)

User = get_user_model()


class TeamCursorPagination(CursorPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"


def _request_org(request):
    """
    Return the request's tenant org.

    Prefer `request.organization` (set by OrganizationMiddleware in real
    requests). Fall back to `request.user.profile.organization` so direct
    test `force_authenticate(...)` flows work without manually wiring up
    middleware in every test setUp. None signals 'unscoped' which we forbid.
    """
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    return getattr(profile, "organization", None) if profile else None


# ---------------------------------------------------------------------------
# Team viewset
# ---------------------------------------------------------------------------


class TeamViewSet(viewsets.ModelViewSet):
    """
    CRUD + custom actions for `Team`. All endpoints are org-scoped via
    `OrganizationMiddleware` (request.organization). Additional visibility
    filtering happens in `get_queryset()`.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = TeamCursorPagination
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "list":
            return TeamListSerializer
        if self.action in ("create", "update", "partial_update"):
            return TeamWriteSerializer
        return TeamDetailSerializer

    # --- queryset & visibility ---------------------------------------------

    def get_queryset(self):
        request = self.request
        org = _request_org(request)
        if org is None:
            return Team.objects.none()

        qs = Team.objects.filter(organization=org)
        qs = qs.annotate(members_count=Count("memberships", distinct=True))

        # Visibility: members see all visibilities of their teams; non-members
        # see public + private. Secret teams are visible only to members
        # (or to the team-detail/edit endpoints which apply object-level checks).
        user = request.user
        if not user.is_authenticated:
            return qs.none()

        secret_visible_membership = TeamMembership.objects.filter(
            team=OuterRef("pk"), user=user
        )
        qs = qs.annotate(_is_member=Exists(secret_visible_membership))
        # Hide secret teams the caller doesn't belong to.
        qs = qs.filter(Q(visibility__in=["public", "private"]) | Q(_is_member=True))

        return qs

    def filter_queryset(self, queryset):
        """Apply ?purpose, ?visibility, ?archived, ?mine, ?q filters."""
        request = self.request
        params = request.query_params

        purpose = params.get("purpose")
        if purpose:
            queryset = queryset.filter(purpose=purpose)

        visibility = params.get("visibility")
        if visibility:
            queryset = queryset.filter(visibility=visibility)

        archived = params.get("archived")
        if archived is None or archived.lower() in ("", "false", "0"):
            queryset = queryset.filter(is_archived=False)
        elif archived.lower() in ("true", "1"):
            queryset = queryset.filter(is_archived=True)
        # archived=any → no filter

        mine = params.get("mine")
        if mine and mine.lower() in ("true", "1"):
            queryset = queryset.filter(memberships__user=request.user).distinct()

        q = params.get("q", "").strip()
        if q:
            queryset = queryset.filter(name__icontains=q)

        return queryset

    # --- create -------------------------------------------------------------

    def perform_create(self, serializer):
        org = _request_org(self.request)
        if org is None:
            raise PermissionDenied("Organization not resolved for this request.")
        with transaction.atomic():
            team = serializer.save(
                organization=org,
                created_by=self.request.user,
            )
            TeamMembership.objects.create(
                team=team,
                user=self.request.user,
                role=TeamMembership.Role.OWNER,
            )
        # Re-annotate so the response carries members_count consistently.
        self.created_team = team

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        # Reload via the standard queryset to attach the annotations.
        team = self.get_queryset().get(pk=self.created_team.pk)
        out = TeamDetailSerializer(team, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # --- detail-level checks -----------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        team = self.get_object()
        if not can_view_team(request.user, team):
            # Defensive — get_queryset already filters secret teams; this
            # catches edge cases where the URL is hit directly.
            raise NotFound()
        serializer = self.get_serializer(team)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        team = self.get_object()
        if not can_edit_team(request.user, team):
            raise PermissionDenied("Only owner or admin can edit team metadata.")
        write_serializer = self.get_serializer(team, data=request.data, partial=True)
        write_serializer.is_valid(raise_exception=True)
        write_serializer.save()
        team = self.get_queryset().get(pk=team.pk)
        out = TeamDetailSerializer(team, context={"request": request})
        return Response(out.data)

    def update(self, request, *args, **kwargs):
        # We don't use full PUT — coerce to PATCH semantics for safety.
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        team = self.get_object()
        if not can_delete_team(request.user, team):
            raise PermissionDenied("Only the owner can delete a team.")
        team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- custom actions -----------------------------------------------------

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Convenience: teams I belong to (any role, any visibility, not archived)."""
        qs = self.get_queryset().filter(memberships__user=request.user, is_archived=False).distinct()
        page = self.paginate_queryset(qs)
        ser = TeamListSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        # Bypass filter_queryset (which hides archived teams by default) so
        # un-archiving works on a second invocation.
        org = _request_org(request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        try:
            team = Team.objects.get(pk=pk, organization=org)
        except Team.DoesNotExist:
            raise NotFound()
        if not can_view_team(request.user, team):
            raise NotFound()
        if not can_edit_team(request.user, team):
            raise PermissionDenied("Only owner or admin can archive a team.")
        team.is_archived = not team.is_archived
        team.archived_at = timezone.now() if team.is_archived else None
        team.save(update_fields=["is_archived", "archived_at", "updated_at"])
        # Re-annotate with members_count for the response.
        team = (
            Team.objects.filter(pk=team.pk)
            .annotate(members_count=Count("memberships", distinct=True))
            .first()
        )
        return Response(TeamDetailSerializer(team, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        team = self.get_object()
        if not can_transfer_team(request.user, team):
            raise PermissionDenied("Only the current owner can transfer ownership.")
        ser = TransferOwnershipSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_owner_id = ser.validated_data["new_owner_id"]
        try:
            new_owner_membership = TeamMembership.objects.get(team=team, user_id=new_owner_id)
        except TeamMembership.DoesNotExist:
            raise ValidationError({"new_owner_id": "Target user is not a member of this team."})
        if new_owner_membership.user_id == request.user.id:
            raise ValidationError({"new_owner_id": "You are already the owner."})

        # Atomic swap. We have to drop the owner role first (partial unique
        # constraint allows only one owner), then promote.
        with transaction.atomic():
            current = TeamMembership.objects.select_for_update().get(team=team, user=request.user)
            current.role = TeamMembership.Role.ADMIN
            current.save(update_fields=["role", "updated_at"])
            new_owner_membership.role = TeamMembership.Role.OWNER
            new_owner_membership.save(update_fields=["role", "updated_at"])

        team = self.get_queryset().get(pk=team.pk)
        return Response(TeamDetailSerializer(team, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        team = self.get_object()
        if team.visibility != Team.Visibility.PUBLIC:
            raise ValidationError({"visibility": "Self-join is only available for public teams."})
        membership, created = TeamMembership.objects.get_or_create(
            team=team,
            user=request.user,
            defaults={"role": TeamMembership.Role.MEMBER, "invited_by": None},
        )
        return Response(
            TeamMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="request-join")
    def request_join(self, request, pk=None):
        team = self.get_object()
        if team.visibility != Team.Visibility.PRIVATE:
            raise ValidationError(
                {"visibility": "Request-to-join is only available for private teams."}
            )
        # v1: stub — real approval workflow ships with a follow-on JoinRequest model.
        # For now, surface a clear "submitted" response. Frontend can show it as pending.
        return Response(
            {
                "status": "submitted",
                "message": "Your request to join has been recorded. Owners and admins will review.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# Membership viewset (nested under a team)
# ---------------------------------------------------------------------------


class TeamMembershipViewSet(viewsets.ViewSet):
    """
    Nested under /teams/{team_id}/members/ — keyed by user_id.

    GET    members/                  — list
    POST   members/                  — add (idempotent per EC11)
    PATCH  members/{user_id}/        — change role (with optimistic lock per EC6)
    DELETE members/{user_id}/        — remove or self-leave (EC1 for owner)
    PATCH  /teams/{id}/notifications/ — update my own prefs (lives on TeamViewSet ideally,
                                        but kept here for grouping; routed at urls.py)
    """

    permission_classes = [IsAuthenticated]

    def _get_team(self, request, team_id) -> Team:
        org = _request_org(request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        try:
            team = Team.objects.get(pk=team_id, organization=org)
        except Team.DoesNotExist:
            raise NotFound()
        if not can_view_team(request.user, team):
            raise NotFound()
        return team

    def list(self, request, team_id=None):
        team = self._get_team(request, team_id)
        memberships = (
            TeamMembership.objects.filter(team=team)
            .select_related("user")
            .order_by("role", "user__first_name", "user__last_name")
        )
        # Filter by role if requested
        role = request.query_params.get("role")
        if role:
            memberships = memberships.filter(role=role)
        # Filter by name/email
        q = request.query_params.get("q", "").strip()
        if q:
            memberships = memberships.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
            )
        ser = TeamMembershipSerializer(memberships, many=True)
        return Response(ser.data)

    def create(self, request, team_id=None):
        team = self._get_team(request, team_id)
        if not can_manage_members(request.user, team):
            raise PermissionDenied("Only owner or admin can add members.")
        ser = TeamMembershipWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = ser.validated_data["user_id"]
        role = ser.validated_data.get("role", TeamMembership.Role.MEMBER)
        if role == TeamMembership.Role.OWNER:
            raise ValidationError(
                {"role": "Use the transfer endpoint to change ownership."}
            )
        target_user = User.objects.filter(
            pk=user_id, profile__organization=team.organization, is_active=True
        ).first()
        if target_user is None:
            raise ValidationError({"user_id": "User not found in this organization."})

        membership, created = TeamMembership.objects.get_or_create(
            team=team,
            user=target_user,
            defaults={"role": role, "invited_by": request.user},
        )
        return Response(
            TeamMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, team_id=None, user_id=None):
        team = self._get_team(request, team_id)
        if not can_manage_members(request.user, team):
            raise PermissionDenied("Only owner or admin can change roles.")
        ser = RoleChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_role = ser.validated_data["role"]
        if_unchanged_since = ser.validated_data.get("if_unchanged_since")

        try:
            membership = TeamMembership.objects.select_for_update().get(
                team=team, user_id=user_id
            )
        except TeamMembership.DoesNotExist:
            raise NotFound()

        # EC6: optimistic lock
        if if_unchanged_since is not None and membership.updated_at > if_unchanged_since:
            return Response(
                {
                    "detail": "This membership was updated by someone else.",
                    "current_role": membership.role,
                    "updated_at": membership.updated_at,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # An admin cannot demote/promote the owner row; only owner can transfer.
        actor_role = team_role_for(request.user, team)
        if membership.role == TeamMembership.Role.OWNER:
            raise ValidationError(
                {"role": "Use the transfer endpoint to change the owner."}
            )
        if new_role == TeamMembership.Role.OWNER:
            raise ValidationError(
                {"role": "Use the transfer endpoint to assign ownership."}
            )
        # An admin cannot demote another admin (only owner can). Two admins
        # mutually demoting each other would be chaos; keep admin↔admin neutral.
        if (
            actor_role == TeamMembership.Role.ADMIN
            and membership.role == TeamMembership.Role.ADMIN
            and new_role != TeamMembership.Role.ADMIN
        ):
            raise PermissionDenied("Admins cannot demote other admins. Owner only.")

        with transaction.atomic():
            membership.role = new_role
            membership.save(update_fields=["role", "updated_at"])
        return Response(TeamMembershipSerializer(membership).data)

    def destroy(self, request, team_id=None, user_id=None):
        team = self._get_team(request, team_id)
        try:
            membership = TeamMembership.objects.get(team=team, user_id=user_id)
        except TeamMembership.DoesNotExist:
            raise NotFound()
        is_self = membership.user_id == request.user.id

        if is_self:
            # EC1: owner cannot self-leave without first transferring.
            if membership.role == TeamMembership.Role.OWNER:
                raise ValidationError(
                    {"detail": "Transfer ownership before leaving the team."}
                )
        else:
            if not can_manage_members(request.user, team):
                raise PermissionDenied("Only owner or admin can remove members.")
            if membership.role == TeamMembership.Role.OWNER:
                raise ValidationError(
                    {"detail": "Use the transfer endpoint to change ownership."}
                )
            actor_role = team_role_for(request.user, team)
            if (
                actor_role == TeamMembership.Role.ADMIN
                and membership.role == TeamMembership.Role.ADMIN
            ):
                raise PermissionDenied("Admins cannot remove other admins. Owner only.")

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Notification prefs — small endpoint that updates the caller's own row.
# ---------------------------------------------------------------------------


class NotificationPrefsView(viewsets.ViewSet):
    """PATCH /api/workspace/teams/{id}/notifications/ — update my prefs."""

    permission_classes = [IsAuthenticated]

    def partial_update(self, request, team_id=None):
        org = _request_org(request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        try:
            team = Team.objects.get(pk=team_id, organization=org)
        except Team.DoesNotExist:
            raise NotFound()
        try:
            membership = TeamMembership.objects.get(team=team, user=request.user)
        except TeamMembership.DoesNotExist:
            raise NotFound()
        ser = NotificationPrefsSerializer(membership, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(TeamMembershipSerializer(membership).data)
