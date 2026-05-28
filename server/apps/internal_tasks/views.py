"""
Views for the Internal Tasks API.

See docs/workspace-internal-tasks-design.md §7 + §8 + §12 for the contract,
permissions matrix, and overlay endpoint shape.

Endpoints (all under /api/internal-tasks/):
- GET    /tasks/                         — list (cursor-paginated)
- POST   /tasks/                         — create (caller = creator; default assignee=creator)
- GET    /tasks/{id}/                    — detail
- PATCH  /tasks/{id}/                    — edit (creator OR assignee)
- DELETE /tasks/{id}/                    — delete (creator only)
- POST   /tasks/{id}/complete/           — toggle done / reopen
- POST   /tasks/{id}/assign/             — change assignee
- POST   /tasks/{id}/checklist/          — replace checklist_items
- GET    /tasks/{id}/comments/           — list comments
- POST   /tasks/{id}/comments/           — add comment
- DELETE /tasks/{id}/comments/{cid}/     — delete a comment (author only)
- GET    /tasks/me/                      — convenience: assignee=me, status!=done
- GET    /tasks/tags/                    — distinct visible tags ranked by frequency
- GET    /overlay/                       — read-only operational task overlay
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date as date_cls
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone as djtimezone
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Task, TaskComment
from .permissions import can_delete_task, can_edit_task, can_view_task, task_role_for
from .serializers import (
    AssignmentSerializer,
    ChecklistReplaceSerializer,
    TaskCommentSerializer,
    TaskCommentWriteSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskWriteSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def _request_org(request):
    """Resolve the request's organization (middleware-set, with fallback)."""
    return getattr(request, "organization", None) or _user_org(request.user)


def _user_org(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "organization", None) if profile else None


# ---------------------------------------------------------------------------
# Queryset visibility scoping (mirrors apps.calendar)
# ---------------------------------------------------------------------------


def _visible_task_queryset(user, org):
    """
    Base queryset for tasks visible to `user` in `org`. Applies §8 rules
    at query time:
      - creator OR assignee
      - visibility=org
      - visibility=team where user is a member of the team
      - excludes secret-team tasks the user isn't a member of
    """
    if user is None or not user.is_authenticated or org is None:
        return Task.objects.none()

    from apps.workspace.models import TeamMembership

    user_team_ids = TeamMembership.objects.filter(user=user).values("team_id")

    visibility_clause = (
        Q(creator=user)
        | Q(assignee=user)
        | Q(visibility=Task.Visibility.ORG)
        | Q(visibility=Task.Visibility.TEAM, team__in=user_team_ids)
    )
    qs = Task.objects.filter(organization=org).filter(visibility_clause).distinct()
    qs = qs.exclude(Q(team__visibility="secret") & ~Q(team__in=user_team_ids))
    return qs


class TaskCursorPagination(CursorPagination):
    page_size = 25
    ordering = "-created_at"


# ---------------------------------------------------------------------------
# Task viewset
# ---------------------------------------------------------------------------


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = TaskCursorPagination
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TaskWriteSerializer
        if self.action == "retrieve":
            return TaskDetailSerializer
        return TaskListSerializer

    def get_queryset(self):
        return _visible_task_queryset(self.request.user, _request_org(self.request))

    def filter_queryset(self, queryset):
        params = self.request.query_params
        request = self.request

        # status — supports multi-value comma-separated or repeated param
        status_values = self._multi_value(params, "status")
        if status_values:
            queryset = queryset.filter(status__in=status_values)

        # priority — same semantics
        priority_values = self._multi_value(params, "priority")
        if priority_values:
            queryset = queryset.filter(priority__in=priority_values)

        # assignee — id, "me", or "unassigned"
        assignee = params.get("assignee")
        if assignee:
            if assignee == "me":
                queryset = queryset.filter(assignee=request.user)
            elif assignee == "unassigned":
                queryset = queryset.filter(assignee__isnull=True)
            else:
                try:
                    queryset = queryset.filter(assignee_id=int(assignee))
                except ValueError:
                    pass

        # mine — convenience alias for assignee=me
        mine = params.get("mine")
        if mine and mine.lower() in ("1", "true"):
            queryset = queryset.filter(assignee=request.user)

        # team
        team = params.get("team")
        if team:
            try:
                queryset = queryset.filter(team_id=int(team))
            except ValueError:
                pass

        # tags — ?tag=foo&tag=bar (AND semantics — task must have ALL tags)
        tags = params.getlist("tag")
        for t in tags:
            tag = (t or "").strip().lower()
            if tag:
                queryset = queryset.filter(tags__contains=[tag])

        # due_before / due_after
        for key, op in (("due_before", "due_date__lte"), ("due_after", "due_date__gte")):
            raw = params.get(key)
            if raw:
                try:
                    parsed = date_cls.fromisoformat(raw)
                    queryset = queryset.filter(**{op: parsed})
                except ValueError:
                    pass

        # overdue
        overdue = params.get("overdue")
        if overdue and overdue.lower() in ("1", "true"):
            queryset = queryset.filter(
                due_date__lt=date_cls.today()
            ).exclude(status=Task.Status.DONE)

        # q — title ILIKE (per design §15: no full-text v1)
        q = (params.get("q") or "").strip()
        if q:
            queryset = queryset.filter(title__icontains=q)

        return queryset

    @staticmethod
    def _multi_value(params, key) -> list[str]:
        raw = params.getlist(key)
        out: list[str] = []
        for item in raw:
            for part in (item or "").split(","):
                part = part.strip()
                if part:
                    out.append(part)
        return out

    # ----- create ----------------------------------------------------------

    def perform_create(self, serializer):
        org = _request_org(self.request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        # Default assignee = creator if not provided.
        assignee = serializer.validated_data.get("assignee")
        if assignee is None and "assignee" not in serializer.initial_data:
            serializer.validated_data["assignee"] = self.request.user
        task = serializer.save(organization=org, creator=self.request.user)
        self.created_task = task

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        out = TaskDetailSerializer(self.created_task, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ----- partial_update --------------------------------------------------

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_edit_task(request.user, task):
            raise PermissionDenied("Only the creator or assignee can edit.")
        # Tighten: changing team/visibility is creator-only.
        if not can_delete_task(request.user, task):
            for restricted in ("team", "visibility"):
                if restricted in request.data:
                    raise PermissionDenied(
                        f"Only the creator can change {restricted}."
                    )
        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        task.refresh_from_db()
        return Response(TaskDetailSerializer(task, context={"request": request}).data)

    def update(self, request, *args, **kwargs):
        # We don't use PUT; coerce to PATCH semantics.
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)

    # ----- retrieve --------------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_view_task(request.user, task):
            raise NotFound()  # never reveal existence
        return Response(
            TaskDetailSerializer(task, context={"request": request}).data
        )

    # ----- destroy ---------------------------------------------------------

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_delete_task(request.user, task):
            raise PermissionDenied("Only the creator can delete this task.")
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ----- custom actions --------------------------------------------------

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Toggle status to done / reopen to todo."""
        task = self.get_object()
        if not can_edit_task(request.user, task):
            raise PermissionDenied("Only the creator or assignee can change status.")
        if task.status == Task.Status.DONE:
            task.status = Task.Status.TODO
        else:
            task.status = Task.Status.DONE
        task.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(
            TaskDetailSerializer(task, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        task = self.get_object()
        if not can_edit_task(request.user, task):
            raise PermissionDenied("Only the creator or assignee can reassign.")
        ser = AssignmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = ser.validated_data.get("user_id")
        if user_id is None:
            task.assignee = None
        else:
            target = User.objects.filter(
                pk=user_id,
                profile__organization=task.organization,
                is_active=True,
            ).first()
            if target is None:
                raise ValidationError({"user_id": "User not found in this organization."})
            task.assignee = target
        task.save(update_fields=["assignee", "updated_at"])
        return Response(
            TaskDetailSerializer(task, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="checklist")
    def replace_checklist(self, request, pk=None):
        task = self.get_object()
        if not can_edit_task(request.user, task):
            raise PermissionDenied("Only the creator or assignee can edit the checklist.")
        ser = ChecklistReplaceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        task.checklist_items = ser.validated_data["items"]
        task.save(update_fields=["checklist_items", "updated_at"])
        return Response(
            TaskDetailSerializer(task, context={"request": request}).data
        )

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """My open tasks (assignee=me, status != done)."""
        qs = self.get_queryset().filter(
            assignee=request.user
        ).exclude(status=Task.Status.DONE)
        # Same default sort as design §5.
        qs = qs.order_by(
            "-priority",  # 'urgent' > 'high' > 'medium' > 'low' won't sort
            # alphabetically right, so we use a Case expression for proper order
        )
        # Default sort per design: priority desc → due_date asc nulls last → created desc
        from django.db.models import Case, IntegerField, Value, When

        qs = qs.annotate(
            _prio_rank=Case(
                When(priority=Task.Priority.URGENT, then=Value(0)),
                When(priority=Task.Priority.HIGH, then=Value(1)),
                When(priority=Task.Priority.MEDIUM, then=Value(2)),
                When(priority=Task.Priority.LOW, then=Value(3)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            _due_null=Case(
                When(due_date__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by("_prio_rank", "_due_null", "due_date", "-created_at")
        page = self.paginate_queryset(qs)
        ser = TaskListSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="tags")
    def tags(self, request):
        """
        Distinct tags in the caller's visible task set, ranked by frequency.
        Used by the TagInput autocomplete.
        """
        qs = self.get_queryset().values_list("tags", flat=True)
        counter: Counter = Counter()
        for row in qs:
            for t in row or []:
                counter[t] += 1
        top = counter.most_common(50)
        return Response({"results": [{"tag": t, "count": c} for t, c in top]})


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TaskCommentView(viewsets.ViewSet):
    """Nested under /tasks/{task_id}/comments/."""

    permission_classes = [IsAuthenticated]

    def _get_task(self, request, task_id) -> Task:
        org = _request_org(request)
        try:
            task = Task.objects.get(pk=task_id, organization=org)
        except Task.DoesNotExist:
            raise NotFound()
        if not can_view_task(request.user, task):
            raise NotFound()
        return task

    def list(self, request, task_id=None):
        task = self._get_task(request, task_id)
        comments = (
            TaskComment.objects.filter(task=task)
            .select_related("author")
            .order_by("created_at")
        )
        return Response(TaskCommentSerializer(comments, many=True).data)

    def create(self, request, task_id=None):
        task = self._get_task(request, task_id)
        # Anyone who can view can comment.
        ser = TaskCommentWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = TaskComment.objects.create(
            task=task,
            author=request.user,
            body=ser.validated_data["body"],
        )
        return Response(
            TaskCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, task_id=None, comment_id=None):
        task = self._get_task(request, task_id)
        try:
            comment = TaskComment.objects.get(pk=comment_id, task=task)
        except TaskComment.DoesNotExist:
            raise NotFound()
        if comment.author_id != request.user.id:
            raise PermissionDenied("Only the comment's author can delete it.")
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Operational task overlay (read-only)
# ---------------------------------------------------------------------------

# Status mapping — operational source → internal_tasks enum (design §12).
# Notes on field-name discoveries during implementation:
#   ProjectTask  : organization FK; assigned_user FK; status enum
#                  {pending, in_progress, completed}; priority enum
#                  {low, medium, high, critical}; due_date DateField;
#                  title source = `name`.
#   FollowUpTask : NO direct org FK (scoped via lead.organization);
#                  assigned_to FK; status enum
#                  {pending, in_progress, completed, breached, escalated, cancelled};
#                  no priority; due_at DateTimeField (we expose .date());
#                  title composed as "rule.name — lead.name".
PROJECT_TASK_STATUS_MAP = {
    "pending": "todo",
    "in_progress": "in_progress",
    "completed": "done",
}
PROJECT_TASK_PRIORITY_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "urgent",
}
FOLLOWUP_TASK_STATUS_MAP = {
    "pending": "todo",
    "in_progress": "in_progress",
    "completed": "done",
    "breached": "blocked",
    "escalated": "blocked",
    "cancelled": "done",
}


class OverlayView(views.APIView):
    """
    GET /api/internal-tasks/overlay/?source=project_task,crm_follow_up&assignee=me|all&...

    Returns operational task rows in a flat shape consumable by the same
    EventCell-style renderer. Inherits the source apps' org scoping —
    we don't add a new layer (per design §12).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _request_org(request)
        if org is None:
            return Response({"results": []})

        sources = request.query_params.get("source", "project_task,crm_follow_up")
        wanted = {s.strip() for s in sources.split(",") if s.strip()}
        results: list[dict] = []

        if "project_task" in wanted:
            results.extend(self._project_task_rows(request, org))
        if "crm_follow_up" in wanted:
            results.extend(self._followup_task_rows(request, org))

        return Response({"results": results})

    # ----- ProjectTask -----------------------------------------------------

    def _project_task_rows(self, request, org) -> list[dict]:
        try:
            from apps.projects.models import ProjectTask
        except Exception:
            return []

        qs = ProjectTask.objects.filter(organization=org).select_related(
            "assigned_user", "phase__project"
        )
        qs = self._apply_overlay_filters(qs, request, assignee_field="assigned_user")

        rows: list[dict] = []
        for t in qs[:200]:  # safety cap
            mapped_status = PROJECT_TASK_STATUS_MAP.get(t.status, "todo")
            unmapped = t.status not in PROJECT_TASK_STATUS_MAP
            mapped_priority = PROJECT_TASK_PRIORITY_MAP.get(t.priority, "medium")
            rows.append({
                "source": "project_task",
                "id": t.id,
                "title": t.name,
                "status": mapped_status,
                "priority": mapped_priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "assignee_id": t.assigned_user_id,
                "team_id": None,
                "project_id": t.phase.project_id if t.phase_id else None,
                "project_name": (
                    t.phase.project.name if t.phase_id and t.phase.project_id else None
                ),
                "edit_url": f"/projects/tasks/{t.id}",
                "edit_in_app": "projects",
                "unmapped_source_status": t.status if unmapped else None,
            })
        return rows

    # ----- FollowUpTask ----------------------------------------------------

    def _followup_task_rows(self, request, org) -> list[dict]:
        try:
            from apps.crm.models import FollowUpTask
        except Exception:
            return []

        qs = FollowUpTask.objects.filter(lead__organization=org).select_related(
            "assigned_to", "rule", "lead"
        )
        qs = self._apply_overlay_filters(qs, request, assignee_field="assigned_to")

        rows: list[dict] = []
        for t in qs[:200]:
            mapped_status = FOLLOWUP_TASK_STATUS_MAP.get(t.status, "todo")
            unmapped = t.status not in FOLLOWUP_TASK_STATUS_MAP
            # Composite title: "Rule name — Lead name"
            rule_name = t.rule.name if t.rule_id else "Follow-up"
            lead_repr = self._lead_display(t.lead) if t.lead_id else ""
            title = f"{rule_name} — {lead_repr}" if lead_repr else rule_name
            rows.append({
                "source": "crm_follow_up",
                "id": t.id,
                "title": title,
                "status": mapped_status,
                "priority": "medium",  # FollowUpTask has no priority — default
                "due_date": t.due_at.date().isoformat() if t.due_at else None,
                "assignee_id": t.assigned_to_id,
                "team_id": None,
                "lead_id": t.lead_id,
                "lead_name": lead_repr,
                "edit_url": (
                    f"/crm/leads/{t.lead_id}" if t.lead_id else f"/crm/follow-ups/{t.id}"
                ),
                "edit_in_app": "crm",
                "unmapped_source_status": t.status if unmapped else None,
            })
        return rows

    # ----- helpers ---------------------------------------------------------

    @staticmethod
    def _apply_overlay_filters(qs, request, *, assignee_field: str):
        """Apply assignee=me/all + status/priority/overdue/due_before filters."""
        params = request.query_params
        assignee = params.get("assignee", "all")
        if assignee == "me":
            qs = qs.filter(**{assignee_field: request.user})

        due_before = params.get("due_before")
        if due_before:
            try:
                parsed = date_cls.fromisoformat(due_before)
                # ProjectTask uses due_date; FollowUpTask uses due_at.
                if hasattr(qs.model, "due_date"):
                    qs = qs.filter(due_date__lte=parsed)
                elif hasattr(qs.model, "due_at"):
                    qs = qs.filter(due_at__date__lte=parsed)
            except ValueError:
                pass

        overdue = params.get("overdue")
        if overdue and overdue.lower() in ("1", "true"):
            today = date_cls.today()
            if hasattr(qs.model, "due_date"):
                qs = qs.filter(due_date__lt=today).exclude(status="completed")
            elif hasattr(qs.model, "due_at"):
                qs = qs.filter(due_at__date__lt=today).exclude(status="completed")

        return qs

    @staticmethod
    def _lead_display(lead) -> str:
        # Lead has various display fields — pick the most defensible.
        for attr in ("name", "full_name", "display_name", "company_name"):
            value = getattr(lead, attr, None)
            if value:
                return str(value)
        return f"Lead #{lead.pk}"
