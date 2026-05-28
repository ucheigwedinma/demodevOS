"""
RRULE expansion service.

Expands an RFC 5545 RRULE string into concrete occurrence times for a query
window. Uses python-dateutil for the heavy lifting and zoneinfo (stdlib)
for DST-aware timezone math.

Key behaviors:
- Expansion is performed in the event's IANA timezone, then results are
  converted to UTC datetimes for storage and API responses. This is the
  standard pattern for calendar systems and is correct across DST.
- The expansion window is hard-capped at 1 year forward / 6 months back
  from "now" (per design EC12). The cap protects against pathological
  rules like `FREQ=YEARLY` with no UNTIL/COUNT.
- Per-occurrence overrides (`CalendarEventOccurrence`) are applied on top
  of the raw expansion: cancelled occurrences are dropped, modified
  times are substituted.
- An override is "orphaned" when its `original_start` no longer matches
  any RRULE-produced occurrence (e.g. the caller shortened the rule).
  We detect this by comparing against the expanded set within a wider
  window and surface the flag in the API response so the UI can offer
  cleanup.

See docs/workspace-calendar-design.md §6 + §15.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dttz
from typing import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.rrule import rrulestr
from django.utils import timezone as djtimezone


# ---------------------------------------------------------------------------
# Hard caps + helpers
# ---------------------------------------------------------------------------


WINDOW_CAP_FORWARD = timedelta(days=365)
WINDOW_CAP_BACKWARD = timedelta(days=183)  # ~6 months


def _safe_tz(name: str) -> ZoneInfo:
    """Return a ZoneInfo, falling back to UTC on garbage input."""
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _cap_window(start, end):
    """Clamp the (start, end) window so we never expand more than the cap.

    Returns the clamped (start, end) and a flag indicating whether the
    caller's window was modified.
    """
    now = djtimezone.now()
    earliest = now - WINDOW_CAP_BACKWARD
    latest = now + WINDOW_CAP_FORWARD
    capped_start = max(start, earliest) if start is not None else earliest
    capped_end = min(end, latest) if end is not None else latest
    return capped_start, capped_end


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Occurrence:
    """One concrete occurrence in the calendar window."""

    event_id: int
    original_start: datetime  # the UTC instant the RRULE produced
    starts_at: datetime       # may differ from original if override; UTC
    ends_at: datetime | None  # UTC; None when kind=reminder (no duration)
    is_override: bool
    is_cancelled: bool


# ---------------------------------------------------------------------------
# Core expansion
# ---------------------------------------------------------------------------


def _build_rrule(event, tz: ZoneInfo):
    """
    Compile the event's RRULE in the event's timezone. We anchor it at the
    event's `starts_at` converted to that TZ (RRULE library uses dtstart
    as the seed for BYDAY/BYHOUR derivations when those aren't explicitly
    set).
    """
    if not event.recurrence_rule:
        return None
    # Anchor the rule at the localized starts_at. The library will use this
    # as DTSTART and respect DST through zoneinfo.
    dtstart_local = event.starts_at.astimezone(tz)
    return rrulestr(event.recurrence_rule, dtstart=dtstart_local)


def expand_raw(event, window_start: datetime, window_end: datetime) -> list[datetime]:
    """
    Return the list of original_start datetimes (UTC) the RRULE produces
    within [window_start, window_end]. Caller is responsible for
    applying overrides and converting to Occurrence shape.

    For non-recurring events, returns either [starts_at] if it falls in
    the window, or [].

    All times in/out are UTC `datetime` instances.
    """
    if window_start is None or window_end is None:
        raise ValueError("window_start and window_end are required")
    if window_end < window_start:
        return []

    # Hard cap
    window_start, window_end = _cap_window(window_start, window_end)

    tz = _safe_tz(event.timezone)
    duration = None
    if event.ends_at is not None:
        duration = event.ends_at - event.starts_at

    if not event.recurrence_rule:
        if window_start <= event.starts_at <= window_end:
            return [event.starts_at]
        return []

    rule = _build_rrule(event, tz)
    if rule is None:
        return []

    # rrule.between() works in the rule's tz; localize the window bounds.
    local_start = window_start.astimezone(tz)
    local_end = window_end.astimezone(tz)

    # Use inc=True so the boundary instants are included.
    local_occurrences = list(rule.between(local_start, local_end, inc=True))

    # Convert back to UTC for storage/transport.
    return [occ.astimezone(dttz.utc) for occ in local_occurrences]


def expand_with_overrides(event, window_start: datetime, window_end: datetime) -> list[Occurrence]:
    """
    Expand `event` into Occurrence rows within [window_start, window_end],
    applying CalendarEventOccurrence overrides.

    - Cancelled overrides drop the occurrence entirely.
    - Time-shifted overrides substitute starts_at/ends_at.
    - Out-of-window override shifts still surface ONLY if the shifted time
      falls inside [window_start, window_end] (Google Calendar behavior).
    """
    raw_originals = expand_raw(event, window_start, window_end)
    duration = None
    if event.ends_at is not None:
        duration = event.ends_at - event.starts_at

    # Index overrides by original_start (UTC); fetch lazily to allow this
    # function to operate on prefetched overrides if the caller provided them.
    overrides_by_original = _index_overrides(event)

    result: list[Occurrence] = []

    # Pass 1: walk RRULE-produced originals; apply overrides if present.
    seen_originals: set[datetime] = set()
    for original in raw_originals:
        seen_originals.add(original)
        override = overrides_by_original.get(original)
        if override is None:
            ends = (original + duration) if duration is not None else None
            result.append(
                Occurrence(
                    event_id=event.pk,
                    original_start=original,
                    starts_at=original,
                    ends_at=ends,
                    is_override=False,
                    is_cancelled=False,
                )
            )
            continue
        if override.is_cancelled:
            # Skip cancelled occurrences.
            continue
        starts_at = override.starts_at or original
        if override.ends_at:
            ends = override.ends_at
        elif override.starts_at and duration is not None:
            ends = override.starts_at + duration
        elif duration is not None:
            ends = original + duration
        else:
            ends = None
        # Override is in-window only if the *shifted* time still falls in.
        if not (window_start <= starts_at <= window_end):
            continue
        result.append(
            Occurrence(
                event_id=event.pk,
                original_start=original,
                starts_at=starts_at,
                ends_at=ends,
                is_override=True,
                is_cancelled=False,
            )
        )

    # Pass 2: catch overrides whose *original_start* is OUTSIDE the window
    # but whose *shifted starts_at* lands inside it. This is rare but
    # important — if you moved a Monday standup to next Friday, and the
    # window covers next Friday, we should return it.
    for original, override in overrides_by_original.items():
        if original in seen_originals:
            continue
        if override.is_cancelled:
            continue
        if override.starts_at is None:
            continue  # not a time-shift; nothing to surface
        if not (window_start <= override.starts_at <= window_end):
            continue
        # Compute ends similarly.
        if override.ends_at:
            ends = override.ends_at
        elif duration is not None:
            ends = override.starts_at + duration
        else:
            ends = None
        result.append(
            Occurrence(
                event_id=event.pk,
                original_start=original,
                starts_at=override.starts_at,
                ends_at=ends,
                is_override=True,
                is_cancelled=False,
            )
        )

    result.sort(key=lambda occ: occ.starts_at)
    return result


# ---------------------------------------------------------------------------
# Orphan detection
# ---------------------------------------------------------------------------


def is_orphan_override(event, occurrence) -> bool:
    """
    True when `occurrence.original_start` no longer corresponds to any
    occurrence the current RRULE would produce.

    Uses a generous detection window (2y back, 2y forward) to handle
    edits that shrink a COUNT-bounded series. False when the event has
    no recurrence rule (overrides on non-recurring events are nonsense
    but tolerated).
    """
    if not event.recurrence_rule:
        return False
    detection_start = occurrence.original_start - timedelta(days=730)
    detection_end = occurrence.original_start + timedelta(days=730)
    # Bypass _cap_window here because orphan detection needs to look
    # outside the hot window. Build rule directly.
    tz = _safe_tz(event.timezone)
    rule = _build_rrule(event, tz)
    if rule is None:
        return True

    local_target = occurrence.original_start.astimezone(tz)
    local_start = detection_start.astimezone(tz)
    local_end = detection_end.astimezone(tz)
    # We could do rule.between() but that materialises a list; for orphan
    # detection a generator scan is fine and bounded by the date window.
    for occ in rule.between(local_start, local_end, inc=True):
        if occ == local_target:
            return False
    return True


def _index_overrides(event):
    """
    Return {original_start (utc datetime): CalendarEventOccurrence} for
    `event`. Uses prefetched data when available, else hits the DB.
    """
    overrides = getattr(event, "_prefetched_overrides", None)
    if overrides is None:
        overrides = list(event.occurrences.all())
    return {ov.original_start: ov for ov in overrides}


# ---------------------------------------------------------------------------
# Multi-event expansion (used by the list endpoint)
# ---------------------------------------------------------------------------


def expand_events(events: Iterable, window_start: datetime, window_end: datetime) -> list[Occurrence]:
    """
    Expand a queryset of events into a flat, time-sorted occurrence list.
    The caller is responsible for filtering visibility before passing in
    the events.
    """
    out: list[Occurrence] = []
    for event in events:
        out.extend(expand_with_overrides(event, window_start, window_end))
    out.sort(key=lambda occ: occ.starts_at)
    return out
