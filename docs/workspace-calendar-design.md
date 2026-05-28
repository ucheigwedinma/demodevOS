# Workspace → Calendar — Design Document

**Status:** Locked, ready for implementation
**Owner:** _tbd_
**Last updated:** 2026-05-11
**Related:** `apps/calendar/` (new), `apps/meetings/`, `apps/notifications/`, `apps/workspace/`, `apps/settings/` (audit log), `client/src/routes/calendar/`
**Companion specs:**
- [`workspace-teams-design.md`](./workspace-teams-design.md) — Teams forward-compat decided here
- [`workspace-calendar-ui-spec.md`](./workspace-calendar-ui-spec.md) — visual + interaction (written next by `/ui-ux-designer`)

---

## 1. Understanding Summary

- **What:** A `Workspace → Calendar` feature in `client/` that gives org users a personal calendar with optional team filtering. Supports four event kinds (`meeting` / `focus` / `out_of_office` / `reminder`), three-tier visibility (`private` / `team` / `org`), full RRULE recurrence with per-occurrence overrides, attendee management (no RSVP), reminders (in-app + email via `apps.notifications`), and a read-only iCal feed for external subscription.
- **Why:** `apps.meetings` owns *operational* meetings (Site Progress, Steering Committee, Toolbox Talk, …) with rich structure. Users need a home for *loose* events (1:1s, OOO, focus blocks, reminders) that don't fit that shape — and a unified canvas that overlays both.
- **For:** Any authenticated org user. Creation is bottom-up; no role-gating.
- **How it's bounded:** New Django app `apps.calendar`. New models `CalendarEvent`, `CalendarEventOccurrence` (overrides), `CalendarEventAttendee`, `IcalFeedToken`. Optional `team_id` FK on `CalendarEvent` (per Teams §12 forward-compat). Read-only overlay from `apps.meetings.Meeting` only — no other source in v1. All UI strings under `workspace.calendar.*` in en/fr/es/ar.
- **What it is *not*:** Not a replacement for `apps.meetings`. Not a CalDAV server. Not a Calendly-style scheduler. Not a multi-user overlay tool.

---

## 2. Decision Log

| # | Decision | Alternatives considered | Why this option |
|---|---|---|---|
| 1 | New `apps.calendar.CalendarEvent` + read-only overlay from `apps.meetings.Meeting` (hybrid) | New model only / view-only aggregator / replace Meeting | Loose events need a home; meetings stay where they are; one canvas |
| 2 | Four event kinds: `meeting` / `focus` / `out_of_office` / `reminder` | Untyped / mid enum (+ holiday/personal/team_ritual) / free-form tags | Captures the 80% case with distinct UI treatments; holidays are v2 |
| 3 | Three visibility tiers (`private` / `team` / `org`) with kind-aware defaults | Two tiers / four tiers (private/attendees/team/org) / derived from team | Maps cleanly to kinds; covers privacy + team status + org-wide |
| 4 | Attendees as M2M, kind-aware UI gating (only `meeting` shows the picker), no RSVP in v1 | No attendees / always M2M / RSVP from day one | Honest about which kinds need attendees; RSVP is YAGNI when ops meetings already have it |
| 5 | Full RRULE (RFC 5545) via `python-dateutil`, per-occurrence overrides via `CalendarEventOccurrence` | None / simple enum / simple + override | User explicit choice; honoured. Highest implementation cost — flagged. |
| 6 | UTC `DateTimeField` + event-level IANA `timezone` field; `zoneinfo` for conversions | UTC only / wall-clock only / creator's TZ implicit | Industry standard; correct for DST + travel + RRULE |
| 7 | Three views — Month, Week, Agenda — switchable; Day defaults to Week-zoomed; Year deferred | Agenda only / Month only / Week only / full Google parity | Covers desktop + mobile + orientation needs without overdesign |
| 8 | Personal calendar + team filter (URL `?team={id}`). Per-user view (B) and overlay mode (D) deferred to v2 | All / personal-only | Tight v1 cut; team filter reuses team_id FK |
| 9 | Reminders: user-default via prefs + per-event override (single value v1); in-app + email **routed through `apps.notifications.services.dispatch_workflow_notification`** | None / single per-event / multi-reminder / direct `send_mail` | Sane default + override; multi is v2; central pipeline picks up user prefs and channel enablement automatically |
| 10 | iCal feed export per user (token-protected URL, hashed storage, rotatable) + per-event `.ics` attachment | None / CalDAV / OAuth two-way | Cheap interop; OAuth is v2/v3 work |
| 11 | Creator-only edit; attendee can self-remove; soft conflict warning; meetings-only overlay; auditlog curated fields; name-only search | Co-edit by attendees / hard conflict block / multi-source overlay / full-text | Conservative permission model; tight v1 |
| 12 | Non-functional defaults accepted; RRULE expansion window 1y forward / 6m back; reminder fan-out via 1-min Celery beat | Larger windows / per-event ETA tasks | Predictable load; survives worker restarts |
| 13 | Code lives in new `apps.calendar` Django app + `client/src/routes/calendar/` | Submodule of `apps.workspace` / submodule of `apps.meetings` | Matches one-app-per-domain convention |

---

## 3. Assumptions (verify before implementation)

- **A1.** `apps.notifications.services.dispatch_workflow_notification(...)` is the canonical delivery pipeline; Calendar reminders use it. Confirmed by inspection.
- **A2.** `apps.meetings.Meeting` has a stable read API; we'll query directly (no new abstraction).
- **A3.** `python-dateutil` is available; if not in `requirements.txt`, add (typically already there via Celery).
- **A4.** `zoneinfo` (Python 3.9+) is available — confirmed (project on Python 3.12+).
- **A5.** `OrganizationMiddleware` scopes querysets by org FK as everywhere else.
- **A6.** `UserProfile` can be extended with `default_reminder_minutes` (or we add it to a calendar-prefs sub-table; resolve in `/django-pro`).
- **A7.** `django-auditlog` accepts new model registrations as it did for Teams.

---

## 4. Non-Goals (v1)

- Two-way sync with Google Calendar / Microsoft 365 (OAuth integrations) — v2+
- CalDAV server endpoint
- Per-user calendar viewing (`/calendar/users/{id}/`) — v2
- Multi-calendar overlay mode (Calendly-style free/busy across people) — v2
- RSVP workflow on attendees — operational meetings cover this
- Day view, Year view
- Other read-only overlays (project milestones, HR leave, finance due dates, support SLA) — additive when shipped
- Holidays / org-wide calendars — v2
- Custom event kinds / tags
- Push notifications (mobile OS) — v2 once Capacitor calendar plugin lands
- Multi-reminder per event (e.g. 1d + 1h + 15min) — v2
- Full-text search on description
- Bulk import / CSV
- "Every other Tuesday and Thursday" UI shortcut — RRULE supports it; v1 UI exposes weekly-on-day pattern only

---

## 5. Architecture

**Backend:** new `apps.calendar` Django app, conventional layout (`models`, `views`, `serializers`, `urls`, `admin`, `signals`, `tasks`, `permissions`, `apps.py`, `ical_export.py`).

**Frontend:** `client/src/routes/calendar/` SvelteKit routes, with reusable components in `client/src/lib/components/calendar/`.

**Cross-app:**
- `apps.meetings.Meeting` — read-only overlay via dedicated endpoint
- `apps.notifications.services.dispatch_workflow_notification` — reminder delivery
- `apps.workspace.Team` — optional FK on `CalendarEvent`
- `apps.settings.AuditLogListView` — extended to scope `CalendarEvent*`

**Celery:** new beat schedule `calendar.dispatch_due_reminders` runs every 60s.

---

## 6. Data Model

```python
# apps/calendar/models.py

class CalendarEvent(models.Model):
    organization = FK(Organization, on_delete=CASCADE, related_name="calendar_events")
    creator      = FK(User, on_delete=CASCADE, related_name="created_calendar_events")
    team         = FK("workspace.Team", null=True, blank=True, on_delete=SET_NULL)

    title        = CharField(max_length=200)
    description  = TextField(blank=True)
    location     = CharField(max_length=200, blank=True)
    meeting_link = URLField(max_length=500, blank=True)

    kind        = CharField(choices=[meeting, focus, out_of_office, reminder], default=meeting)
    visibility  = CharField(choices=[private, team, org], default=private)

    starts_at   = DateTimeField()                          # UTC
    ends_at     = DateTimeField(null=True, blank=True)     # UTC; null only for kind=reminder
    all_day     = BooleanField(default=False)
    timezone    = CharField(max_length=64, default="UTC")  # IANA

    recurrence_rule = CharField(max_length=400, blank=True)  # RFC 5545; "" = single
    recurrence_end  = DateTimeField(null=True, blank=True)

    reminder_minutes_before = PositiveIntegerField(null=True, blank=True)
    # null  → use UserProfile.default_reminder_minutes
    # 0     → no reminder
    # >0    → override

    is_cancelled = BooleanField(default=False)
    created_at, updated_at

    class Meta:
        indexes = [
            Index(fields=["organization", "starts_at"]),
            Index(fields=["creator", "starts_at"]),
            Index(fields=["team", "starts_at"]),
        ]
        constraints = [
            CheckConstraint(check=Q(ends_at__isnull=True) | Q(ends_at__gte=F("starts_at")),
                            name="calendar_event_end_after_start"),
        ]

class CalendarEventOccurrence(models.Model):
    """Override or cancellation of a single occurrence in a recurring series."""
    event           = FK(CalendarEvent, on_delete=CASCADE, related_name="occurrences")
    original_start  = DateTimeField()  # the UTC start the RRULE would have produced
    is_cancelled    = BooleanField(default=False)
    starts_at       = DateTimeField(null=True, blank=True)
    ends_at         = DateTimeField(null=True, blank=True)
    title           = CharField(max_length=200, blank=True)
    location        = CharField(max_length=200, blank=True)
    description     = TextField(blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["event", "original_start"])]

class CalendarEventAttendee(models.Model):
    event       = FK(CalendarEvent, on_delete=CASCADE, related_name="attendees")
    user        = FK(User, on_delete=CASCADE, related_name="calendar_event_attendances")
    invited_by  = FK(User, on_delete=SET_NULL, null=True)
    invited_at  = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["event", "user"])]

class IcalFeedToken(models.Model):
    """One row per active feed token per user. Old tokens stay rows with revoked_at set."""
    user        = FK(User, on_delete=CASCADE, related_name="ical_feed_tokens")
    token_hash  = CharField(max_length=64, unique=True)  # sha256(raw_token)
    created_at  = DateTimeField(auto_now_add=True)
    revoked_at  = DateTimeField(null=True, blank=True)
```

**Key constraints:**
- `ends_at` nullable for `kind=reminder`
- CHECK constraint: `ends_at IS NULL OR ends_at >= starts_at`
- Occurrence override fields are sparse — null/blank means "unchanged"
- Token storage is hash-only; raw shown once at allocation

---

## 7. API Surface

All under `/api/calendar/`.

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/calendar/events/?start=&end=&team=&kind=&q=` | List events in a date window, RRULE-expanded server-side | Authenticated; visibility-filtered |
| POST | `/api/calendar/events/` | Create event (caller becomes creator) | Authenticated |
| GET | `/api/calendar/events/{id}/` | Detail (single event, raw RRULE) | Visibility-permitted |
| PATCH | `/api/calendar/events/{id}/?scope=this\|future\|all` | Edit; series-scope governs recurring semantics | Creator only |
| DELETE | `/api/calendar/events/{id}/?scope=this\|future\|all` | Delete with same series-scope | Creator only |
| POST | `/api/calendar/events/{id}/cancel/` | Cancel without deleting | Creator only |
| POST | `/api/calendar/events/{id}/occurrences/` | Create/update occurrence override | Creator only |
| DELETE | `/api/calendar/events/{id}/occurrences/{original_start}/` | Skip occurrence | Creator only |
| GET | `/api/calendar/events/{id}/attendees/` | List attendees | Visibility-permitted |
| POST | `/api/calendar/events/{id}/attendees/` | Add attendee `{user_id}` | Creator only; idempotent |
| DELETE | `/api/calendar/events/{id}/attendees/{user_id}/` | Remove (or self-leave) | Creator (any) or self |
| GET | `/api/calendar/events/agenda/?cursor=` | Cursor-paginated agenda | Authenticated |
| GET | `/api/calendar/meetings-overlay/?start=&end=&team=` | Read-only overlay of `apps.meetings.Meeting` | Authenticated |
| GET | `/api/calendar/feed/?token=…` | iCal subscribable feed; `text/calendar` | Token-validated |
| POST | `/api/calendar/feed/rotate-token/` | Rotate caller's iCal token | Authenticated |

**Window cap:** server enforces `end - start <= 62 days` for non-agenda calls.

**List response shape (occurrence-flat):**
```json
{ "results": [
  { "event_id": 7, "original_start": "...", "starts_at": "...", "ends_at": "...",
    "title": "Weekly standup", "kind": "meeting", "is_override": false,
    "is_cancelled": false, "creator_id": 12, "team_id": null,
    "my_role": "creator|attendee|viewer" }
]}
```

---

## 8. Permissions Matrix

### Action × role

| Action | Creator | Attendee | Team member (event has team) | Org member | Outsider |
|---|---|---|---|---|---|
| View metadata | ✅ | ✅ | depends on visibility | depends on visibility | ❌ |
| Edit metadata | ✅ | ❌ | ❌ | ❌ | ❌ |
| Add/remove attendees | ✅ | ❌ | ❌ | ❌ | ❌ |
| Self-remove from attendees | ✅ (if also attendee) | ✅ | ❌ | ❌ | ❌ |
| Cancel event | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete event | ✅ | ❌ | ❌ | ❌ | ❌ |
| Edit/skip occurrence | ✅ | ❌ | ❌ | ❌ | ❌ |

### Visibility × viewing

| Visibility | Visible to |
|---|---|
| **private** | Creator + attendees |
| **team** | Creator + attendees + team members (requires `team_id`) |
| **org** | Anyone in the org |

### Secret-team interaction

If the event's `team` has `visibility="secret"`, the event is only visible to team members — regardless of the event's own visibility tier. Secret-team is a stronger gate.

### iCal feed permission

The URL token is the auth. 32-char URL-safe random, stored hashed (SHA-256). Rotating invalidates immediately.

---

## 9. Frontend Pages

| Route | Purpose | Loaded data |
|---|---|---|
| `/calendar` | Main page: view switcher Month/Week/Agenda; date nav; team + kind filters | Concurrent `GET /calendar/events/?start=&end=` and `GET /calendar/meetings-overlay/?start=&end=` |
| `/calendar/events/new` | Create wizard (single page) | Lazy `/projects/` and `/workspace/teams/me/` for FK pickers |
| `/calendar/events/[id]` | Event detail + attendees + recurrence summary + overrides list | `GET /calendar/events/{id}/` + `GET /calendar/events/{id}/attendees/` |
| `/calendar/events/[id]/edit` | Edit metadata. Update-scope prompt for recurring series | as above |

Settings (iCal feed token, default reminder) live on the existing `user-settings/calendar-scheduling/+page.svelte`.

**State:** Svelte 5 runes only. Window-keyed `$derived` event fetches. Optimistic add/remove for attendees.

**Reusable components in `client/src/lib/components/calendar/`:**
- `<MonthView>`, `<WeekView>`, `<AgendaView>`
- `<EventCell event size mode />` — shape adapts per view
- `<KindChip>`, `<VisibilityChip>`, `<RecurrenceEditor>`
- `<EventForm />` — kind-aware (hides attendees for solo kinds)
- `<UpdateScopePrompt />` — "this only / this and future / all" modal
- Reuses `<UserPicker>` and `<Toggle>` from the Teams components

**i18n:** all strings under `workspace.calendar.*` in en/fr/es/ar from day one. Day/month names from `Intl.DateTimeFormat` (locale-aware).

---

## 10. Reminders + Delivery Pipeline

### Effective reminder time

- `event.reminder_minutes_before is None` → `UserProfile.default_reminder_minutes` (we add this field; default 15)
- `event.reminder_minutes_before == 0` → no reminder
- `event.reminder_minutes_before > 0` → override

Per-occurrence overrides shift the trigger automatically via `occurrence.starts_at`.

### Celery beat task

```python
# apps/calendar/tasks.py
@shared_task(name="calendar.dispatch_due_reminders")
def dispatch_due_reminders():
    """Runs every minute. Finds events whose effective reminder window has just
    elapsed (trigger in [now - 60s, now]) and fans out via the notifications service."""
    now = timezone.now()
    window_start = now - timedelta(seconds=60)
    for event in _events_with_reminders_in_window(window_start, now):
        recipients = _resolve_recipients(event)  # creator + attendees
        if not recipients: continue
        dispatch_workflow_notification(
            organization=event.organization,
            event_key="calendar.reminder",
            recipients=recipients,
            context={...},
            fallback_title=f"Reminder: {event.title} starts in {minutes_before}m",
            fallback_message=...,
            fallback_category=Notification.Category.CALENDAR_REMINDER,
            fallback_severity=Notification.Severity.INFO,
            channels=("in_app", "email"),
            fallback_channels=("in_app", "email"),
        )
```

### Category enum extension

`apps.notifications.models.Notification.Category` gains `CALENDAR_REMINDER = "calendar_reminder"`. Users can mute this category independently.

### Beat schedule

```python
"calendar-dispatch-due-reminders": {
    "task": "calendar.dispatch_due_reminders",
    "schedule": 60.0,  # every minute
},
```

### RRULE expansion in the reminder job

Each event with a non-empty `recurrence_rule` expands via `dateutil.rrule.between(window_start - max_minutes_before, now)`. Per-occurrence overrides applied first; `is_cancelled=True` occurrences skipped.

### Failure handling

`dispatch_workflow_notification` handles per-channel failure (`send_mail` is `fail_silently=True`). The Celery task wraps each recipient in a try/except; one bad recipient doesn't poison the batch.

---

## 11. Audit Logging

Uses `django-auditlog`.

```python
# apps/calendar/auditlog_registry.py
auditlog.register(
    CalendarEvent,
    include_fields=["title", "kind", "visibility", "starts_at", "ends_at",
                    "team", "recurrence_rule", "is_cancelled"],
)
auditlog.register(
    CalendarEventOccurrence,
    include_fields=["original_start", "starts_at", "ends_at", "is_cancelled"],
)
auditlog.register(CalendarEventAttendee, include_fields=["user"])
```

**Deliberate exclusions:** `description`, `location`, `meeting_link`, `reminder_minutes_before`.

**Aggregator extension** in `apps/settings/views.py::AuditLogListView.get_queryset`:

```python
from apps.calendar.models import CalendarEvent, CalendarEventOccurrence, CalendarEventAttendee
scopes += [
    _org_ids(CalendarEvent),
    _org_ids_via(CalendarEventOccurrence, lambda qs: qs.filter(event__organization=org)),
    _org_ids_via(CalendarEventAttendee, lambda qs: qs.filter(event__organization=org)),
]
```

**Not audited:** view events, reminder deliveries, iCal feed reads.

---

## 12. iCal Feed + Per-Event `.ics`

### Per-user iCal feed

URL like `https://app.developeros.pro/api/calendar/feed/?token=abc123…`.

**Token mechanics:**
- 32-char `secrets.token_urlsafe(24)` allocated on first request
- Stored hashed (SHA-256) in `IcalFeedToken`
- Raw token shown once at allocation; rotation revokes prior
- Resolution: `SELECT user FROM IcalFeedToken WHERE token_hash = sha256(req_token) AND revoked_at IS NULL`

**Feed contents:**
- All `CalendarEvent`s the user can see per §8
- **NOT** `apps.meetings.Meeting` (per OQ3 — would conflict with their own iCal export)
- RRULE emitted as raw `RRULE:` line; calendar clients expand on their side (correctly handles their local TZ + DST)
- Per-occurrence overrides emitted as `RECURRENCE-ID` exceptions per RFC 5545

**Caching:** 5-min Redis cache keyed `ical_feed:{user_id}:{rev}`. Busted on any write the user is involved in.

### Per-event `.ics`

When creating a meeting-kind event with external attendees (email strings outside the org), the create response includes a base64-encoded `.ics`. The frontend's "Send invite" button triggers an email via the notifications pipeline with `.ics` as attachment. v1 stores external emails as a free-form list on the event; no FK.

---

## 13. Meetings Overlay (read-only)

### Endpoint

`GET /api/calendar/meetings-overlay/?start=&end=&team=` returns a flattened, calendar-friendly shape:

```json
{ "results": [
  { "source": "meeting", "id": 12, "title": "Site Progress Meeting — W19",
    "kind": "meeting", "starts_at": "...", "ends_at": "...", "timezone": "...",
    "location": "...", "meeting_link": "...",
    "meeting_type": "site_progress", "status": "scheduled",
    "project_id": 4, "project_name": "Phoenix Tower",
    "edit_url": "/meetings/12", "edit_in_app": "meetings" }
]}
```

### Visibility

Meetings inherit `apps.meetings`'s rules — no extra filter layer. If the user can't see a Meeting in `/meetings`, it won't appear in `/calendar`.

### No FK either direction

The overlay is a queryset union at the API layer, not a database join. Calendar can be removed without breaking `apps.meetings` and vice versa.

### Concurrent fetch

```ts
const [events, meetings] = await Promise.all([
  api.get(`/calendar/events/?start=${s}&end=${e}`),
  api.get(`/calendar/meetings-overlay/?start=${s}&end=${e}`),
]);
const merged = [...events.results, ...meetings.results].sort(byStart);
```

Failure modes isolated: if `/meetings-overlay/` 500s, calendar events still render with a "Meetings unavailable" banner. Reverse holds.

### Forward-compat

Future overlay sources (project milestones, HR leave, …) add new endpoints in the same shape. Frontend extends the concurrent-fetch list. Zero changes to existing pages.

---

## 14. Testing Strategy

| Layer | What | Where |
|---|---|---|
| Model | constraints, defaults, RRULE expansion correctness across DST, override application | `apps/calendar/tests_models.py` |
| Permission | matrix from §8 across `(visibility, role, secret-team)` cells | `apps/calendar/tests_permissions.py` |
| API | endpoints × roles; list windowing; series-scope update modes; occurrence override CRUD | `apps/calendar/tests_api.py` |
| RRULE | DST forward + back; orphan overrides; COUNT vs UNTIL | `apps/calendar/tests_rrule.py` |
| Notifications | dispatch through `dispatch_workflow_notification`; respects user channel prefs and org channel enablement; skip cancelled occurrences | `apps/calendar/tests_reminders.py` |
| Audit | registered events create `LogEntry`; aggregator returns them; description changes NOT logged | `apps/calendar/tests_audit.py` |
| iCal feed | token mechanics (allocation, rotation, hash storage); RFC-5545 output parseable; cache invalidation; meeting overlays not included | `apps/calendar/tests_ical.py` |
| Meetings overlay | window query correct; org-scoping inherited; merge order in mixed responses | `apps/calendar/tests_overlay.py` |
| Frontend | playwright per page (Month/Week/Agenda render, create, edit-this-vs-all, attendee add/remove, occurrence skip) | existing playwright suite |

### Performance smoke

`GET /api/calendar/events/?start=2026-05-01&end=2026-05-31` for a user attending 20 events including 5 weekly recurring returns < 300ms p95 against a seeded DB.

---

## 15. Edge Cases

| # | Case | Behavior |
|---|---|---|
| EC1 | Event with `kind=reminder` and `ends_at=null` | Allowed; CHECK constraint permits null on ends_at |
| EC2 | Event end < start | 400 from CHECK + serializer |
| EC3 | Weekly 9am-NYC recurring event spans DST | UTC instant shifts 1h; local stays 9am; expansion uses `zoneinfo` per occurrence |
| EC4 | Override at `original_start` no longer matching the RRULE (caller shortened rule) | Orphaned. Hidden from canvas. Detail page surfaces with `is_orphan: true` and a cleanup CTA |
| EC5 | Reminder for cancelled occurrence | Skipped in `_events_with_reminders_in_window` query |
| EC6 | Visibility=`team` with `team_id=null` | Serializer 400 |
| EC7 | Event in secret team with visibility=`org` | Effective visibility is secret (team gate wins) |
| EC8 | Creator removes themselves from attendees | Allowed; remains creator |
| EC9 | Concurrent attendee adds (same user) | Idempotent via unique constraint |
| EC10 | RRULE COUNT=10; override at occurrence 11 | Orphaned per EC4 |
| EC11 | iCal feed token rotated mid-poll | Old → 404; client retries with new |
| EC12 | RRULE asks 100 years (`FREQ=YEARLY` no UNTIL) | Server expansion capped at 1y forward / 6m back. iCal feed emits raw RRULE; clients expand |
| EC13 | External attendee email malformed | Serializer rejects via `EmailField` |
| EC14 | All-day event spanning TZ shift | Stored as midnight local in `timezone`; never UTC-converted |
| EC15 | User's `default_reminder_minutes` null + event override null | No reminder fires (opt-out) |
| EC16 | Two creators editing concurrently | Last-write-wins in v1; v2 may add optimistic lock |

---

## 16. Non-Functional

| | Target |
|---|---|
| Scale | ~50 events/user/month; ~10,000 events/org/year; RRULE expansion window 1y forward / 6m back |
| Performance | Month/Week view p95 < 400ms; Agenda paginated at 50/page; reminders fan-out via 1-min Celery beat |
| Reliability | No separate SLA; iCal feed served from the same Django app |
| Authorization | Org middleware + queryset visibility filtering + DRF permission classes |
| Pagination | Cursor at 25/page for Agenda; window-bounded for Month/Week |
| i18n | en/fr/es/ar from day one under `workspace.calendar.*`; day/month names via `Intl.DateTimeFormat` |
| Notifications | In-app + email via `apps.notifications.services.dispatch_workflow_notification`; new `CALENDAR_REMINDER` category |
| iCal feed | 32-char token, hashed storage, 5-min server cache, rotatable |

---

## 17. Implementation Plan (Sequencing)

1. **Backend foundation** — `apps.calendar` skeleton, `CalendarEvent` + `CalendarEventOccurrence` + `CalendarEventAttendee` + `IcalFeedToken` models, migrations. Extend `UserProfile.default_reminder_minutes` (or sub-table). Run `makemigrations` + `migrate`.
2. **Notifications category** — extend `Notification.Category` enum with `CALENDAR_REMINDER`. One-line migration in `apps.notifications`.
3. **RRULE expansion service** — `apps/calendar/recurrence.py` with `expand_window(event, start, end)` and `expand_with_overrides(...)`. Unit tests for DST + orphans before any API work.
4. **API layer** — serializers, viewsets, permission classes, URL config. Smoke-test each endpoint.
5. **Audit + signals** — register models with auditlog; aggregator extension in `apps.settings`.
6. **Reminder Celery task** — beat schedule, `_events_with_reminders_in_window`, `dispatch_workflow_notification` plumbing.
7. **iCal export + per-event `.ics`** — reuse helpers from `apps.meetings.calendar_export`; feed endpoint with token resolution + caching.
8. **Meetings overlay endpoint** — `/api/calendar/meetings-overlay/`.
9. **Frontend foundation** — components (MonthView, WeekView, AgendaView, EventCell, KindChip, VisibilityChip, RecurrenceEditor, EventForm, UpdateScopePrompt). Reuse Teams' UserPicker/Toggle.
10. **Frontend pages** — `/calendar`, `/calendar/events/new`, `/calendar/events/[id]`, `/calendar/events/[id]/edit`. Extend `user-settings/calendar-scheduling/+page.svelte` for prefs + feed token.
11. **i18n** — extend `workspace.calendar.*` namespace in en/fr/es/ar.
12. **Tests** — model, RRULE, permission matrix, API, sibling overlay, ical, reminders, playwright.
13. **Performance smoke + visibility audit** — seed + run perf test; eyeball secret-team leakage.
