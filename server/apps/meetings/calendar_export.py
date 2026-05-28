"""
Calendar export helpers — generate iCal (.ics) events from meetings.

Usage in views:
    from apps.meetings.calendar_export import meeting_to_ical
    ical_str = meeting_to_ical(meeting)
    return HttpResponse(ical_str, content_type="text/calendar")
"""

from datetime import timedelta


def meeting_to_ical(meeting) -> str:
    """Generate an iCal (.ics) string for a single meeting."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//developerOS//Meeting//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
    ]

    # UID
    lines.append(f"UID:{meeting.meeting_number}@developeros.app")

    # Timestamps
    if meeting.scheduled_start:
        lines.append(f"DTSTART:{_ical_dt(meeting.scheduled_start)}")
    if meeting.scheduled_end:
        lines.append(f"DTEND:{_ical_dt(meeting.scheduled_end)}")
    elif meeting.scheduled_start and meeting.duration_mins:
        end = meeting.scheduled_start + timedelta(minutes=meeting.duration_mins)
        lines.append(f"DTEND:{_ical_dt(end)}")

    lines.append(f"DTSTAMP:{_ical_dt(meeting.created_at)}")

    # Summary & Description
    lines.append(f"SUMMARY:{_ical_escape(meeting.title)}")

    desc_parts = []
    if meeting.series_name:
        desc_parts.append(f"Series: {meeting.series_name}")
    if meeting.meeting_type:
        desc_parts.append(f"Type: {meeting.get_meeting_type_display()}")
    if meeting.project:
        desc_parts.append(f"Project: {meeting.project.name}")
    if meeting.notes:
        desc_parts.append(f"Notes: {meeting.notes}")
    if desc_parts:
        lines.append(f"DESCRIPTION:{_ical_escape(chr(10).join(desc_parts))}")

    # Location
    if meeting.location:
        lines.append(f"LOCATION:{_ical_escape(meeting.location)}")
    elif meeting.meeting_link:
        lines.append(f"LOCATION:{meeting.meeting_link}")

    # Organizer
    if meeting.organized_by and meeting.organized_by.email:
        lines.append(f"ORGANIZER;CN={_ical_escape(meeting.organized_by.get_full_name())}:mailto:{meeting.organized_by.email}")

    # Attendees
    for attendee in meeting.attendees.all():
        if attendee.email:
            cn = _ical_escape(attendee.name)
            lines.append(f"ATTENDEE;CN={cn};RSVP=TRUE:mailto:{attendee.email}")

    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def _ical_dt(dt) -> str:
    """Format a datetime as iCal UTC timestamp."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _ical_escape(text: str) -> str:
    """Escape special characters for iCal."""
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
