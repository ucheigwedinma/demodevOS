# Workspace → Internal Tasks — Design Document

**Status:** Locked, ready for implementation
**Owner:** _tbd_
**Last updated:** 2026-05-12
**Related:** `apps/internal_tasks/` (new), `apps/workspace/`, `apps/projects/`, `apps/crm/`, `apps/notifications/`, `apps/settings/` (audit log), `client/src/routes/internal-tasks/`
**Companion specs:**
- [`workspace-teams-design.md`](./workspace-teams-design.md) — Teams forward-compat (team_id FK)
- [`workspace-calendar-design.md`](./workspace-calendar-design.md) — sibling pattern that Internal Tasks mirrors
- [`workspace-internal-tasks-ui-spec.md`](./workspace-internal-tasks-ui-spec.md) — visual + interaction (written next by `/ui-ux-designer`)

---

## 1. Understanding Summary

- **What:** A `Workspace → Internal Tasks` feature in `client/` for lightweight personal + team todos that don't fit a specific business process. New `Task` model with assignee, due date, four-state status, three-tier visibility, priority, tags, checklist items, and comments. PLUS a read-only overlay from existing operational task models (`ProjectTask`, `FollowUpTask`) so users see everything on their plate in one canvas.
- **Why:** The codebase has 5 operational task models (Project / CRM / HR / Settings) but none covers free-form "follow up with Joan," "submit Q3 board pack" — the personal/team todos that don't belong to a project, pipeline, or onboarding flow. Internal Tasks is the third leg of the Workspace tripod (Teams ✓ Calendar ✓ Tasks ←).
- **For:** Any authenticated org user. Creation is bottom-up; no role-gating. Defaults bias toward "personal todo" with team-scoping as an opt-in.
- **How it's bounded:** New Django app `apps.internal_tasks`. New models `Task` + `TaskComment`. Optional `team_id` FK on `Task` per Teams §12 forward-compat. Read-only overlay endpoints query existing operational task models — no FKs introduced. i18n keys under `workspace.internal_tasks.*` in en/fr/es/ar.
- **What it is *not*:** Not a project management tool (use `apps.projects.ProjectTask`). Not a CRM follow-up system (use `apps.crm.FollowUpTask`). Not Asana/Jira. Not a kanban board (yet). Not an attachment store. Not a recurring-task engine.

---

## 2. Decision Log

| # | Decision | Alternatives considered | Why this option |
|---|---|---|---|
| 1 | New `apps.internal_tasks.Task` + read-only overlay from operational task models (hybrid) | New model only / view-only / replace existing | Loose tasks need a home; operational tasks stay where they belong; one canvas |
| 2 | Optional `assignee` FK, defaults to creator on create | No assignee / required / multiple assignees | Personal default; supports team backlog ("unassigned"); single owner avoids ambiguity |
| 3 | Four-state status: `todo / in_progress / blocked / done` (v1 list view only; kanban v2 same enum) | 2-state / 3-state / 5-state / custom | Captures "stuck" signal without UI overload |
| 4 | Three-tier visibility: `private / team / org` (mirrors Calendar) | None / two-tier / derived from team | Symmetric with Calendar; secret-team gate inherits |
| 5 | 4-tier priority enum (`low/medium/high/urgent`) + optional `DateField` due_date; sort priority desc → due asc nulls last → created desc | No priority / boolean / Eisenhower / numeric | Universal default; pairs with future kanban |
| 6 | Flat checklist via `checklist_items: JSONField` (no nested subtasks) | None / nested FK / both | Real-world todos use checklists; subtasks are project-task territory |
| 7 | Comments YES (new `TaskComment` table). Activity log NO. Tags YES (Postgres `ArrayField`). Attachments NO. Mentions via comments + notifications. Recurring tasks NO. | Activity log per-event / Tag model / Attachments table / RRULE engine | Each item: ship what's load-bearing, defer the rest |
| 8 | v1 overlay sources: `ProjectTask` + `FollowUpTask`. ON by default on "My" tab, OFF on "Team" tab. OnboardingTask / LeadActivity / TemplateActivity deferred or rejected | All five / none / per-user choice | Two highest-overlap sources for personal todo mental model |
| 9 | Notifications via `dispatch_workflow_notification()`. Triggers: assigned / reassigned / due-approaching (9am day-before + 9am due-day) / comment / mention / blocked / done. New `Notification.Category.TASK_REMINDER`. No per-task reminder override in v1. Digest deferred to v2. | Per-event firehose / minimal / per-task override | Symmetric with Calendar; tasks don't need minute-precision |
| 10 | Non-functional defaults accepted. App name `apps.internal_tasks`. i18n namespace `workspace.internal_tasks.*`. Audit via `django-auditlog` curated fields. Celery beat every 15 min for due-date reminders. | `apps.tasks` / `apps.workspace_tasks` | Boring is good; matches URL + nav; no Celery collision |
| 11 | Edit rights are wider than ownership: creator AND assignee can edit metadata + complete; only creator can delete and change team/visibility | Creator-only / either-edits-everything | Tasks need shared edit (assignee marks in-progress); destructive actions stay narrow |

---

## 3. Assumptions (verify before implementation)

- **A1.** `apps.notifications.services.dispatch_workflow_notification()` is the canonical delivery pipeline. Verified during Calendar work.
- **A2.** `apps.projects.ProjectTask` and `apps.crm.FollowUpTask` have stable queryable APIs and `assigned_to` (or equivalent) fields. **Will verify exact field names in `/django-pro`.**
- **A3.** `OrganizationMiddleware` scopes querysets by org FK; same pattern as Teams + Calendar.
- **A4.** `django-auditlog` accepts new model registrations as it did for Teams + Calendar.
- **A5.** Postgres `ArrayField` is available (PostgreSQL 16 — verified).
- **A6.** `apps.workspace.Team` is the FK target — confirmed (shipped recently).
- **A7.** `Notification.Category` enum extension is a one-line + migration change — confirmed via the Calendar precedent.
- **A8.** `Organization.timezone` exists for org-aware 9am-local reminder scheduling. (If not, fall back to UTC + 9am; identical pattern to Calendar's iCal feed.)

---

## 4. Non-Goals (v1)

- Nested subtasks with separate assignees / due dates — v2 (or use ProjectTask)
- Recurring tasks (RRULE-style) — v2
- Attachments on tasks — v2 (description supports markdown links to Documents)
- Kanban board view — v2 (status enum supports it; just add a new view)
- Calendar overlay (tasks appearing on Calendar canvas) — v2 (additive endpoint)
- Activity log UI — auditlog covers compliance; not surfaced as a user-facing timeline
- Multiple assignees on one task — v2
- Custom status states per team — v3+
- Eisenhower-matrix priority / numeric priority — rejected
- Per-task reminder override — v2
- OnboardingTask / LeadActivity / TemplateActivity overlay — deferred or rejected
- Org-wide-task broadcast workflow — `visibility=org` exists but no special UX
- Bulk import / CSV
- External sync with Asana / Jira / Linear / Trello
- Full-text search on description (name-only via `ILIKE` for v1)
- Markdown rendering in comments — v2 (plain text in v1)
- Saved views / custom filters — v2
- Time tracking / pomodoro / effort estimation
- Task templates — v2
- Comment threading (replies-to-replies) — v2

---

## 5. Architecture

**Backend:** new `apps.internal_tasks` Django app, conventional layout (`models`, `views`, `serializers`, `urls`, `admin`, `signals`, `tasks`, `permissions`, `apps.py`).

**Frontend:** `client/src/routes/internal-tasks/` SvelteKit routes, with reusable components in `client/src/lib/components/internal-tasks/`.

**Cross-app:**
- `apps.projects.ProjectTask` — read-only overlay via dedicated endpoint
- `apps.crm.FollowUpTask` — read-only overlay via same endpoint
- `apps.notifications.services.dispatch_workflow_notification` — reminder + assignment + comment delivery
- `apps.workspace.Team` — optional FK on `Task`
- `apps.settings.AuditLogListView` — extended to scope `Task` + `TaskComment`

**Celery:** new beat schedule `internal_tasks.dispatch_due_reminders` runs every 15 minutes.

---

## 6. Data Model

```python
# apps/internal_tasks/models.py

class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TEAM = "team", "Team"
        ORG = "org", "Org-wide"

    organization = FK(Organization, on_delete=CASCADE, related_name="internal_tasks")
    creator      = FK(User, on_delete=CASCADE, related_name="created_internal_tasks")
    assignee     = FK(User, null=True, blank=True, on_delete=SET_NULL, related_name="assigned_internal_tasks")
    team         = FK("workspace.Team", null=True, blank=True, on_delete=SET_NULL, related_name="internal_tasks")

    title        = CharField(max_length=200)
    description  = TextField(blank=True)

    status       = CharField(choices=Status.choices, default=Status.TODO, db_index=True)
    priority     = CharField(choices=Priority.choices, default=Priority.MEDIUM)
    visibility   = CharField(choices=Visibility.choices, default=Visibility.PRIVATE)

    due_date     = DateField(null=True, blank=True, db_index=True)
    completed_at = DateTimeField(null=True, blank=True)

    tags             = ArrayField(CharField(max_length=40), default=list, blank=True)
    checklist_items  = JSONField(default=list, blank=True)  # [{"label": "...", "checked": false}]

    created_at, updated_at

    class Meta:
        indexes = [
            Index(fields=["organization", "status", "due_date"]),
            Index(fields=["assignee", "status", "due_date"]),
            Index(fields=["team", "status", "due_date"]),
            GinIndex(fields=["tags"], name="task_tags_gin"),
        ]
        ordering = ["-created_at"]

class TaskComment(models.Model):
    task       = FK(Task, on_delete=CASCADE, related_name="comments")
    author     = FK(User, on_delete=SET_NULL, null=True, related_name="task_comments")
    body       = TextField()
    mentions   = ArrayField(IntegerField(), default=list, blank=True)
    created_at, updated_at

    class Meta:
        ordering = ["created_at"]
        indexes = [Index(fields=["task", "created_at"])]
```

**Key choices:**
- `completed_at` denormalised — set on `Task.save()` override when `status` transitions to `done`. Cleared on reopen.
- `tags` GIN index supports fast `WHERE tags @> ARRAY[...]` for filter chips.
- `mentions` is computed in `TaskComment.save()` by regex-matching `@username` in `body`. The notification dispatcher reads this column rather than re-parsing.
- `checklist_items` schema: `[{label: str, checked: bool}]`. No IDs, no order column. Soft limit of 100 enforced in serializer. UI warns above 50.

---

## 7. API Surface

All under `/api/internal-tasks/`.

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/internal-tasks/tasks/?status=&priority=&assignee=&team=&tag=&due_before=&due_after=&overdue=&q=&mine=&cursor=` | List visible tasks (cursor-paginated 25/page) | Authenticated; visibility-filtered |
| POST | `/api/internal-tasks/tasks/` | Create task | Authenticated org member |
| GET | `/api/internal-tasks/tasks/{id}/` | Detail | Visibility-permitted |
| PATCH | `/api/internal-tasks/tasks/{id}/` | Edit | Creator OR assignee |
| DELETE | `/api/internal-tasks/tasks/{id}/` | Delete | Creator only |
| POST | `/api/internal-tasks/tasks/{id}/complete/` | Toggle status to done / reopen | Creator OR assignee |
| POST | `/api/internal-tasks/tasks/{id}/assign/` | Body `{user_id \| null}` | Creator OR current assignee |
| POST | `/api/internal-tasks/tasks/{id}/checklist/` | Replace `checklist_items` (full array) | Creator OR assignee |
| GET | `/api/internal-tasks/tasks/{id}/comments/` | List comments | Visibility-permitted |
| POST | `/api/internal-tasks/tasks/{id}/comments/` | Add comment | Visibility-permitted |
| DELETE | `/api/internal-tasks/tasks/{id}/comments/{comment_id}/` | Delete a comment | Comment author only |
| GET | `/api/internal-tasks/tasks/me/` | Convenience: assignee=caller, status!=done, sorted default | Authenticated |
| GET | `/api/internal-tasks/tasks/tags/` | Tag autocomplete — distinct visible tags ranked by frequency | Authenticated |
| GET | `/api/internal-tasks/overlay/?source=project_task,crm_follow_up&assignee=me\|all&status=&priority=&due_before=&overdue=` | Read-only overlay rows | Authenticated |

**Default sort:** `priority desc → due_date asc nulls last → created_at desc`.

**Filters:**
- `?overdue=true` → `status != done AND due_date < today`
- `?mine=true` → `assignee = caller`
- `?tag=board&tag=urgent` → AND via Postgres `tags @> ARRAY[...]`
- `?q=board` → `title ILIKE %board%` only

---

## 8. Permissions Matrix

### Action × role

| Action | Creator | Assignee | Team member (visibility=team) | Org member (visibility=org) | Outsider |
|---|---|---|---|---|---|
| View task | ✅ | ✅ | depends on visibility | depends on visibility | ❌ |
| Edit metadata (title, description, status, priority, due_date, tags, checklist) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit team / visibility | ✅ | ❌ | ❌ | ❌ | ❌ |
| Reassign | ✅ | ✅ | ❌ | ❌ | ❌ |
| Complete / reopen | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete task | ✅ | ❌ | ❌ | ❌ | ❌ |
| Add comment | ✅ | ✅ | ✅ (if visible) | ✅ (if visible) | ❌ |
| Delete own comment | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ❌ |

### Visibility

| Visibility | Visible to |
|---|---|
| **private** | Creator + assignee only |
| **team** | Creator + assignee + members of the FK'd team (requires `team_id`) |
| **org** | Anyone in the org |

### Secret-team gate

If `team.visibility == "secret"`, the task is only visible to team members regardless of its own visibility. Identical rule to Teams §8-C and Calendar §8-C.

### Implementation seam

- `IsTaskVisible` — read endpoints
- `IsTaskWriter` — edit endpoints (creator OR assignee)
- `IsTaskCreator` — destructive endpoints (delete, change visibility/team)
- `task_role_for(user, task) -> "creator" | "assignee" | "viewer" | None`

---

## 9. Frontend Pages

| Route | Purpose | Loaded data |
|---|---|---|
| `/internal-tasks` | Main page: `My / Team / All` tabs + filter chips + search + inline quick-add | Concurrent `GET /tasks/?...` + `GET /overlay/?source=project_task,crm_follow_up&assignee=me` |
| `/internal-tasks/new` | Create form | `GET /workspace/teams/me/`, tag autocomplete via `/tags/` |
| `/internal-tasks/[id]` | Detail: header + description + checklist + comments + actions | `GET /tasks/{id}/` + `GET /tasks/{id}/comments/` |
| `/internal-tasks/[id]/edit` | Edit form (pre-filled). No update-scope prompt — no recurrence in v1 | as above |

No `/internal-tasks/teams/{id}/` route — team scoping is a filter (`?team={id}`). No per-user view — v2.

**Inline interactions on the list page:**
- Quick-add input at the top: single line → title + Enter creates `status=todo, priority=medium, assignee=self`
- Status checkbox toggles `done` ↔ `todo` directly (no menu)
- Status chip dropdown for `in_progress` / `blocked` transitions
- Optimistic updates with rollback for: complete toggle, status change, assignee change, checklist toggle

**State:** Svelte 5 runes only. List page owns `tab`, `filters`, `searchQuery`, `tasks`, `overlay`.

**Reusable components in `client/src/lib/components/internal-tasks/`:**
- `<TaskRow>` — list row
- `<StatusChip>`, `<PriorityChip>` — small chips
- `<ChecklistEditor>` — `[ ]/[x]` list with add/remove
- `<TaskForm>` — create + edit
- `<CommentThread>` — list + new comment input with `@mention` autocomplete
- `<TagInput>` — chip-style multi-tag input with autocomplete from `/tags/`
- `<OperationalTaskBadge>` — `P` / `C` badges for overlay rows

**i18n:** all strings under `workspace.internal_tasks.*` in en/fr/es/ar from day one.

---

## 10. Reminders + Delivery Pipeline

Same canonical pipeline as Calendar.

### Real-time triggers (Django signals)

| Event | Recipient |
|---|---|
| Assigned to a task | New assignee |
| Reassigned away from you | Previous assignee |
| Status moved to `blocked` | Creator (if different from actor) |
| Status moved to `done` | Creator (if different from actor) |
| New comment on a task you're involved in | Creator + assignee + previously-commented users (deduped, exclude actor) |
| You're @mentioned in a comment | Mentioned user ids from `comment.mentions` |

All routed through `dispatch_workflow_notification(... fallback_category=Notification.Category.TASK_REMINDER ...)`.

### Due-date reminders (Celery beat)

```python
# apps/internal_tasks/tasks.py
@shared_task(name="internal_tasks.dispatch_due_reminders")
def dispatch_due_reminders():
    """
    Runs every 15 minutes. For each task with status != done and due_date set,
    send a reminder at:
      - 9am org-local on (due_date - 1 day)
      - 9am org-local on due_date
    Idempotency: skip if a TASK_REMINDER notification exists for the same
    user + task in the last 23 hours.
    """
```

### Beat schedule

```python
"internal-tasks-due-reminders": {
    "task": "internal_tasks.dispatch_due_reminders",
    "schedule": 900.0,  # every 15 minutes
},
```

### Notification category extension

`Notification.Category` gains `TASK_REMINDER = "task_reminder"`. One-line migration in `apps.notifications`.

---

## 11. Audit Logging

Uses `django-auditlog`.

```python
# apps/internal_tasks/auditlog_registry.py
auditlog.register(
    Task,
    include_fields=["title", "status", "priority", "visibility", "due_date",
                    "assignee", "team", "completed_at", "tags"],
)
auditlog.register(TaskComment)  # full record — comments are short
```

**Deliberate exclusions:** `description`, `checklist_items`, `mentions` (computed).

**Aggregator extension** in `apps/settings/views.py::AuditLogListView.get_queryset`:

```python
from apps.internal_tasks.models import Task, TaskComment
scopes += [
    _org_ids(Task),
    _org_ids_via(TaskComment, lambda qs: qs.filter(task__organization=org)),
]
```

---

## 12. Operational Task Overlay

### Endpoint

`GET /api/internal-tasks/overlay/?source=project_task,crm_follow_up&assignee=me|all&status=&priority=&due_before=&overdue=`

Returns flattened rows:

```json
{ "results": [
  { "source": "project_task", "id": 412, "title": "...",
    "status": "in_progress", "priority": "high", "due_date": "...",
    "assignee_id": 12, "team_id": null,
    "project_id": 4, "project_name": "Phoenix Tower",
    "edit_url": "/projects/tasks/412", "edit_in_app": "projects" }
] }
```

### Status / priority normalization

Operational tasks may use different enums. The overlay serializer maps to Internal Tasks' enums (`todo / in_progress / blocked / done`, `low / medium / high / urgent`) so the frontend's filter chips work consistently. Mapping verified during `/django-pro` and documented inline.

### Visibility

Operational tasks inherit their app's permissions. If a user can't see a ProjectTask in `/projects/tasks`, they don't see it in `/internal-tasks` either.

### No FK either direction

The overlay is a queryset union at the API layer. Internal Tasks can be removed without breaking `apps.projects` or `apps.crm`, and vice versa.

### Forward-compat

Future overlay sources add `?source=onboarding_task` etc. — same endpoint, additive. Frontend extends the source filter dropdown.

---

## 13. Testing Strategy

| Layer | What | Where |
|---|---|---|
| Model | constraints, completed_at auto-set, tag lowercasing, mention extraction | `apps/internal_tasks/tests_models.py` |
| Permission | matrix from §8 parameterized across roles + visibility + secret-team | `apps/internal_tasks/tests_permissions.py` |
| API | endpoints × roles; filters; search; pagination | `apps/internal_tasks/tests_api.py` |
| Comments | add / list / delete; mention parsing; notification fan-out | `apps/internal_tasks/tests_comments.py` |
| Notifications | each trigger fires through `dispatch_workflow_notification`; due-date job idempotency; respect user prefs | `apps/internal_tasks/tests_reminders.py` |
| Audit | events create LogEntry; aggregator returns them; description + checklist NOT logged | `apps/internal_tasks/tests_audit.py` |
| Overlay | normalization; org-scoping inherited; merge order; failure isolation | `apps/internal_tasks/tests_overlay.py` |
| Frontend | playwright per page (list, create, detail, status toggle, comment add) | existing playwright suite |

### Performance smoke

`GET /api/internal-tasks/tasks/?assignee=me&status=todo,in_progress` for a user with 200 tasks returns < 250ms p95 against a seeded DB of 5,000 org-wide tasks.

---

## 14. Edge Cases

| # | Case | Behavior |
|---|---|---|
| EC1 | `visibility=team` with `team_id=null` | Serializer 400: "Team is required when visibility is 'team'." |
| EC2 | Status set to `done` | `completed_at = now()` auto-populated; clearing to `todo` clears `completed_at` |
| EC3 | Task in secret team with `visibility=org` | Effective visibility = secret (team gate wins) |
| EC4 | Comment body `@joan` for unknown user | Mention silently dropped from `mentions`; no notification |
| EC5 | Comment body `@joan @marco @joan` | Deduped in `mentions`; one notification per unique user |
| EC6 | Assignee removed from task's team | Task remains visible to them (assignee always sees their own tasks) |
| EC7 | Tag `"BoarD"` | Stored lowercase `"board"`; filter `?tag=board` matches |
| EC8 | Concurrent edits by creator + assignee | Last-write-wins (no optimistic lock in v1) |
| EC9 | > 100 checklist items | Serializer rejects with 400; UI warns above 50 |
| EC10 | Comment author deactivated (`is_active=False`) | Comment remains; author display shows "[deactivated user]" sentinel; can't delete |
| EC11 | Reminder for task moved to `done` between beat ticks | Skipped via pre-check (`status != done`) |
| EC12 | Idempotency on due-date reminder | Skipped if TASK_REMINDER notification exists for the same user + task in the last 23h |
| EC13 | Overlay source has unknown status not in our enum | Mapped to `todo`; response carries `unmapped_source_status` flag for UI tooltip |
| EC14 | Bulk delete of org with 10k tasks | `CASCADE` from Organization handles it; benchmarked once |

---

## 15. Non-Functional

| | Target |
|---|---|
| Scale | ~50 active tasks/user, ~5,000 active tasks/org |
| Performance | List endpoint p95 < 300ms; cursor pagination at 25/page; overlay fetched in parallel via `Promise.allSettled` |
| Reliability | No separate SLA |
| Authorization | Org middleware + visibility filtering + DRF permission classes + secret-team gate inheritance |
| Pagination | Cursor at 25/page |
| i18n | `workspace.internal_tasks.*` in en/fr/es/ar from day one |
| Notifications | In-app + email via `dispatch_workflow_notification`; new `TASK_REMINDER` category |
| Audit | Curated `auditlog.register` fields per §11 |
| Celery beat | Every 15 min |

---

## 16. Implementation Plan (Sequencing)

1. **Backend foundation** — `apps.internal_tasks` skeleton, `Task` + `TaskComment` models, migrations, admin. Run `makemigrations` + `migrate`.
2. **Notifications category** — extend `Notification.Category` with `TASK_REMINDER`. Migration in `apps.notifications`.
3. **API layer** — serializers, viewsets, permission classes, URL config. Smoke-test each endpoint.
4. **Audit + signals** — `auditlog.register`; signals for assigned / reassigned / status-change / comment / mention notifications; aggregator extension in `apps.settings`.
5. **Reminder Celery task** — beat schedule, due-date dispatcher with idempotency check.
6. **Overlay endpoint** — `/overlay/` returning ProjectTask + FollowUpTask normalized rows. Status/priority mapping verified.
7. **Frontend foundation** — components (TaskRow, StatusChip, PriorityChip, ChecklistEditor, TaskForm, CommentThread, TagInput, OperationalTaskBadge).
8. **Frontend pages** — `/internal-tasks`, `/internal-tasks/new`, `/internal-tasks/[id]`, `/internal-tasks/[id]/edit`.
9. **i18n** — extend `workspace.internal_tasks.*` namespace in en/fr/es/ar.
10. **Tests** — model, permission matrix, API, comments, notifications, audit, overlay, playwright.
11. **Performance smoke + visibility audit** — seed 5,000 tasks; verify perf; eyeball secret-team leakage.
