from datetime import date, timedelta

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.permissions import HasRolePermission

from .calendar_export import meeting_to_ical
from .minutes_generator import (
    auto_generate_minutes,
    generate_minutes_from_form,
    generate_minutes_from_notes,
)
from .models import Meeting, MeetingActionItem, MeetingAttendee, MeetingTemplate
from .serializers import (
    MeetingActionItemSerializer,
    MeetingAttendeeSerializer,
    MeetingDetailSerializer,
    MeetingListSerializer,
    MeetingTemplateSerializer,
    MeetingWriteSerializer,
)

_ACTION_MAP = {
    "list": "view", "retrieve": "view",
    "create": "create", "update": "edit", "partial_update": "edit",
    "destroy": "delete",
}


class MeetingTemplateViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.system_preferences"
    rbac_action_map = _ACTION_MAP
    serializer_class = MeetingTemplateSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["frequency", "is_active"]
    ordering = ["name"]

    def get_queryset(self):
        return MeetingTemplate.objects.filter(organization=self._resolve_request_org())

    def perform_create(self, serializer):
        serializer.save(organization=self._resolve_request_org())


class MeetingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _ACTION_MAP
    search_fields = ["meeting_number", "title", "series_name", "location", "recorded_by"]
    filterset_fields = ["project", "meeting_type", "status", "template", "series_name"]
    ordering_fields = ["scheduled_start", "created_at", "status", "meeting_type"]
    ordering = ["-scheduled_start"]

    def get_serializer_class(self):
        if self.action == "list":
            return MeetingListSerializer
        if self.action in ("create", "update", "partial_update"):
            return MeetingWriteSerializer
        return MeetingDetailSerializer

    def get_queryset(self):
        return (
            Meeting.objects.filter(organization=self._resolve_request_org())
            .select_related("project", "template", "organized_by", "created_by", "consultant")
            .prefetch_related("attendees", "action_items")
            .annotate(
                attendee_count=Count("attendees", distinct=True),
                action_item_count=Count("action_items", distinct=True),
                open_action_count=Count(
                    "action_items",
                    filter=Q(action_items__status__in=["open", "in_progress", "overdue"]),
                    distinct=True,
                ),
            )
        )

    def perform_create(self, serializer):
        meeting = serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user,
            organized_by=self.request.user,
        )
        # Auto-populate attendees from template
        if meeting.template and meeting.template.default_attendee_roles:
            for role in meeting.template.default_attendee_roles:
                MeetingAttendee.objects.get_or_create(
                    meeting=meeting,
                    role=role,
                    defaults={"name": role, "email": ""},
                )
        # Auto-populate agenda from template
        if meeting.template and meeting.template.default_agenda and not meeting.agenda:
            meeting.agenda = meeting.template.default_agenda
            meeting.save(update_fields=["agenda"])

    @action(detail=True, methods=["post"], url_path="generate-minutes")
    def generate_minutes_action(self, request, pk=None):
        """Manually trigger minutes generation.

        Accepts optional `source` param:
          - "ai_from_notes" — force AI generation from live notes
          - "from_form" — force structured form generation
          - omit — auto-detect best approach
        """
        meeting = self.get_object()
        source_hint = request.data.get("source", "")

        try:
            if source_hint == "ai_from_notes":
                text = generate_minutes_from_notes(meeting)
                source = "ai_from_notes"
            elif source_hint == "from_form":
                text = generate_minutes_from_form(meeting)
                source = "ai_from_form"
            else:
                text, source = auto_generate_minutes(meeting)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        meeting.minutes_text = text
        meeting.minutes_source = source
        meeting.minutes_generated_at = timezone.now()
        meeting.save(update_fields=["minutes_text", "minutes_source", "minutes_generated_at", "updated_at"])
        return Response({
            "detail": "Minutes generated.",
            "source": source,
            "minutes_text": text,
        })

    @action(detail=True, methods=["post"], url_path="approve-minutes")
    def approve_minutes(self, request, pk=None):
        """Approve the meeting minutes."""
        meeting = self.get_object()
        if not meeting.minutes_text:
            return Response({"detail": "No minutes to approve."}, status=status.HTTP_400_BAD_REQUEST)
        meeting.minutes_approved = True
        meeting.minutes_approved_by = request.data.get(
            "approved_by", request.user.get_full_name() or request.user.username,
        )
        meeting.minutes_approved_at = timezone.now()
        meeting.save(update_fields=["minutes_approved", "minutes_approved_by", "minutes_approved_at", "updated_at"])
        return Response({"detail": "Minutes approved."})

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_meeting(self, request, pk=None):
        """Mark meeting as completed — triggers auto-generation of minutes."""
        meeting = self.get_object()
        meeting.status = "completed"
        meeting.actual_end = timezone.now()
        if not meeting.actual_start:
            meeting.actual_start = meeting.scheduled_start
        meeting.save()  # pre_save signal will auto-generate minutes
        return Response({"detail": "Meeting completed.", "minutes_generated": bool(meeting.minutes_text)})

    @action(detail=True, methods=["get"], url_path="export-ical")
    def export_ical(self, request, pk=None):
        """Export meeting as .ics calendar file."""
        meeting = self.get_object()
        ical_str = meeting_to_ical(meeting)
        response = HttpResponse(ical_str, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{meeting.meeting_number}.ics"'
        return response

    @action(detail=False, methods=["get"])
    def summary(self, request):
        org = self._resolve_request_org()
        today = date.today()
        qs = Meeting.objects.filter(organization=org)
        upcoming = qs.filter(status="scheduled", scheduled_start__gte=timezone.now())
        return Response({
            "total": qs.count(),
            "scheduled": qs.filter(status="scheduled").count(),
            "completed": qs.filter(status="completed").count(),
            "upcoming_7d": upcoming.filter(scheduled_start__lte=timezone.now() + timedelta(days=7)).count(),
            "upcoming_30d": upcoming.filter(scheduled_start__lte=timezone.now() + timedelta(days=30)).count(),
            "open_action_items": MeetingActionItem.objects.filter(
                meeting__organization=org, status__in=["open", "in_progress", "overdue"],
            ).count(),
            "overdue_action_items": MeetingActionItem.objects.filter(
                meeting__organization=org, status="overdue",
            ).count(),
        })

    @action(detail=False, methods=["post"], url_path="create-from-template")
    def create_from_template(self, request):
        """Create a meeting pre-populated from a template."""
        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"detail": "template_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        org = self._resolve_request_org()
        try:
            template = MeetingTemplate.objects.get(pk=template_id, organization=org)
        except MeetingTemplate.DoesNotExist:
            return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)

        scheduled_start = request.data.get("scheduled_start")
        if not scheduled_start:
            return Response({"detail": "scheduled_start is required."}, status=status.HTTP_400_BAD_REQUEST)

        meeting = Meeting.objects.create(
            organization=org,
            template=template,
            title=request.data.get("title", template.name),
            meeting_type=request.data.get("meeting_type", "other"),
            series_name=template.name,
            scheduled_start=scheduled_start,
            duration_mins=template.default_duration_mins,
            location=template.default_location,
            agenda=template.default_agenda,
            project_id=request.data.get("project"),
            created_by=request.user,
            organized_by=request.user,
        )

        # Auto-add default attendees
        for role in (template.default_attendee_roles or []):
            MeetingAttendee.objects.create(
                meeting=meeting, name=role, role=role,
            )

        return Response(MeetingDetailSerializer(meeting).data, status=status.HTTP_201_CREATED)


class MeetingAttendeeViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /meetings/<pk>/attendees/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _ACTION_MAP
    serializer_class = MeetingAttendeeSerializer
    ordering = ["name"]

    def get_queryset(self):
        return MeetingAttendee.objects.filter(meeting_id=self.kwargs.get("meeting_pk"))

    def perform_create(self, serializer):
        serializer.save(meeting_id=self.kwargs["meeting_pk"])


class MeetingActionItemViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Nested under /meetings/<pk>/action-items/"""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    rbac_action_map = _ACTION_MAP
    serializer_class = MeetingActionItemSerializer
    search_fields = ["description", "assigned_to"]
    filterset_fields = ["status", "priority"]
    ordering = ["sort_order", "due_date"]

    def get_queryset(self):
        return MeetingActionItem.objects.filter(meeting_id=self.kwargs.get("meeting_pk"))

    def perform_create(self, serializer):
        serializer.save(meeting_id=self.kwargs["meeting_pk"])

    @action(detail=True, methods=["post"], url_path="extract-to-task")
    def extract_to_task(self, request, meeting_pk=None, pk=None):
        """Convert this action item into a ProjectTask."""
        ai = self.get_object()
        meeting = ai.meeting
        if not meeting.project:
            return Response(
                {"detail": "Meeting has no linked project — cannot create task."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.projects.models import ProjectTask
        task = ProjectTask.objects.create(
            organization=meeting.organization,
            project=meeting.project,
            name=ai.description[:255],
            description=f"Extracted from meeting {meeting.meeting_number}: {ai.description}",
            assigned_to=ai.assigned_to,
            due_date=ai.due_date,
            status="pending",
        )
        ai.linked_task = task
        ai.save(update_fields=["linked_task"])

        return Response({
            "detail": "Task created from action item.",
            "task_id": task.pk,
            "task_name": task.name,
        })
