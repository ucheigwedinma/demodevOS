"""
Calendar API views.

See docs/workspace-calendar-design.md §7 + §8 for endpoint contract +
permissions.

Window-bounded list endpoint (`/events/?start=&end=`) returns occurrence-flat
results. Detail/edit/cancel/destroy work on the event row. Occurrence
overrides have their own POST/DELETE endpoints. Cursor pagination is used
only on the agenda endpoint.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone as dttz
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone as djtimezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, views, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CalendarEvent,
    CalendarEventAttendee,
    CalendarEventOccurrence,
    IcalFeedToken,
)
from .permissions import can_edit_event, can_view_event, event_role_for
from .recurrence import expand_with_overrides, is_orphan_override
from .serializers import (
    AttendeeAddSerializer,
    CalendarEventAttendeeSerializer,
    CalendarEventDetailSerializer,
    CalendarEventListSerializer,
    CalendarEventOccurrenceSerializer,
    CalendarEventWriteSerializer,
    OccurrenceUpsertSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

WINDOW_MAX_DAYS = 62  # per design §7
ICAL_FEED_CACHE_SECONDS = 300


def _request_org(request):
    return getattr(request, "organization", None) or _user_org(request.user)


def _user_org(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "organization", None) if profile else None


def _parse_window(request) -> tuple[datetime, datetime]:
    start_raw = request.query_params.get("start")
    end_raw = request.query_params.get("end")
    if not start_raw or not end_raw:
        raise ValidationError({"detail": "Both 'start' and 'end' query params are required."})
    start = parse_datetime(start_raw)
    end = parse_datetime(end_raw)
    if start is None or end is None:
        raise ValidationError({"detail": "start/end must be ISO 8601 datetimes."})
    if djtimezone.is_naive(start):
        start = djtimezone.make_aware(start, dttz.utc)
    if djtimezone.is_naive(end):
        end = djtimezone.make_aware(end, dttz.utc)
    if end < start:
        raise ValidationError({"detail": "end must be on or after start."})
    if (end - start).days > WINDOW_MAX_DAYS:
        raise ValidationError(
            {"detail": f"Window cannot exceed {WINDOW_MAX_DAYS} days."}
        )
    return start, end


def _visible_event_queryset(user, org):
    """
    Base queryset for events visible to `user` in `org`. Applies the §8
    rules at query time.
    """
    if user is None or not user.is_authenticated or org is None:
        return CalendarEvent.objects.none()

    qs = CalendarEvent.objects.filter(organization=org)

    # Build the OR clause: creator | attendee | org visibility | team
    # visibility (member of the team) | secret-team member-only override.
    # We approximate "user is on team" with Exists subquery on TeamMembership.
    from apps.workspace.models import TeamMembership

    user_team_ids = TeamMembership.objects.filter(user=user).values("team_id")

    visibility_clause = (
        Q(creator=user)
        | Q(attendees__user=user)
        | Q(visibility=CalendarEvent.Visibility.ORG)
        | Q(visibility=CalendarEvent.Visibility.TEAM, team__in=user_team_ids)
    )

    # Secret-team override: events with team__visibility=secret are excluded
    # unless the user is a member of that team. We add an exclusion clause
    # AFTER the OR to enforce this.
    qs = qs.filter(visibility_clause).distinct()
    qs = qs.exclude(
        Q(team__visibility="secret") & ~Q(team__in=user_team_ids)
    )
    return qs


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class AgendaCursorPagination(CursorPagination):
    page_size = 25
    ordering = "starts_at"


# ---------------------------------------------------------------------------
# Event viewset
# ---------------------------------------------------------------------------


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CalendarEventWriteSerializer
        if self.action == "retrieve":
            return CalendarEventDetailSerializer
        return CalendarEventListSerializer

    def get_queryset(self):
        request = self.request
        org = _request_org(request)
        return _visible_event_queryset(request.user, org)

    # ----- list (window-bounded, occurrence-flat) -------------------------

    def list(self, request, *args, **kwargs):
        start, end = _parse_window(request)
        org = _request_org(request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        qs = self.get_queryset().filter(is_cancelled=False)

        # Optional filters
        team = request.query_params.get("team")
        if team:
            qs = qs.filter(team_id=team)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(title__icontains=q)

        # Time prefilter: we want events whose [starts_at, ends_at] (or RRULE)
        # could intersect the window. For non-recurring: starts_at <= end AND
        # (ends_at >= start OR ends_at IS NULL). For recurring: the rule may
        # span the window even if its starts_at is in the past — so include
        # events whose recurrence_end is null or >= start.
        time_clause = Q(recurrence_rule="") & Q(starts_at__lte=end) & (
            Q(ends_at__gte=start) | Q(ends_at__isnull=True)
        )
        recurring_clause = ~Q(recurrence_rule="") & (
            Q(starts_at__lte=end)
            & (Q(recurrence_end__gte=start) | Q(recurrence_end__isnull=True))
        )
        qs = qs.filter(time_clause | recurring_clause)
        qs = qs.select_related("creator", "team").prefetch_related(
            Prefetch(
                "occurrences",
                queryset=CalendarEventOccurrence.objects.all(),
                to_attr="_prefetched_overrides",
            )
        )

        # Expand each event into occurrence dicts.
        results = []
        for event in qs:
            occurrences = expand_with_overrides(event, start, end)
            base = {
                "event_id": event.pk,
                "title": event.title,
                "kind": event.kind,
                "visibility": event.visibility,
                "creator_id": event.creator_id,
                "team_id": event.team_id,
                "all_day": event.all_day,
                "timezone": event.timezone,
                "is_recurring": bool(event.recurrence_rule),
            }
            role = event_role_for(request.user, event)
            for occ in occurrences:
                results.append(
                    {
                        **base,
                        "original_start": occ.original_start,
                        "starts_at": occ.starts_at,
                        "ends_at": occ.ends_at,
                        "is_override": occ.is_override,
                        "is_cancelled": occ.is_cancelled,
                        "my_role": role,
                    }
                )
        results.sort(key=lambda r: r["starts_at"])
        return Response({"results": results})

    # ----- agenda (cursor-paginated) -------------------------------------

    def agenda(self, request, *args, **kwargs):
        """
        Cursor-paginated upcoming events. Returns event rows (not occurrence
        rows). Frontend Agenda view can either render one row per event or
        expand client-side.
        """
        qs = self.get_queryset().filter(
            is_cancelled=False, starts_at__gte=djtimezone.now() - timedelta(days=1)
        ).order_by("starts_at")
        paginator = AgendaCursorPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        ser = CalendarEventListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(ser.data)

    # ----- create ---------------------------------------------------------

    def perform_create(self, serializer):
        org = _request_org(self.request)
        if org is None:
            raise PermissionDenied("Organization not resolved.")
        recurrence_end = self._compute_recurrence_end(serializer.validated_data)
        event = serializer.save(
            organization=org,
            creator=self.request.user,
            recurrence_end=recurrence_end,
        )
        self.created_event = event

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        out = CalendarEventDetailSerializer(self.created_event, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ----- partial_update -------------------------------------------------

    def partial_update(self, request, *args, **kwargs):
        event = self.get_object()
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can edit this event.")
        ser = self.get_serializer(event, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        # Recompute recurrence_end if rule changed.
        if "recurrence_rule" in ser.validated_data:
            ser.validated_data["recurrence_end"] = self._compute_recurrence_end(
                {**ser.validated_data, "starts_at": event.starts_at}
            )
        with transaction.atomic():
            ser.save()
        event.refresh_from_db()
        out = CalendarEventDetailSerializer(event, context={"request": request})
        return Response(out.data)

    # ----- retrieve -------------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        event = self.get_object()
        if not can_view_event(request.user, event):
            raise NotFound()  # never reveal existence
        ser = self.get_serializer(event)
        return Response(ser.data)

    # ----- destroy --------------------------------------------------------

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can delete this event.")
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ----- cancel ---------------------------------------------------------

    def cancel(self, request, pk=None):
        event = self.get_object()
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can cancel this event.")
        event.is_cancelled = True
        event.save(update_fields=["is_cancelled", "updated_at"])
        return Response(CalendarEventDetailSerializer(event, context={"request": request}).data)

    # ----- helpers --------------------------------------------------------

    @staticmethod
    def _compute_recurrence_end(data: dict) -> Optional[datetime]:
        """
        Derive recurrence_end from RRULE UNTIL/COUNT when present. Returns
        None for open-ended rules.
        """
        rule = data.get("recurrence_rule") or ""
        if not rule:
            return None
        from dateutil.rrule import rrulestr

        anchor = data.get("starts_at")
        try:
            r = rrulestr(rule, dtstart=anchor)
        except Exception:
            return None
        # If UNTIL is set, dateutil exposes _until; for COUNT, we compute the
        # last occurrence (bounded — won't loop forever because count is set).
        until = getattr(r, "_until", None)
        if until is not None:
            return until.astimezone(dttz.utc) if djtimezone.is_aware(until) else until
        count = getattr(r, "_count", None)
        if count is not None:
            try:
                last = list(r)[-1]
                return last.astimezone(dttz.utc) if djtimezone.is_aware(last) else last
            except Exception:
                return None
        return None


# ---------------------------------------------------------------------------
# Occurrence override view
# ---------------------------------------------------------------------------


class OccurrenceView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_event(self, request, event_id) -> CalendarEvent:
        org = _request_org(request)
        try:
            event = CalendarEvent.objects.get(pk=event_id, organization=org)
        except CalendarEvent.DoesNotExist:
            raise NotFound()
        if not can_view_event(request.user, event):
            raise NotFound()
        return event

    def upsert(self, request, event_id=None):
        """POST /events/{id}/occurrences/ — create or update an override."""
        event = self._get_event(request, event_id)
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can manage overrides.")
        ser = OccurrenceUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        original_start = data["original_start"]
        defaults = {
            "is_cancelled": data.get("is_cancelled", False),
            "starts_at": data.get("starts_at"),
            "ends_at": data.get("ends_at"),
            "title": data.get("title", ""),
            "location": data.get("location", ""),
            "description": data.get("description", ""),
        }
        with transaction.atomic():
            override, _created = CalendarEventOccurrence.objects.update_or_create(
                event=event,
                original_start=original_start,
                defaults=defaults,
            )
        return Response(CalendarEventOccurrenceSerializer(override).data)

    def destroy(self, request, event_id=None, original_start=None):
        """DELETE /events/{id}/occurrences/{original_start}/ — mark cancelled."""
        event = self._get_event(request, event_id)
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can manage overrides.")
        if original_start is None:
            raise ValidationError({"original_start": "Missing original_start."})
        parsed = parse_datetime(original_start)
        if parsed is None:
            raise ValidationError({"original_start": "Must be ISO 8601."})
        with transaction.atomic():
            override, _created = CalendarEventOccurrence.objects.update_or_create(
                event=event,
                original_start=parsed,
                defaults={"is_cancelled": True},
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Attendee view
# ---------------------------------------------------------------------------


class AttendeeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_event(self, request, event_id) -> CalendarEvent:
        org = _request_org(request)
        try:
            event = CalendarEvent.objects.get(pk=event_id, organization=org)
        except CalendarEvent.DoesNotExist:
            raise NotFound()
        if not can_view_event(request.user, event):
            raise NotFound()
        return event

    def list(self, request, event_id=None):
        event = self._get_event(request, event_id)
        attendees = (
            CalendarEventAttendee.objects.filter(event=event)
            .select_related("user")
            .order_by("user__first_name", "user__last_name")
        )
        return Response(CalendarEventAttendeeSerializer(attendees, many=True).data)

    def create(self, request, event_id=None):
        event = self._get_event(request, event_id)
        if not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can add attendees.")
        ser = AttendeeAddSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = ser.validated_data["user_id"]
        target = User.objects.filter(
            pk=user_id, profile__organization=event.organization, is_active=True
        ).first()
        if target is None:
            raise ValidationError({"user_id": "User not found in this organization."})
        attendee, _created = CalendarEventAttendee.objects.get_or_create(
            event=event, user=target, defaults={"invited_by": request.user}
        )
        return Response(CalendarEventAttendeeSerializer(attendee).data)

    def destroy(self, request, event_id=None, user_id=None):
        event = self._get_event(request, event_id)
        try:
            attendee = CalendarEventAttendee.objects.get(event=event, user_id=user_id)
        except CalendarEventAttendee.DoesNotExist:
            raise NotFound()
        # Self-remove always allowed; otherwise creator-only.
        is_self = attendee.user_id == request.user.id
        if not is_self and not can_edit_event(request.user, event):
            raise PermissionDenied("Only the creator can remove other attendees.")
        attendee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Meetings overlay view
# ---------------------------------------------------------------------------


class MeetingsOverlayView(views.APIView):
    """
    GET /api/calendar/meetings-overlay/?start=&end=&team=

    Read-only overlay of apps.meetings.Meeting rows in the request window.
    Inherits apps.meetings's org scoping — we just hit its model directly
    with the request's org as the filter.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_window(request)
        org = _request_org(request)
        if org is None:
            return Response({"results": []})

        try:
            from apps.meetings.models import Meeting
        except Exception:
            return Response({"results": []})

        qs = Meeting.objects.filter(
            organization=org,
            scheduled_start__lte=end,
        ).filter(
            Q(scheduled_end__gte=start) | Q(scheduled_end__isnull=True)
        ).select_related("project")

        team_id = request.query_params.get("team")
        if team_id:
            # Meeting has no team_id; this filter is a no-op for now but
            # documented for forward-compat when meetings get teams.
            pass

        results = []
        for m in qs:
            results.append(
                {
                    "source": "meeting",
                    "id": m.pk,
                    "title": m.title,
                    "kind": "meeting",
                    "starts_at": m.scheduled_start,
                    "ends_at": m.scheduled_end,
                    "timezone": "UTC",  # apps.meetings doesn't track TZ at row level
                    "location": m.location or "",
                    "meeting_link": m.meeting_link or "",
                    "meeting_type": m.meeting_type,
                    "status": m.status,
                    "project_id": m.project_id,
                    "project_name": m.project.name if m.project_id and m.project else None,
                    "edit_url": f"/meetings/{m.pk}",
                    "edit_in_app": "meetings",
                }
            )
        return Response({"results": results})


# ---------------------------------------------------------------------------
# iCal feed + rotation
# ---------------------------------------------------------------------------


class CalendarFeedView(views.APIView):
    """GET /api/calendar/feed/?token=… — public-but-token-protected feed."""

    permission_classes = []  # token IS the auth
    authentication_classes = []

    def get(self, request):
        raw_token = request.query_params.get("token", "").strip()
        if not raw_token:
            return HttpResponse("", status=404)
        token_hash = IcalFeedToken.hash_token(raw_token)
        token_row = IcalFeedToken.objects.filter(
            token_hash=token_hash, revoked_at__isnull=True
        ).select_related("user").first()
        if token_row is None:
            return HttpResponse("", status=404)

        cache_key = f"calendar.ical_feed.v:{token_row.user_id}"
        cache_data_key = f"calendar.ical_feed.body:{token_row.user_id}"
        version = cache.get(cache_key)
        cached_body = cache.get(cache_data_key) if version else None
        if cached_body is not None:
            return HttpResponse(cached_body, content_type="text/calendar")

        from .ical_export import build_user_feed

        body = build_user_feed(token_row.user)
        cache.set(cache_key, "v1", ICAL_FEED_CACHE_SECONDS)
        cache.set(cache_data_key, body, ICAL_FEED_CACHE_SECONDS)
        return HttpResponse(body, content_type="text/calendar")


class RotateFeedTokenView(views.APIView):
    """POST /api/calendar/feed/rotate-token/ — revoke old, mint new, return raw."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            IcalFeedToken.objects.filter(
                user=request.user, revoked_at__isnull=True
            ).update(revoked_at=djtimezone.now())
            raw = IcalFeedToken.generate_raw_token()
            IcalFeedToken.objects.create(
                user=request.user, token_hash=IcalFeedToken.hash_token(raw)
            )
        # Bust feed cache
        cache.delete(f"calendar.ical_feed.body:{request.user.id}")
        return Response({"token": raw, "feed_url_path": f"/api/calendar/feed/?token={raw}"})
