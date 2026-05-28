# Workspace → Teams — Design Document

**Status:** Locked, ready for implementation
**Owner:** _tbd_
**Last updated:** 2026-05-09
**Related:** `apps/workspace/`, `apps/support_desk/`, `apps/notifications/`, `apps/settings/` (audit log), `client/src/routes/teams/`

---

## 1. Understanding Summary

- **What:** A `Workspace → Teams` page in `client/` that lets any org member create lightweight collaboration teams (project pods, cross-functional initiatives, or interest-based guilds), manage four-tier membership (owner / admin / member / guest), and see the team's scoped activity from siblings (Internal Tasks, Calendar, Support Desk).
- **Why:** `apps.hr.Team` is department-bound and HR-curated — it can't model cross-functional squads, working groups, or grassroots guilds. The Workspace domain is meant to be low-friction collaboration; Teams becomes the spine that ties Internal Tasks / Calendar / Support Desk together when work is genuinely team-scoped.
- **For:** Any authenticated org user. Creation is bottom-up, not role-gated.
- **How it's bounded:** New Django app `apps.workspace`. New models `Team` + `TeamMembership`. One nullable FK (`SupportTicket.team`) added in v1; Internal Tasks + Calendar will add their own when those features ship next. All UI strings keyed under `workspace.teams.*` in en/fr/es/ar from day one (Phase 2 of the i18n rollout).
- **What it is *not*:** Not a re-skin of HR teams. Not a Slack/Teams-style chat product. Not an org-chart tool.

---

## 2. Decision Log

| # | Decision | Alternatives considered | Why this option |
|---|---|---|---|
| 1 | New model `apps.workspace.Team`, distinct from `apps.hr.Team` | Reuse HR.Team / replace HR.Team / "my teams" portal view | HR team is dept-bound and admin-curated; workspace team is cross-functional and user-driven. Different lifecycle, different ownership, different visibility |
| 2 | One flexible model with `purpose` enum (project / initiative / guild); optional `project_id` only when purpose=project | Separate models per archetype; just "groups"; only project pods | YAGNI on separate models; explicit purpose still drives UX (filter chips, default visibility hints) without committing to per-archetype schema |
| 3 | Three-tier visibility (public / private / secret) | Admin-curated only; open join; two-tier (public/private) | Confidential task forces ("M&A Review Squad") need "secret"; guilds need self-join "public"; private with request-to-join covers the middle |
| 4 | Loosely-linked spine: nullable `team_id` FK on sibling models with `on_delete=SET_NULL` | Standalone directory; fully-scoped permissions; defer | Integration value (team-scoped tickets/tasks/events) without permission-rework cost |
| 5 | Four-tier roles: owner / admin / member / guest | Flat; two-tier (owner+member); three-tier (owner+admin+member) | Plural admins for delegation; guest tier for advisors/observers (read-only on team-scoped content) |
| 6 | Anyone in the org can create teams | Role-gated; gated by purpose; gated except guilds | Bottom-up culture fit; visibility tiers contain mess (private/secret) without RBAC ceremony |
| 7 | Archive + owner hard-delete; oldest admin auto-promotes when owner leaves; orphan teams surface to org-admin queue | Archive-only; soft-delete; admin-only delete | Self-service consistent with self-service create; nullable FK design makes hard delete safe (siblings keep their rows, just lose `team`) |
| 8 | Real-time notifications on add / promote / owner-transfer + once-a-day team digest (Celery beat) + per-user mute/digest-frequency prefs | Minimal (membership only); per-event firehose | Digest needs mute prefs to not become spam |
| 9 | Color + emoji at create time, auto-defaults, no image upload | Name only; color only; uploadable avatar | Strong identity, zero object-storage cost; matches monochrome-with-color-accent brand |
| 10 | No HR-team connection of any kind | Seed-at-create; live link | YAGNI; user picker is fast enough for v1 |
| 11 | Guests strictly read-only on team-scoped content (DRF-enforced) | Metadata-only; comment+RSVP allowed; member-with-fewer-permissions | Clean rule; promote-to-member is the correct escalation path |
| 12 | Audit membership, visibility, and lifecycle changes via existing `auditlog` infra; name-only search via Postgres `ILIKE` | Membership audit only; full-text search | Cheap; matches existing patterns; full-text is a v2 add-on if needed |
| 13 | v1 sibling spine = `SupportTicket` only (Internal Tasks + Calendar are unbuilt; will add `team` FK when they ship) | Build all three siblings now; defer the spine entirely | Adapts cleanly to current reality; demonstrates the spine value with one rib; forward-compatible |
| 14 | Code lives in new `apps.workspace` Django app + `client/src/routes/teams/` | `apps.teams` (collides with `hr.Team`); submodule of `apps.accounts` | Matches one-app-per-domain convention; door open for Workspace siblings later |

---

## 3. Assumptions

- **A1.** `apps.notifications` accepts new notification types/templates without architectural changes.
- **A2.** `apps.support_desk.SupportTicket` has an `organization` FK and is the right object to scope by team.
- **A3.** The existing `django-auditlog` infra in `apps.settings.AuditLogListView` accepts new registered models with the addition of one query-extension block.
- **A4.** `OrganizationMiddleware` automatically scopes querysets by org FK — no new middleware needed.
- **A5.** `Organization.timezone` exists or can be added; if missing, digest task falls back to UTC + 08:00.
- **A6.** No existing reusable user-picker component on the frontend — `<UserPicker>` will be built here and reused elsewhere.

---

## 4. Non-Goals (v1)

- HR-team linkage of any kind (seed-at-create, live link, sync)
- Image upload for team avatar
- Per-event activity firehose notifications
- Team hierarchies / parent teams / nested teams
- External / cross-org membership
- Team-level Files tab (use the Documents domain)
- Retroactive backfill of existing sibling rows to teams
- Bulk-import of teams or members from CSV
- Slack/Teams-style chat panel
- Full-text search on description (name-only via `ILIKE` for v1)
- Internal Tasks and Calendar siblings (separate, follow-on builds — will land with `team_id` from day one)

---

## 5. Architecture

**Backend:** new `apps.workspace` Django app, conventional layout (`models`, `views`, `serializers`, `urls`, `admin`, `signals`, `tasks`, `permissions`, `apps.py`).

**Frontend:** `client/src/routes/teams/` SvelteKit routes, with reusable components in `client/src/lib/components/teams/`.

**Cross-app:** one cross-app FK (`apps.support_desk.SupportTicket.team` → `apps.workspace.Team`). Audit aggregator extension in `apps.settings.AuditLogListView`. Celery beat task in `apps.workspace.tasks`.

---

## 6. Data Model

```python
# apps/workspace/models.py

class Team(models.Model):
    organization = FK(Organization, on_delete=CASCADE, related_name="workspace_teams")
    name = CharField(max_length=120)
    slug = SlugField(max_length=140)              # auto-generated, unique within org
    description = TextField(blank=True)
    purpose = CharField(choices=[project, initiative, guild], default=initiative)
    visibility = CharField(choices=[public, private, secret], default=public)
    project = FK("projects.Project", null=True, blank=True, on_delete=SET_NULL)
    emoji = CharField(max_length=8, default="👥")
    color = CharField(max_length=20)              # palette token, not raw hex
    is_archived = BooleanField(default=False)
    archived_at = DateTimeField(null=True, blank=True)
    created_by = FK(User, on_delete=SET_NULL, null=True)
    created_at, updated_at

    class Meta:
        constraints = [UniqueConstraint(fields=["organization", "slug"])]
        indexes = [
            Index(fields=["organization", "-created_at"]),
            Index(fields=["organization", "is_archived", "visibility"]),
        ]


class TeamMembership(models.Model):
    team = FK(Team, on_delete=CASCADE, related_name="memberships")
    user = FK(User, on_delete=CASCADE, related_name="workspace_memberships")
    role = CharField(choices=[owner, admin, member, guest], default=member)
    joined_at = DateTimeField(auto_now_add=True)
    invited_by = FK(User, on_delete=SET_NULL, null=True)
    notify_realtime = BooleanField(default=True)
    digest_frequency = CharField(choices=[daily, weekly, off], default=daily)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["team", "user"]),
            UniqueConstraint(fields=["team"], condition=Q(role="owner"), name="one_owner_per_team"),
        ]
        indexes = [
            Index(fields=["user", "team"]),
            Index(fields=["team", "role"]),
        ]
```

Key constraints:
- **One owner per team** enforced at DB level via partial unique constraint. Ownership transfer is a single transaction (demote old owner → promote new owner).
- **Slug** auto-derived from name with org-scoped uniqueness; rename appends `-2`, `-3`, etc., deterministically.
- **Color** stores a palette token (e.g. `"violet"`), not raw hex — keeps Tailwind classnames static.

---

## 7. API Surface

All under `/api/workspace/`.

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/api/workspace/teams/` | List visible teams (filters: `purpose`, `visibility`, `q`, `archived`, `mine`) | Authenticated |
| POST | `/api/workspace/teams/` | Create team (caller becomes owner) | Authenticated |
| GET | `/api/workspace/teams/{id}/` | Detail (incl. linked-resource counts) | Visible to caller |
| PATCH | `/api/workspace/teams/{id}/` | Edit metadata | Owner or admin |
| POST | `/api/workspace/teams/{id}/archive/` | Archive (toggleable) | Owner or admin |
| DELETE | `/api/workspace/teams/{id}/` | Hard delete | Owner only |
| POST | `/api/workspace/teams/{id}/transfer/` | Transfer ownership | Owner only |
| GET | `/api/workspace/teams/{id}/members/` | List members | Visible to caller |
| POST | `/api/workspace/teams/{id}/members/` | Add member | Owner or admin |
| PATCH | `/api/workspace/teams/{id}/members/{user_id}/` | Change role | Owner or admin |
| DELETE | `/api/workspace/teams/{id}/members/{user_id}/` | Remove or self-leave | Self for own row; owner/admin for others |
| POST | `/api/workspace/teams/{id}/join/` | Self-join (visibility=public only) | Authenticated |
| POST | `/api/workspace/teams/{id}/request-join/` | Request join (visibility=private only) | Authenticated |
| GET | `/api/workspace/teams/me/` | Convenience: caller's teams | Authenticated |

Pagination: cursor at 25/page. Search: `q=name__icontains`.

---

## 8. Permissions Matrix

### Action × team role

| Action | Owner | Admin | Member | Guest | Non-member |
|---|---|---|---|---|---|
| View team metadata | ✅ | ✅ | ✅ | ✅ | depends on visibility |
| View team-scoped tickets | ✅ | ✅ | ✅ | ✅ read-only | depends on visibility |
| Create team-scoped ticket | ✅ | ✅ | ✅ | ❌ | n/a |
| Edit team metadata | ✅ | ✅ | ❌ | ❌ | ❌ |
| Add member | ✅ | ✅ | ❌ | ❌ | ❌ |
| Remove member | ✅ | ✅ | ❌ | ❌ | ❌ |
| Promote/demote roles | ✅ | ✅ (cannot touch owner) | ❌ | ❌ | ❌ |
| Self-leave | ✅ only after transfer | ✅ | ✅ | ✅ | n/a |
| Archive / unarchive | ✅ | ✅ | ❌ | ❌ | ❌ |
| Hard delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| Transfer ownership | ✅ | ❌ | ❌ | ❌ | ❌ |

### Visibility × non-member viewing

| Visibility | Listed in directory? | Detail page | Can request to join? |
|---|---|---|---|
| public | ✅ | ✅ | self-join (no approval) |
| private | ✅ | metadata-only stub + "request to join" | ✅ (approval) |
| secret | ❌ (hidden) | 404 unless invited | ❌ (must be added) |

---

## 9. Frontend Pages

| Route | Purpose | Loaded data |
|---|---|---|
| `/teams` | Directory: filter chips (My / All / Archived), purpose filter, name search | `GET /api/workspace/teams/?mine=true` (default) |
| `/teams/new` | Create wizard (single page) | reads `/projects/` only when purpose=project |
| `/teams/[id]` | Detail: metadata, members, "Linked work", actions | `GET /api/workspace/teams/{id}/` + `GET /api/workspace/teams/{id}/members/` |
| `/teams/[id]/edit` | Edit metadata | as above |
| `/teams/[id]/members` | Full member-management for large rosters | `GET /api/workspace/teams/{id}/members/?page=1` |
| `/teams/[id]/settings` | Notifications, danger zone | inline state |

**State:** Svelte 5 runes only, no global store. Optimistic updates with rollback for member add/remove + role change.

**Reusable components in `client/src/lib/components/teams/`:**
- `<TeamAvatar emoji color size />`
- `<TeamCard />` (directory cell)
- `<MemberRow />`
- `<UserPicker multiple />`
- `<RoleSelect />`

**i18n:** all strings under `workspace.teams.*` in en/fr/es/ar from day one. No English literal in any rendered template.

---

## 10. Notifications

### Real-time triggers (Django signals on TeamMembership)

| Event | Recipient |
|---|---|
| Added to team | The added user |
| Removed from team | The removed user |
| Promoted to admin | The promoted user |
| Demoted from admin | The demoted user |
| Ownership transferred to you | New owner |
| Ownership transferred away | Previous owner |

Each respects `TeamMembership.notify_realtime`. Unsubscribe link → `/teams/[id]/settings`.

### Daily digest (Celery beat)

`apps.workspace.tasks.send_team_digests` runs daily at 08:00 in each org's timezone:

- Iterates active memberships with `digest_frequency="daily"`
- Builds digest of last 24h SupportTicket activity (opened, resolved, escalated)
- Suppresses empty digests
- Email send failures are logged, not retried

Per-user `digest_frequency`: `daily` / `weekly` / `off` (Q12 confirmed).

When Internal Tasks and Calendar ship, they extend the digest builder with additional sections following the same pattern.

---

## 11. Audit Logging

Uses `django-auditlog` (consistent with existing infra).

```python
# apps/workspace/auditlog_registry.py
auditlog.register(
    Team,
    include_fields=["name", "description", "purpose", "visibility",
                    "project", "is_archived", "emoji", "color"],
)
auditlog.register(TeamMembership, include_fields=["role"])
```

Aggregator extension in `apps/settings/views.py::AuditLogListView.get_queryset`:

```python
from apps.workspace.models import Team, TeamMembership
scopes += [
    _org_ids(Team),
    _org_ids_via(TeamMembership, lambda qs: qs.filter(team__organization=org)),
]
```

Team-related events appear in the existing `Settings → Audit & Activity Logs` page.

**Not audited:** view events, notification deliveries, digest emails.

---

## 12. Sibling Spine (v1 — SupportTicket only)

### Migration

```python
# apps/support_desk/migrations/00XX_add_team_fk.py
operations = [
    migrations.AddField(
        model_name="supportticket",
        name="team",
        field=models.ForeignKey(
            "workspace.Team",
            on_delete=models.SET_NULL,
            null=True, blank=True,
            related_name="support_tickets",
        ),
    ),
    migrations.AddIndex(
        model_name="supportticket",
        index=models.Index(
            fields=["team", "-created_at"],
            name="supportticket_team_created_idx",
        ),
    ),
]
```

### Queryset extension on SupportTicketViewSet

```python
qs = qs.filter(organization=org)                  # existing
qs = qs.exclude(                                   # new
    Q(team__visibility="secret") & ~Q(team__memberships__user=user)
)
# When team is null, original behavior preserved.
```

### UI changes

- Optional `<TeamPicker />` on ticket-create + edit forms
- `<TeamAvatar>` chip on ticket detail when set
- Optional team filter chip on ticket list

### Forward-compat

When Internal Tasks and Calendar ship, each adds a `team` FK with the same migration shape. Team detail page extends to show `tasks_count` + `events_count`. No re-architecture.

---

## 13. Testing Strategy

| Layer | What | Where |
|---|---|---|
| Model | constraints, defaults, archived_at toggle | `apps/workspace/tests_models.py` |
| Permission | matrix from §8, parameterized | `apps/workspace/tests_permissions.py` |
| API | endpoints × {owner, admin, member, guest, non-member}; visibility filtering | `apps/workspace/tests_api.py` |
| Audit | events create LogEntry; aggregator returns them | `apps/workspace/tests_audit.py` |
| Notifications | triggers fire once; respect mute prefs | `apps/workspace/tests_notifications.py` |
| Digest task | timezone scheduling; failures logged not retried | `apps/workspace/tests_tasks.py` |
| Sibling | SupportTicket queryset honors visibility; null-team unchanged | `apps/support_desk/tests_team_scoping.py` |
| Frontend | playwright per page (directory, create, detail, member CRUD, archive, transfer, delete) | existing playwright suite |

### Performance smoke

`GET /api/workspace/teams/?mine=true` for a user in 50 teams returns < 200ms p95 against a seeded DB of 200 teams × 20 members.

---

## 14. Edge Cases

| # | Case | Behavior |
|---|---|---|
| EC1 | Owner self-leaves with no transfer | 400 *"Transfer ownership before leaving"* |
| EC2 | Owner leaves the org (`is_active=False`) | Auto-promote oldest-by-`joined_at` admin; if no admins, `is_orphaned=True`, surfaces in org-admin orphan queue |
| EC3 | Last admin demoted, only owner remains | Allowed |
| EC4 | Visibility public → secret with non-member tickets visible | Tickets become invisible on next request; in-flight UI may show stale until reload (acceptable) |
| EC5 | Linked Project deleted | `team.project` → NULL via `on_delete=SET_NULL`; UI shows "(project removed)" |
| EC6 | Concurrent role change | Optimistic lock via `updated_at`; second writer gets 409 |
| EC7 | Hard delete with 100+ linked tickets | Tickets keep their rows; `team` → NULL via SET_NULL; one audit row |
| EC8 | Slug collision after rename | Append `-2`, `-3`, etc.; deterministic |
| EC9 | Digest fan-out for org with 200 teams × 20 members | One Celery task per org; queued sends async; budget < 500ms compute |
| EC10 | Member count desync | Detail counts always come from fresh aggregate query |
| EC11 | Add user already in team | Idempotent — 200 with existing membership, no new audit row |
| EC12 | User account deleted while in team | `TeamMembership` cascades; if owner, EC2 fires |

---

## 15. Non-Functional

| | Target |
|---|---|
| Scale | ~50–200 teams per org; 5–20 members typical (long tail to ~50); few hundred org users total |
| Performance | Directory list p95 < 300ms; detail p95 < 400ms; member ops p95 < 200ms |
| Audit | All membership / visibility / lifecycle changes logged |
| Reliability | No separate SLA; recoverable from regular DB backups |
| Authorization | Org middleware + visibility filtering at queryset level; DRF permission classes per §8 |
| Pagination | Cursor at 25/page |
| i18n | en/fr/es/ar from day one under `workspace.teams.*` |

---

## 16. Implementation Plan (Sequencing)

1. **Backend foundation** — `apps.workspace` skeleton, `Team` + `TeamMembership` models, migrations, admin registration. Run `makemigrations` + `migrate` on staging DB.
2. **API layer** — serializers, ViewSets, permission classes, URL config. Smoke-test each endpoint manually.
3. **Audit + signals** — `auditlog.register` calls; signals for membership-state notifications; aggregator extension in `apps.settings`.
4. **Celery digest task** — beat schedule, builder for SupportTicket activity, mute pref handling.
5. **SupportTicket integration** — migration adding `team` FK; queryset extension; serializer field; minimal UI plumbing on ticket forms.
6. **Frontend foundation** — `<TeamAvatar>`, `<UserPicker>`, `<RoleSelect>`, `<TeamCard>`, `<MemberRow>` components.
7. **Frontend pages** — `/teams`, `/teams/new`, `/teams/[id]`, `/teams/[id]/edit`, `/teams/[id]/members`, `/teams/[id]/settings`.
8. **i18n strings** — extend `workspace.teams.*` namespace in en/fr/es/ar.
9. **Tests** — model, permission matrix, API, sibling scoping, playwright scenarios.
10. **Performance smoke + visibility audit** — seed 200×20, run perf test, eyeball secret-team leakage.

Each step has a clear stop-and-verify gate before moving on.
