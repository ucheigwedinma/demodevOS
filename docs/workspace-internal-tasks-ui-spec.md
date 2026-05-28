# Workspace → Internal Tasks — UI/UX Spec

**Companion to:** [`workspace-internal-tasks-design.md`](./workspace-internal-tasks-design.md)
**Inherits from:** [`workspace-teams-ui-spec.md`](./workspace-teams-ui-spec.md) (all design tokens § 1) and [`workspace-calendar-ui-spec.md`](./workspace-calendar-ui-spec.md) (component composition style + overlay-badge pattern)
**Status:** Locked, ready for `/sveltekit` implementation
**Audience:** the engineer (or skill) writing the Svelte components

This is the **visual + interaction** spec. Model, API, permissions, audit, and notifications decisions live in the companion design doc. **Don't duplicate** — refer back to it. Tokens inherit from the Teams UI spec — don't re-derive them.

---

## 1. Inheritance from prior siblings

Everything in `workspace-teams-ui-spec.md` § 1 (typography, surface tokens, spacing, radii, focus rings, team-color palette, iconography) applies here **unchanged**.

From `workspace-calendar-ui-spec.md`:
- Section-card layout convention for the create/edit form
- Overlay-row badge pattern (Calendar's `M` badge → here's `P` / `C` badges with the same shape language: top-right corner, `bg-neutral-200 text-neutral-700`, paired with dashed border on the parent row)
- Locale-aware date rendering via `Intl.DateTimeFormat` — never hardcode month/day names

Internal Tasks adds:
- **Status palette** (§ 2) — 4 status enums → fixed Tailwind class trio
- **Priority palette** (§ 3) — 4 priority enums → fixed class trio (only urgent has a color accent)
- **List-row composition** with inline interactions (quick-add, status-checkbox, status-chip dropdown)
- **Overdue treatment** — red text on the date only, never the whole row
- **Team color accent** rule (left edge strip — reuses Teams 10-token palette from `workspace-teams-ui-spec.md` § 1.6)

---

## 2. Status palette

4 status values, static lookup map in `client/src/lib/components/internal-tasks/task-status.ts`. Tailwind 4's static scanner requires every utility class to appear verbatim — keep all of these as fixed strings in the map.

| Status | Chip bg | Chip text | Chip border | Dot/Icon | Use case |
|---|---|---|---|---|---|
| **todo** | `bg-white` | `text-neutral-600` | `border-neutral-300` | hollow circle | default; the starting line |
| **in_progress** | `bg-neutral-900` | `text-white` | `border-neutral-900` | half-filled circle | active; the working state |
| **blocked** | `bg-amber-50` | `text-amber-700` | `border-amber-200` | warning triangle | stuck; surfaces stalled work |
| **done** | `bg-neutral-100` | `text-neutral-500` | `border-neutral-200` | checkmark | completed; muted so it falls back |

**Why "blocked" gets amber**: it's the only status that demands attention from someone else (the creator, an unblocker). Amber is the universal "needs attention but not critical" color — different enough from rose-red (urgent priority) that the two don't compete on the same row.

**Why "in_progress" is solid black**: it's the visual loudest state on the page. The whole list scans for "what am I actively working on?" — solid neutral-900 chips win that scan.

**Why "done" is the quietest**: completed tasks should fade into the background. Default list filter excludes `done` anyway; when shown via toggle, muted neutral keeps them on the page without distracting.

**Static-class map (literal):**

```ts
// task-status.ts
export type StatusToken = "todo" | "in_progress" | "blocked" | "done";

export const STATUS_TREATMENT: Record<StatusToken, {
  chip: string;
  text: string;
  border: string;
  iconPath: string;     // heroicons-outline path
  label_key: string;     // i18n key
}> = {
  todo:        { chip: "bg-white",       text: "text-neutral-600", border: "border-neutral-300", iconPath: "...", label_key: "workspace.internal_tasks.status.todo" },
  in_progress: { chip: "bg-neutral-900", text: "text-white",       border: "border-neutral-900", iconPath: "...", label_key: "workspace.internal_tasks.status.in_progress" },
  blocked:     { chip: "bg-amber-50",    text: "text-amber-700",   border: "border-amber-200",   iconPath: "...", label_key: "workspace.internal_tasks.status.blocked" },
  done:        { chip: "bg-neutral-100", text: "text-neutral-500", border: "border-neutral-200", iconPath: "...", label_key: "workspace.internal_tasks.status.done" },
};
```

---

## 3. Priority palette

4 priority values. **Only "urgent" gets a color accent** — everything else stays neutral so urgency reads at a glance without color noise on every row.

| Priority | Chip bg | Chip text | Chip border | Indicator | Use case |
|---|---|---|---|---|---|
| **low** | `bg-white` | `text-neutral-500` | `border-neutral-200` | down-arrow icon | informational; sort to bottom |
| **medium** | `bg-white` | `text-neutral-600` | `border-neutral-200` | (no indicator) | default; ~70% of tasks |
| **high** | `bg-white` | `text-neutral-700` | `border-neutral-300` | up-arrow icon | important but not critical |
| **urgent** | `bg-rose-50` | `text-rose-700` | `border-rose-200` | fire icon | drop-everything; the only color accent |

**Display rule:** in list rows, **only render the priority chip when priority is `high` or `urgent`**. Low and medium go silent. Reduces visual noise on the 80% of tasks that don't need to compete.

**Static-class map (literal):**

```ts
// task-priority.ts
export type PriorityToken = "low" | "medium" | "high" | "urgent";

export const PRIORITY_TREATMENT: Record<PriorityToken, {
  chip: string;
  text: string;
  border: string;
  iconPath: string | null;  // null = no indicator
  showInRow: boolean;       // false = hidden in list rows
  label_key: string;
}> = {
  low:    { chip: "bg-white",   text: "text-neutral-500", border: "border-neutral-200", iconPath: "M12 4.5v15M4.5 12l7.5 7.5L19.5 12", showInRow: false, label_key: "workspace.internal_tasks.priority.low" },
  medium: { chip: "bg-white",   text: "text-neutral-600", border: "border-neutral-200", iconPath: null,                                  showInRow: false, label_key: "workspace.internal_tasks.priority.medium" },
  high:   { chip: "bg-white",   text: "text-neutral-700", border: "border-neutral-300", iconPath: "M12 19.5v-15M4.5 12l7.5-7.5L19.5 12", showInRow: true,  label_key: "workspace.internal_tasks.priority.high" },
  urgent: { chip: "bg-rose-50", text: "text-rose-700",    border: "border-rose-200",    iconPath: "M15.362 5.214A8.252...",              showInRow: true,  label_key: "workspace.internal_tasks.priority.urgent" },
};
```

---

## 4. Team color accent (left edge)

When `task.team_id` is set, the `TaskRow` (and the `/internal-tasks/[id]` header card) get a **4px left-edge strip** in the team's color. Reuses the 10-token palette from `workspace-teams-ui-spec.md` § 1.6 (`rose / orange / amber / lime / emerald / teal / sky / indigo / violet / fuchsia`).

```ts
// team-edge-colors.ts (matches the existing one in calendar/team-edge-colors.ts)
import { TEAM_EDGE_CLASS } from "$lib/components/calendar/team-edge-colors";
// reuse — no duplication needed
```

Apply via static lookup: `border-l-4 border-l-{token}-500`. Without a team, `border-l-transparent` (no accent).

**Why on the left edge, not the chip:** the team is *context*, not *content*. Putting the team's color in the chip would compete with status/priority chips for attention. Left-edge strip is unmistakable and visually quiet.

---

## 5. Operational task overlay rows (P / C badges)

Per design doc § 12, overlay rows from `ProjectTask` and `FollowUpTask` render in the same list as native `Task` rows but are **unmistakably read-only**.

### Visual treatment

- **Border:** dashed instead of solid (`border-dashed`, not `border-solid`) — same shape language as Calendar's `M` badge on meeting overlays
- **Badge:** `P` (project) or `C` (CRM) badge in the top-right corner of the row, `h-4 w-4 inline-flex items-center justify-center rounded bg-neutral-200 text-[9px] font-bold text-neutral-700`
- **Hover state:** subtle "click-through" cursor and a tooltip via `title=` attribute: *"Open in Projects"* / *"Open in CRM"*
- **Click action:** navigates to the source's owning app (`/projects/tasks/{id}` or `/crm/leads/{lead_id}`) — **never** opens an inline edit affordance
- **Status checkbox:** **HIDDEN** on overlay rows (can't toggle from here; click-through to the owning app)
- **No three-dot menu:** overlay rows have no destructive actions

### A11y

Overlay rows announce as `role="link"` (not `role="button"`) with `aria-label` like *"From Projects (read-only): {title}. Opens in Projects."* — screen readers immediately understand the row is a navigation target, not an editable item.

### Static lookup

```ts
// task-source-badges.ts
export const SOURCE_BADGE: Record<"project_task" | "crm_follow_up", {
  badge_label: string;
  badge_aria_key: string;
}> = {
  project_task:   { badge_label: "P", badge_aria_key: "workspace.internal_tasks.overlay.project" },
  crm_follow_up:  { badge_label: "C", badge_aria_key: "workspace.internal_tasks.overlay.crm" },
};
```

---

## 6. Components

### 6.1 `<TaskRow>`

The list-row workhorse. Renders a native `Task` OR an overlay row (badge + dashed border variant). All inline interactions live here.

```
┌────────────────────────────────────────────────────────────────────┐
│ ┌──┐                                                               │
│ │  │  Submit Q3 board pack          [In progress ▾]  [URGENT]      │
│ └──┘  ⭕ Joan  ·  May 15  ·  [board] [q3] [+1]               ⋯    │
│  ↑ team color left-edge strip when team_id is set                  │
└────────────────────────────────────────────────────────────────────┘
```

**Layout (left-to-right):**

1. **Checkbox** (44px hit area) — toggles `done` ↔ `todo`. Hidden on overlay rows.
2. **Title** — `text-sm font-medium text-neutral-900`; strikethrough + opacity-60 when status=done.
3. **Status chip** (editable variant) — opens dropdown for transitions (todo / in_progress / blocked / done).
4. **Priority chip** — only renders for `high` and `urgent` (per § 3 rule).
5. **Meta row (below the title):** assignee avatar + name (or "Unassigned"), due date (with overdue red text), tags (first 2 + overflow chip).
6. **Trailing 3-dot menu** — open detail, change assignee, delete, etc.

**Surface tokens:**
- Outer: `flex flex-col gap-1 rounded-2xl border bg-white px-4 py-3 transition hover:border-neutral-400 sm:flex-row sm:items-center sm:gap-3 sm:py-2.5`
- Border: `border-neutral-200` (native), `border-dashed border-neutral-300` (overlay)
- Border-left: `border-l-4 border-l-{teamcolor}-500` when `team_id` set, else `border-l-transparent`
- Hover: `hover:border-neutral-400`
- Focus-within: `focus-within:ring-2 focus-within:ring-neutral-800/10`

**Overdue treatment:**
- Date text: `text-rose-700 font-semibold` only on the date span, not the row
- Optional: small `⚠` icon prepended to the date (heroicons exclamation-circle, `h-3 w-3 text-rose-700`)
- Done rows are NEVER shown as overdue, even if due_date < today

**Inline interactions:**

| Element | Action | Optimistic? |
|---|---|---|
| Checkbox | Toggle `done` ↔ `todo` | ✅ Toggle visually; rollback + toast on error |
| Status chip dropdown | Set to `in_progress` / `blocked` / `done` | ✅ Update chip immediately; rollback on error |
| Assignee avatar (click) | Open assign-to popover with UserPicker | ✅ Update avatar on commit; rollback on error |
| Tag chips (click) | Add to filter (navigates to `?tag=...`) | n/a (read-only interaction) |
| Row body (click anywhere not interactive) | Navigate to `/internal-tasks/[id]` | n/a |
| 3-dot menu | Reveal: Open, Reassign, Move to..., Delete | n/a |

**Mobile collapse:** at `< sm`, layout stacks. Title row goes to the top; meta row drops below. Right-side chips wrap to a new line. Checkbox stays on the left edge with extra padding so it's a thumb-friendly target.

### 6.2 `<StatusChip>`

Two variants: static (read-only) and editable (opens a popover).

**Static variant:**
```
[ ⊙ Todo ]
```

**Editable variant (opens popover on click):**
```
[ ⊙ Todo ▾ ]   →   ┌─────────────┐
                    │ ⊙ Todo      │
                    │ ◐ In progress│
                    │ ⚠ Blocked    │
                    │ ✓ Done       │
                    └─────────────┘
```

Sizing: `inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider`. Icon `h-3 w-3`.

A11y: `role="button" aria-haspopup="listbox" aria-expanded`. Popover options: `role="listbox"`, items `role="option" aria-selected`.

### 6.3 `<PriorityChip>`

Same chip shape as StatusChip. Renders only when `showInRow=true` (per § 3 rule) OR when explicitly forced (e.g. in the detail page header where all priorities are visible).

Editable variant: opens a tiny 4-option popover. Same a11y pattern as StatusChip.

### 6.4 `<ChecklistEditor>`

Inline editable checklist on the detail page.

```
┌─────────────────────────────────────────────────────────────┐
│ Checklist                                          3 of 5  │
│ ─────────────────────────────────────────────────────────── │
│ [✓] Draft outline                                          │
│ [✓] Review with Joan                                       │
│ [✓] Send to chair                                          │
│ [ ] Finalize numbers                          ✏  ⊖         │
│ [ ] Push to board portal                      ✏  ⊖         │
│                                                             │
│ + Add item                                                  │
└─────────────────────────────────────────────────────────────┘
```

**Layout:**
- Each row: checkbox + text + (hover-revealed) edit + remove icons
- Click `+ Add item` → inline input row at the bottom; Enter commits, Esc cancels, blur-with-content commits
- Drag handle on the left for reorder (sortable.js or HTML5 native drag — see OQ4 below)
- Soft limit warning at 50 items: `text-xs text-amber-600` below the list "{i18n.t('workspace.internal_tasks.checklist.soft_limit_warning')}"
- Hard limit at 100 items: `+ Add item` disabled with tooltip

**Optimistic updates:**
- Toggle: checkbox flips immediately; rollback on error
- Add: optimistically append; rollback on error
- Remove: optimistically remove; rollback on error
- Reorder: optimistically reorder; rollback on error

**Save mechanic:** the API takes the entire `checklist_items` array (per design doc § 7 endpoint). Every mutation = full-array replace.

**A11y:** each row has `role="listitem"` inside a `role="list"`. The checkbox is a native `<input type="checkbox">`. Keyboard reorder via `Alt+Up` / `Alt+Down`.

### 6.5 `<TaskForm>`

Single-page form for create + edit. Section-organized like Calendar's `<EventForm>`. Sections in vertical order:

1. **Identity** — title (required), description
2. **Status & priority** — two side-by-side chips that open popovers; default: `todo` / `medium`
3. **Assignment** — assignee (UserPicker single-mode, default to creator), team picker (optional)
4. **Visibility** — radio: private / team / org (matches Calendar visibility radio styling)
5. **Schedule** — due_date (native `<input type="date">`)
6. **Organization** — tags (TagInput) + checklist (ChecklistEditor)
7. **Footer actions** — Dev Fill button (left), Cancel + Create/Save buttons (right)

**Sticky footer:** `sticky bottom-0` bar with `border-t border-neutral-200 bg-neutral-50` background and the action buttons. Same pattern as Calendar EventForm.

**Conditional validation:**
- `visibility=team` requires `team_id` (inline `text-xs text-rose-600` error: *"Pick a team or change visibility."*)
- Title required (max 200 chars, trimmed)

**Dev Fill** populates: title="Demo task", description="Auto-populated by Dev Fill.", status="todo", priority="medium", tags=["demo"]. Per CLAUDE.md.

### 6.6 `<CommentThread>`

Comments list with new-comment input at the bottom.

```
┌─────────────────────────────────────────────────────────────┐
│ Comments · 3                                                │
│                                                              │
│  ⭕ Joan Reyes  ·  2 hours ago                       ⊖      │
│      I'll handle the slides this week.                      │
│                                                              │
│  ⭕ Marco L.  ·  Yesterday                                  │
│      Blocked by missing Q3 numbers from Finance.            │
│      @joan can you ping them?                               │
│                                                              │
│  ⭕ You  ·  Just now                                  ⊖      │
│      Just pinged Finance. Should have by EOD.               │
│                                                              │
│ ─────────────────────────────────────────────────────────── │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Add a comment...                                        │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                              [Post comment] │
└─────────────────────────────────────────────────────────────┘
```

**Comment row:**
- Author initials disc (`h-8 w-8 rounded-full bg-neutral-200 text-xs font-semibold text-neutral-700`)
- Author name + time-ago (`text-xs text-neutral-500`, locale-aware via `Intl.RelativeTimeFormat`)
- Body: `text-sm text-neutral-700 whitespace-pre-wrap` (preserves line breaks; plain text only in v1)
- Delete icon (trash) appears on hover/focus, only on the user's own comments
- `@username` mentions render as `text-sky-700 font-medium` inline spans (just styling — no autolink in v1)
- Deactivated author: name renders as `[deactivated user]` per design doc EC10

**New-comment input:**
- `<textarea>` with `rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm` styling
- Auto-grows on input (CSS `field-sizing: content` if available, otherwise JS rows-adjustment)
- `@` triggers an autocomplete popover with org members (reuses UserPicker's search but as an inline popover)
- Post button: `bg-neutral-900 text-white rounded-xl px-4 py-2 text-sm font-semibold`. Disabled when empty.
- Cmd/Ctrl+Enter submits

**Mention autocomplete a11y:** ARIA Combobox 1.2 pattern (textarea is the input; popover is `role="listbox"`; arrow keys navigate; Enter selects; Esc closes).

### 6.7 `<TagInput>`

Chip-style multi-tag input. Used in `<TaskForm>` and (in v2) for filtering.

```
┌─────────────────────────────────────────────────────────────┐
│ [ board × ] [ q3 × ] [ finance × ]   Type to add…           │
└─────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Pills render existing tags with × buttons
- Typing in the input filters autocomplete from `GET /api/internal-tasks/tasks/tags/`
- Enter, comma, or Tab commits the current input as a new pill
- Backspace on empty input removes the last pill
- All values are lowercased on commit
- Max 20 tags per task (UI-enforced; serializer-side cap is also reasonable)

**Surface tokens:**
- Container: `flex flex-wrap items-center gap-1.5 rounded-2xl border border-neutral-200 bg-neutral-50 px-3 py-2`
- Pill: `inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700`
- × button: `text-neutral-400 hover:text-neutral-900`

**A11y:** Combobox pattern (input is combobox; suggestion list is listbox; pills are descendant of the same listbox visually but in DOM are between input and listbox — use `aria-describedby` to link them as the "selected values" relationship).

### 6.8 `<OperationalTaskBadge>`

Tiny absolute-positioned marker (top-right of TaskRow) for overlay rows.

```ts
// Same shape as Calendar's <MeetingOverlayBadge>
<span
  class="absolute right-1 top-1 inline-flex h-4 w-4 items-center
         justify-center rounded bg-neutral-200 text-[9px] font-bold text-neutral-700"
  aria-label={i18n.t(SOURCE_BADGE[source].badge_aria_key)}
>
  {SOURCE_BADGE[source].badge_label}
</span>
```

Color-blind safe — distinguished by **shape** (dashed border) + **text** (`P` / `C`), not hue.

---

## 7. Routes

### 7.1 `/internal-tasks` — Main page

```
─────────────────────────────────────────────────────────────────────
WORKSPACE
Internal Tasks                                            [+ New task]
Your todos, team backlog, and operational tasks on your plate.

┌── Toolbar ──────────────────────────────────────────────────────┐
│  [ My ] [ Team ] [ All ]                                        │
│                                                                 │
│  Filters:                                                       │
│  [ ⊙ Todo ] [ ◐ In progress ] [ ⚠ Blocked ] [ ✓ Done ]          │
│  [ Overdue ] [ Has tag ▾ ] [ Team ▾ ]      🔍 Search…           │
└─────────────────────────────────────────────────────────────────┘

┌── Quick-add ────────────────────────────────────────────────────┐
│ + Add task: ___________________________________________  ⏎     │
└─────────────────────────────────────────────────────────────────┘

┌── List ─────────────────────────────────────────────────────────┐
│ ┌──┐                                                            │
│ │  │ Submit Q3 board pack                  [⊙ Todo ▾] [URGENT]  │
│ └──┘ ⭕ Joan  ·  May 15  ·  [board] [q3]                       │
│ ─────────────────────────────────────────────────────────────── │
│ ┌──┐                                                            │
│ │  │ Pour foundation slab           [P]    [◐ In progress]      │   ← operational overlay (dashed)
│ └──┘ ⭕ Marco  ·  May 20  ·  Phoenix Tower                     │
│ ─────────────────────────────────────────────────────────────── │
│ ┌──┐                                                            │
│ │  │ Call back on Marina Heights   [C]    [⊙ Todo]              │   ← operational overlay
│ └──┘ ⭕ You  ·  May 13                                          │
│ ─────────────────────────────────────────────────────────────── │
│ [Load more]                                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Toolbar details:**
- **Tab strip** (My / Team / All): `inline-flex rounded-full border border-neutral-300 bg-white p-0.5`. Active: `bg-neutral-900 text-white`. Inactive: `text-neutral-600 hover:bg-neutral-50`.
- **My tab** (default): `?mine=true`, overlay ON by default with `?assignee=me`
- **Team tab**: shows tasks where I'm a member of the FK'd team, OR shows team-scoped + visibility=team tasks. Overlay OFF by default (configurable via filter chip).
- **All tab**: all tasks visible to me by visibility rules. Overlay OFF by default.

**Filter chips:** the four status chips toggle ON/OFF. Default ON: `todo`, `in_progress`. Default OFF: `blocked`, `done`. "Overdue" chip is a single boolean. Tag dropdown opens TagInput-style autocomplete. Team dropdown is a single-select team picker.

**Quick-add:** `<input type="text" placeholder="Add task: type and press Enter">`. On Enter: POST `/tasks/` with `{title, status: "todo", priority: "medium", assignee: me, visibility: "private"}` and prepend the new row optimistically.

**Empty states:**
- **No tasks at all (new user)** — dashed-border full-canvas card: emoji + headline "Your task list is empty" + helper "Add your first task above" + small CTA pointing to quick-add. No "+ New task" CTA here (the full form is over-engineered for a first task).
- **Empty after filter** — flat text inside the existing list card: *"No tasks match this filter — [Clear filters]"*. No emoji.

**Loading:**
- Initial: centered spinner `py-28`
- View-switch / filter-change: skeleton TaskRow placeholders (3-4 rows) with `animate-pulse bg-neutral-100`

**Error:** `<DataStateBanner>` rose-tinted card with retry button (existing pattern).

**Failure isolation:** if `/overlay/` fails but `/tasks/` succeeds, show a small inline yellow pill above the list: *"Operational tasks unavailable — [Retry]"*.

**Mobile (< sm):**
- Tab strip wraps if needed
- Filter chips wrap into multiple rows
- Quick-add input is full-width
- "+ New task" becomes a FAB: `fixed bottom-6 right-6 h-14 w-14 rounded-full bg-neutral-900 text-white shadow-lg`

### 7.2 `/internal-tasks/new` — Create

Standard `<TaskForm>` in create mode. Inherits the Calendar EventForm section-card layout.

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Internal Tasks
New task                                                     [Cancel]

┌── Section 1 — Identity ───────────────────────────────────────┐
│  Title *                                                       │
│  [____________________________________________________________]│
│                                                                │
│  Description (optional)                                        │
│  [____________________________________________________________]│
│  [____________________________________________________________]│
└────────────────────────────────────────────────────────────────┘

┌── Section 2 — Status & priority ──────────────────────────────┐
│  [⊙ Todo ▾]            [Medium ▾]                              │
└────────────────────────────────────────────────────────────────┘

┌── Section 3 — Assignment ─────────────────────────────────────┐
│  Assignee  [UserPicker — defaults to you]                      │
│  Team      [Team picker (optional)]                            │
└────────────────────────────────────────────────────────────────┘

┌── Section 4 — Visibility ─────────────────────────────────────┐
│  ⦿ Private    Only you and the assignee see this task.        │
│  ○ Team       Members of the selected team can see it.        │
│  ○ Org-wide   Anyone in the org can see it.                   │
└────────────────────────────────────────────────────────────────┘

┌── Section 5 — Schedule ───────────────────────────────────────┐
│  Due date  [____________]                                      │
└────────────────────────────────────────────────────────────────┘

┌── Section 6 — Tags & checklist ───────────────────────────────┐
│  Tags                                                          │
│  [TagInput pills + autocomplete]                               │
│                                                                │
│  Checklist                                                     │
│  [ChecklistEditor — empty by default]                          │
└────────────────────────────────────────────────────────────────┘

[ Dev Fill ]                          [Cancel] [Create task]
```

**Validation:** as described in § 6.5.

**Submit success:** redirect to `/internal-tasks/[id]` with toast: *"Task created"*.

**Submit failure:** toast with API field error first, otherwise fallback message.

### 7.3 `/internal-tasks/[id]` — Detail

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Internal Tasks › Submit Q3 board pack

┌── Header card ─────────────────────────────────────────────────┐
│  ┌──┐                                                          │
│  │  │ Submit Q3 board pack                                     │   ← team color left edge
│  └──┘                                                          │
│        [⊙ Todo ▾]  [URGENT]  [⊙ Private]                       │
│                                                                │
│        Joan Reyes (you) · Due May 15 (overdue) · [board] [q3] │
│                                                                │
│        [ Mark in progress ] [ Edit ]   ⋯ (delete, reassign…)  │
└────────────────────────────────────────────────────────────────┘

┌── Description ─────────────────────────────────────────────────┐
│ Long-form description text, preserving line breaks.            │
└────────────────────────────────────────────────────────────────┘

┌── Checklist ───────────────────────────────────────────────────┐
│ <ChecklistEditor>                                              │
└────────────────────────────────────────────────────────────────┘

┌── Comments · 3 ────────────────────────────────────────────────┐
│ <CommentThread>                                                │
└────────────────────────────────────────────────────────────────┘
```

**Header card** is a "big card" (`rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm`, matches Calendar's detail).

**Action buttons gated by my_role:**
- Creator + assignee: all actions (edit, status, reassign, delete in 3-dot menu)
- Creator only: delete + change-visibility + change-team in the 3-dot menu
- Viewer (org/team member who can see): no action buttons; just comments and read

**404 for invisible tasks:** if the API returns 404 (or 403, normalized to 404 client-side per design doc), show the same "Task not found" empty state used in Calendar's `/calendar/events/[id]` 404 — never reveal whether the task exists.

**Empty checklist:** ChecklistEditor renders "No items yet — [ + Add item ]" inline.

**Empty comments:** CommentThread shows "No comments yet. Be the first to comment." above the new-comment input.

### 7.4 `/internal-tasks/[id]/edit`

Same `<TaskForm>` in edit mode, pre-filled. No update-scope prompt (no recurring tasks in v1). Header changes:

```
WORKSPACE › Internal Tasks › Submit Q3 board pack › Edit
Edit task                                                    [Cancel]
```

Save → redirect to `/internal-tasks/[id]` with toast *"Task saved"*.

---

## 8. Mobile considerations

- **Default tab on mobile:** still **My** (most actionable view)
- **Tab strip:** wraps if necessary; otherwise stays on top
- **Filter chips:** wrap into multiple rows; tap targets are 32px+ min height
- **Quick-add input:** full-width on mobile, with the placeholder shortened to *"Add task…"*
- **TaskRow:** stacks (title row → meta row) at `< sm`; checkbox stays on the left edge with `p-1.5` for thumb-friendly hit area
- **FAB:** `+ New task` becomes a floating action button on `< sm`
- **Detail page:** sticky header card on scroll (so action buttons stay reachable on long descriptions)
- **CommentThread input:** auto-focus on mobile only when explicitly opened (don't pop the keyboard on page load)

---

## 9. Accessibility

### Keyboard navigation

- Tab strip: arrow keys to switch tabs (left/right)
- Filter chips: each is a toggle button; Space/Enter toggles
- Quick-add input: Enter creates; Esc clears
- TaskRow list:
  - Arrow Up/Down to move between rows
  - Space toggles the checkbox (done ↔ todo)
  - Enter opens the detail page
  - `S` opens the status dropdown
  - `M` opens the 3-dot menu
- ChecklistEditor:
  - Tab through items
  - Space toggles checkbox
  - Alt+Up / Alt+Down reorders within the list
  - Backspace on empty item removes it
- CommentThread:
  - Cmd/Ctrl+Enter posts
  - Esc cancels mention autocomplete

### Screen readers

- TaskRow announces: *"{status}, {priority if shown}, {title}, assigned to {assignee or 'unassigned'}, due {date or 'no date'}{', overdue' if overdue}"*
- Overlay rows announce as *"From Projects (read-only): {title}. Opens in Projects."* with `role="link"`
- StatusChip / PriorityChip popovers: ARIA Combobox / Listbox pattern
- CommentThread comments are an ordered list (`role="list"`, each `role="listitem"`)
- Mention autocomplete: ARIA Combobox 1.2 pattern
- ChecklistEditor: each row announces as *"{item label}, checked"* or *"unchecked"*

### Color contrast

All text/background pairs cleared WCAG AA (4.5:1 normal text, 3:1 large). The amber/rose accents on `blocked` and `urgent` were verified against neutral text on the chip background.

### Reduced motion

Respect `prefers-reduced-motion`: skeleton placeholders don't pulse; status-chip popover doesn't animate; row hover transitions become instant.

---

## 10. State cheat-sheet

| State | Pattern |
|---|---|
| **Loading (initial)** | Centered `animate-spin` `h-7 w-7` inside `py-28` |
| **Loading (filter change)** | Skeleton TaskRow placeholders |
| **Empty (no tasks ever)** | Dashed full-canvas card pointing at quick-add |
| **Empty (filtered)** | Inline pill above list: *"No tasks match — Clear filters"* |
| **Error (tasks fetch failed)** | `<DataStateBanner>` rose-tinted card with retry |
| **Error (overlay fetch failed, tasks succeeded)** | Inline yellow pill above list: *"Operational tasks unavailable — Retry"*. Native tasks still render. |
| **404 (task not found)** | Neutral-tinted card — never reveals whether the task exists |
| **Optimistic in-flight** | Affected row at 60% opacity; revert on error with toast |
| **Overdue row** | Red text on the due-date span only; never on the row body |

---

## 11. i18n

All strings under `workspace.internal_tasks.*` namespace, contributed in en / fr / es / ar.

Starter key set (`/sveltekit` will round out):

```
workspace.internal_tasks.title                            → "Internal Tasks"
workspace.internal_tasks.eyebrow                          → "Workspace"
workspace.internal_tasks.helper                           → "Your todos, team backlog, and operational tasks on your plate."
workspace.internal_tasks.new_task                         → "New task"
workspace.internal_tasks.edit_task                        → "Edit task"

workspace.internal_tasks.tabs.my                          → "My"
workspace.internal_tasks.tabs.team                        → "Team"
workspace.internal_tasks.tabs.all                         → "All"

workspace.internal_tasks.status.todo                      → "Todo"
workspace.internal_tasks.status.in_progress               → "In progress"
workspace.internal_tasks.status.blocked                   → "Blocked"
workspace.internal_tasks.status.done                      → "Done"

workspace.internal_tasks.priority.low                     → "Low"
workspace.internal_tasks.priority.medium                  → "Medium"
workspace.internal_tasks.priority.high                    → "High"
workspace.internal_tasks.priority.urgent                  → "Urgent"

workspace.internal_tasks.visibility.private               → "Private"
workspace.internal_tasks.visibility.private_helper        → "Only you and the assignee see this task."
workspace.internal_tasks.visibility.team                  → "Team"
workspace.internal_tasks.visibility.team_helper           → "Members of the selected team can see it."
workspace.internal_tasks.visibility.org                   → "Org-wide"
workspace.internal_tasks.visibility.org_helper            → "Anyone in your organization can see it."

workspace.internal_tasks.overlay.project                  → "From Projects (read-only)"
workspace.internal_tasks.overlay.crm                      → "From CRM (read-only)"
workspace.internal_tasks.overlay.unavailable              → "Operational tasks unavailable"
workspace.internal_tasks.overlay.unavailable_retry        → "Retry"

workspace.internal_tasks.filters.overdue                  → "Overdue"
workspace.internal_tasks.filters.clear                    → "Clear filters"

workspace.internal_tasks.quick_add.placeholder            → "Add task: type and press Enter"
workspace.internal_tasks.quick_add.placeholder_mobile     → "Add task…"

workspace.internal_tasks.empty.no_tasks_title             → "Your task list is empty"
workspace.internal_tasks.empty.no_tasks_helper            → "Add your first task above."
workspace.internal_tasks.empty.no_match                   → "No tasks match this filter"
workspace.internal_tasks.empty.no_checklist               → "No items yet"
workspace.internal_tasks.empty.no_comments                → "No comments yet. Be the first to comment."

workspace.internal_tasks.error.not_found                  → "Task not found"
workspace.internal_tasks.error.not_found_helper           → "This task doesn't exist, or you don't have access to it."
workspace.internal_tasks.error.load                       → "Couldn't load tasks"
workspace.internal_tasks.error.load_helper                → "We couldn't reach the task service. Try again."

workspace.internal_tasks.form.section.identity            → "Identity"
workspace.internal_tasks.form.section.status_priority     → "Status & priority"
workspace.internal_tasks.form.section.assignment          → "Assignment"
workspace.internal_tasks.form.section.visibility          → "Visibility"
workspace.internal_tasks.form.section.schedule            → "Schedule"
workspace.internal_tasks.form.section.tags_checklist      → "Tags & checklist"
workspace.internal_tasks.form.title                       → "Title"
workspace.internal_tasks.form.title_placeholder           → "What needs doing?"
workspace.internal_tasks.form.description                 → "Description (optional)"
workspace.internal_tasks.form.assignee                    → "Assignee"
workspace.internal_tasks.form.team                        → "Team"
workspace.internal_tasks.form.due_date                    → "Due date"
workspace.internal_tasks.form.tags                        → "Tags"
workspace.internal_tasks.form.checklist                   → "Checklist"
workspace.internal_tasks.form.create                      → "Create task"
workspace.internal_tasks.form.save                        → "Save changes"
workspace.internal_tasks.form.errors.title_required       → "Title is required."
workspace.internal_tasks.form.errors.team_required        → "Pick a team or change visibility."

workspace.internal_tasks.actions.edit                     → "Edit"
workspace.internal_tasks.actions.delete                   → "Delete"
workspace.internal_tasks.actions.mark_done                → "Mark done"
workspace.internal_tasks.actions.reopen                   → "Reopen"
workspace.internal_tasks.actions.mark_in_progress         → "Mark in progress"
workspace.internal_tasks.actions.reassign                 → "Reassign"
workspace.internal_tasks.actions.move_to                  → "Move to…"

workspace.internal_tasks.checklist.add_item               → "Add item"
workspace.internal_tasks.checklist.add_placeholder        → "New checklist item"
workspace.internal_tasks.checklist.progress               → "{checked} of {total}"
workspace.internal_tasks.checklist.soft_limit_warning     → "Checklists work best under 50 items. Consider breaking this task into smaller ones."

workspace.internal_tasks.comments.title                   → "Comments · {count}"
workspace.internal_tasks.comments.add_placeholder         → "Add a comment…"
workspace.internal_tasks.comments.post                    → "Post comment"
workspace.internal_tasks.comments.deactivated             → "[deactivated user]"
workspace.internal_tasks.comments.delete_confirm          → "Delete this comment? This can't be undone."
workspace.internal_tasks.comments.mention_helper          → "Type @ to mention a teammate"

workspace.internal_tasks.tags.placeholder                 → "Type to add tags"
workspace.internal_tasks.tags.remove                      → "Remove tag"

workspace.internal_tasks.toast.created                    → "Task created"
workspace.internal_tasks.toast.saved                      → "Task saved"
workspace.internal_tasks.toast.deleted                    → "Task deleted"
workspace.internal_tasks.toast.status_updated             → "Status updated"
workspace.internal_tasks.toast.assigned                   → "Reassigned"
workspace.internal_tasks.toast.comment_posted             → "Comment posted"
workspace.internal_tasks.toast.error_generic              → "Something went wrong. Try again."
```

**Day/month names:** NEVER hardcode. Always `Intl.DateTimeFormat(locale).format(date)`.

**Relative time** (e.g. "2 hours ago" on comments): `Intl.RelativeTimeFormat(locale, { numeric: "auto" })`.

**RTL** (Arabic): chip rows reverse via Tailwind `rtl:` variants. Checkbox stays on the leading edge (which is right in RTL). Verify on Arabic locale before shipping.

---

## 12. Open questions for `/sveltekit`

1. **Checklist reorder mechanism** — drag handle + HTML5 native `dragstart`/`dragover` is the cheapest; sortable.js adds a dependency but is more polished. My read: **HTML5 native** in v1; revisit if users complain about jank.

2. **Mention autocomplete in CommentThread** — share code with the existing `<UserPicker>` (from teams) or build a thin inline variant? Both are valid. My read: **build a thin inline variant** (the existing UserPicker is designed for a "select from list" use case, not "insert at cursor in a textarea"). New component: `<MentionAutocomplete>` co-located with `<CommentThread>`.

3. **Status chip dropdown anchoring** — `position: fixed` with computed coords (per the existing Teams pattern) is the safest; nothing in the existing codebase uses a popover library. My read: **inline `position: fixed`** with click-outside-to-close.

4. **TagInput autocomplete** — debounce the `/tags/` call; cache results in a `$state` map keyed by lowercased prefix. My read: 250ms debounce + 30-second client cache.

5. **Overdue check** — compute on the client (`new Date(due_date) < new Date()` after normalizing both to midnight local) OR ship an `overdue: bool` flag from the API? My read: **API ships the flag** so we don't have timezone bugs on the client. Backend already plans to compute this for the filter; adding to the response payload is cheap.

6. **Optimistic update rollback toast wording** — generic *"Something went wrong"* is too vague; field-specific (*"Couldn't save status"*) is friendlier. My read: **field-specific toast keys for the four common optimistic actions** (status change, assignee change, checklist toggle, mark done).

7. **Quick-add input behavior on the Team tab** — should it default the new task's `team_id` to the currently-active team filter? My read: **YES if a team filter is active**; otherwise creates a personal task. Saves a click for the common case.

---

## Sign-off

This spec is the visual + interaction source of truth for Internal Tasks. Implementation (`/sveltekit`) should produce:

- 2 static lookup files in `client/src/lib/components/internal-tasks/` (`task-status.ts`, `task-priority.ts`, plus `task-source-badges.ts`)
- 8 components (`TaskRow`, `StatusChip`, `PriorityChip`, `ChecklistEditor`, `TaskForm`, `CommentThread`, `TagInput`, `OperationalTaskBadge`) — plus a thin inline `<MentionAutocomplete>` co-located with `CommentThread`
- 4 routes (`/internal-tasks`, `/internal-tasks/new`, `/internal-tasks/[id]`, `/internal-tasks/[id]/edit`)
- ~80 i18n keys × 4 locales (en/fr/es/ar)

Anything that contradicts this spec should bounce back here for resolution rather than getting decided silently in code.
