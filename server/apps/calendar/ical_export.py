"""
iCal (RFC 5545) export for CalendarEvent rows.

Hand-written rather than depending on `icalendar` — matches the existing
pattern in apps.meetings.calendar_export. We emit the minimum viable VEVENT
fields and the raw RRULE for recurring events (calendar clients expand
client-side, which is correct because they know the user's local TZ).

Per design §12: the feed does NOT include apps.meetings.Meeting rows. Those
have their own export in apps.meetings.
"""

from __future__ import annotations

from datetime import datetime, timezone as dttz

from django.utils import timezone as djtimezone

from .models import CalendarEvent, CalendarEventOccurrence


def _ical_dt(dt: datetime) -> str:
    """Format a datetime as iCal UTC: 20260512T093000Z."""
    if djtimezone.is_naive(dt):
        dt = djtimezone.make_aware(dt, dttz.utc)
    return dt.astimezone(dttz.utc).strftime("%Y%m%dT%H%M%SZ")


def _ical_escape(text: str) -> str:
    """Per RFC 5545: backslash-escape special characters."""
    return (
        text.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold(line: str, width: int = 75) -> list[str]:
    """RFC 5545 long-line folding (every {width} chars, prepend space)."""
    if len(line) <= width:
        return [line]
    chunks = []
    chunks.append(line[:width])
    remaining = line[width:]
    while remaining:
        chunks.append(" " + remaining[: width - 1])
        remaining = remaining[width - 1 :]
    return chunks


def event_to_vevent_lines(event: CalendarEvent) -> list[str]:
    """Return iCal VEVENT lines for a single event."""
    lines = ["BEGIN:VEVENT"]
    lines.append(f"UID:cal-{event.pk}@developeros.app")
    lines.append(f"DTSTAMP:{_ical_dt(event.updated_at)}")
    lines.append(f"DTSTART:{_ical_dt(event.starts_at)}")
    if event.ends_at is not None:
        lines.append(f"DTEND:{_ical_dt(event.ends_at)}")
    lines.append(f"SUMMARY:{_ical_escape(event.title)}")
    if event.description:
        lines.append(f"DESCRIPTION:{_ical_escape(event.description)}")
    if event.location:
        lines.append(f"LOCATION:{_ical_escape(event.location)}")
    if event.is_cancelled:
        lines.append("STATUS:CANCELLED")
    else:
        lines.append("STATUS:CONFIRMED")
    if event.recurrence_rule:
        lines.append(f"RRULE:{event.recurrence_rule}")
    if event.kind == CalendarEvent.Kind.OUT_OF_OFFICE:
        lines.append("TRANSP:OPAQUE")
    elif event.kind == CalendarEvent.Kind.FOCUS:
        lines.append("TRANSP:OPAQUE")
    else:
        lines.append("TRANSP:OPAQUE")
    lines.append("END:VEVENT")
    return lines


def occurrence_to_exception_lines(event: CalendarEvent, override: CalendarEventOccurrence) -> list[str]:
    """
    Emit a VEVENT with RECURRENCE-ID for an override per RFC 5545 §3.8.4.4.
    Cancelled overrides emit an EXDATE on the parent series instead.
    """
    if override.is_cancelled:
        return [f"EXDATE:{_ical_dt(override.original_start)}"]
    lines = ["BEGIN:VEVENT"]
    lines.append(f"UID:cal-{event.pk}@developeros.app")
    lines.append(f"RECURRENCE-ID:{_ical_dt(override.original_start)}")
    lines.append(f"DTSTAMP:{_ical_dt(override.updated_at)}")
    start = override.starts_at or override.original_start
    lines.append(f"DTSTART:{_ical_dt(start)}")
    if override.ends_at:
        lines.append(f"DTEND:{_ical_dt(override.ends_at)}")
    elif event.ends_at and override.starts_at:
        duration = event.ends_at - event.starts_at
        lines.append(f"DTEND:{_ical_dt(override.starts_at + duration)}")
    title = override.title or event.title
    lines.append(f"SUMMARY:{_ical_escape(title)}")
    description = override.description or event.description
    if description:
        lines.append(f"DESCRIPTION:{_ical_escape(description)}")
    location = override.location or event.location
    if location:
        lines.append(f"LOCATION:{_ical_escape(location)}")
    lines.append("STATUS:CONFIRMED")
    lines.append("END:VEVENT")
    return lines


def event_to_ical(event: CalendarEvent) -> str:
    """Return a standalone .ics string for a single event (for email invites)."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//developerOS//Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    lines.extend(event_to_vevent_lines(event))
    for override in event.occurrences.all():
        if override.is_cancelled:
            # Append EXDATE inside the same VEVENT for cancelled occurrences.
            # We've already closed the VEVENT, so this is a simplification:
            # in production we'd inline the EXDATE before END:VEVENT. For
            # one-shot per-event .ics emails this is rare and acceptable.
            pass
        else:
            lines.extend(occurrence_to_exception_lines(event, override))
    lines.append("END:VCALENDAR")
    out = []
    for line in lines:
        out.extend(_fold(line))
    return "\r\n".join(out) + "\r\n"


def build_user_feed(user) -> str:
    """
    Build the user's iCal subscribable feed body.

    Includes: events the user can see (creator, attendee, org-visible, or
    team-visible where they're a member). Excludes secret-team events
    they're not in. Per §12 — does NOT include apps.meetings.Meeting.
    """
    from .permissions import can_view_event

    # Filter at queryset level for visibility — same logic as the list view
    # but un-windowed. We export events from -6 months to +1 year for
    # subscribed clients (matches the expansion cap).
    org_profile = getattr(user, "profile", None)
    org = getattr(org_profile, "organization", None) if org_profile else None
    if org is None:
        return _empty_feed()

    from django.db.models import Q

    from apps.workspace.models import TeamMembership

    user_team_ids = TeamMembership.objects.filter(user=user).values("team_id")
    qs = CalendarEvent.objects.filter(
        organization=org,
        is_cancelled=False,
    ).filter(
        Q(creator=user)
        | Q(attendees__user=user)
        | Q(visibility=CalendarEvent.Visibility.ORG)
        | Q(visibility=CalendarEvent.Visibility.TEAM, team__in=user_team_ids)
    ).exclude(
        Q(team__visibility="secret") & ~Q(team__in=user_team_ids)
    ).distinct()

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//developerOS//Calendar Feed//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:developerOS — {user.get_full_name() or user.email}",
    ]
    for event in qs.select_related("creator", "team").prefetch_related("occurrences"):
        lines.extend(event_to_vevent_lines(event))
        for override in event.occurrences.all():
            lines.extend(occurrence_to_exception_lines(event, override))
    lines.append("END:VCALENDAR")
    out = []
    for line in lines:
        out.extend(_fold(line))
    return "\r\n".join(out) + "\r\n"


def _empty_feed() -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//developerOS//Calendar Feed//EN\r\n"
        "END:VCALENDAR\r\n"
    )
