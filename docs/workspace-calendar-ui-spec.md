# Workspace → Calendar — UI/UX Spec

**Companion to:** [`workspace-calendar-design.md`](./workspace-calendar-design.md)
**Inherits from:** [`workspace-teams-ui-spec.md`](./workspace-teams-ui-spec.md) (typography, surface tokens, spacing rhythm, focus rings, iconography, team color palette)
**Status:** Locked, ready for `/sveltekit` implementation
**Audience:** the engineer (or skill) writing the Svelte components

This is the **visual + interaction** spec. The model, API, permissions, and audit decisions live in the companion design doc. **Don't duplicate** — refer back to it for anything not visual. Tokens inherit from the Teams UI spec — don't re-derive them.

---

## 1. Inheritance from Teams UI spec

Everything in `workspace-teams-ui-spec.md` §1 (Design tokens — type scale, surface tokens, spacing, radii, focus, team color palette, iconography) applies here unchanged. Calendar adds:

- **Kind palette** (§2 below) — 4 fixed treatments for `meeting | focus | out_of_office | reminder`
- **Meetings overlay treatment** — distinguishes read-only `apps.meetings.Meeting` rows
- **Calendar-grid spacing** — the Month/Week grids have their own rhythm because the cells are dimensioned by time, not by content

---

## 2. Kind palette (the new "color" system for events)

The Calendar has no per-team color on event *fills* — that would conflict visually with team identity in the rest of the app. Instead, **the team color appears on the left edge** of an event block (4px strip), and the **fill is kind-driven**.

Each kind resolves to a static lookup map in `client/src/lib/components/calendar/event-kinds.ts`:

| Kind | Block bg | Block text | Block border | Pattern | Icon |
|---|---|---|---|---|---|
| `meeting` | `bg-neutral-900` | `text-white` | `border-neutral-900` | solid | calendar-glyph |
| `focus` | `bg-neutral-100` | `text-neutral-700` | `border-neutral-200` | very subtle dotted (CSS bg) | brain / focus-eye |
| `out_of_office` | `bg-white` | `text-neutral-700` | `border-neutral-300` | diagonal stripes (CSS bg) | plane / palm-tree |
| `reminder` | n/a (rendered as marker, not block) | `text-neutral-700` | n/a | n/a | bell-small |

**Pattern note:** `focus` and `out_of_office` patterns are CSS background-image gradients applied via fixed utility classes (`bg-pattern-dots`, `bg-pattern-diagonal`) declared in a custom Tailwind layer — NOT dynamic generation. Tailwind 4's static scanner is honored.

**Reminder rendering:** because `reminder` has no duration, it renders as a small dot/marker at the moment-in-time on the timeline, NOT a block. In Month view: a small dot inside the day cell with the title. In Week view: a horizontal line + dot at the time position. In Agenda: a normal row but with the bell icon prominent.

**Cancelled events:** any kind with `is_cancelled=true` gets a strike-through on the title and 50% opacity. Hover/focus still reveals full info.

### 2.1 Team color accent (left edge)

When `event.team_id` is set, the block gets an additional `border-l-4 border-l-{token}-500` lookup from Teams UI spec §1.6. The 10 team-color tokens map to 10 fixed border classes. Without a team, the left edge is the same as the block border (no accent).

### 2.2 Meetings overlay treatment

Rows from `apps.meetings.Meeting` (the read-only overlay) get a **dashed border** + **small "M" badge** in the top-right corner:

- `border-dashed border-neutral-400` instead of solid
- Top-right corner: `<span class="absolute top-1 right-1 h-4 w-4 inline-flex items-center justify-center rounded text-[9px] font-bold bg-neutral-200 text-neutral-700">M</span>`
- Hover state: cursor switches to a "click-through" icon and a tooltip says "Open in Meetings"
- Click navigates to `/meetings/{id}` (the existing meeting detail page)
- **Cannot be dragged, resized, or edited inline** — purely a navigation surface

Color-blind / contrast note: meetings overlay is identifiable by the dashed border + badge, not by hue — the difference works for users who can't perceive subtle color shifts.

---

## 3. Components

### 3.1 `<KindChip kind size />`

Small kind indicator chip. Used in EventForm, detail page, filter shelf.

```
Props:
  kind: "meeting" | "focus" | "out_of_office" | "reminder"
  size?: "sm" | "md"

Closed shape: rounded-full inline-flex items-center gap-1 px-2.5 py-0.5
              text-[10px] font-semibold uppercase tracking-wider
              border + tone driven by lookup map

Kinds (sm size):
  meeting       → border-neutral-300 bg-neutral-900 text-white
  focus         → border-neutral-200 bg-neutral-100 text-neutral-700
  out_of_office → border-neutral-300 bg-white text-neutral-700
  reminder      → border-neutral-200 bg-white text-neutral-600
```

Each chip includes the kind icon (`h-3 w-3`).

### 3.2 `<VisibilityChip visibility size />`

Inherits the chip shape and gets one of three icons + label:

| Visibility | Icon | Label |
|---|---|---|
| `private` | lock-closed | "Private" |
| `team` | users | "Team" |
| `org` | globe | "Org-wide" |

All three use `border-neutral-200 bg-neutral-50 text-neutral-600` for consistency — visibility shouldn't compete with kind for attention.

### 3.3 `<EventCell event view mode />`

The chameleon component. Single source of truth for "render an event"; shape adapts to context.

```
Props:
  event: CalendarEvent | MeetingOverlayRow
  view: "month" | "week" | "agenda"
  mode?: "default" | "compact" | "hover-tooltip"
```

**Month view (compact pill):**
```
┌──────────────────────────────────┐
│⬛│ 9:30 Standup                   │  ← color-bar (team) + time + title
└──────────────────────────────────┘
   • truncate title to 1 line
   • h-5 px-1.5 text-[11px]
   • kind treatment applied to whole pill
```

**Week view (timeline block):**
```
┌──────────────────────────────────┐
│⬛│ 9:30 — 10:00                   │  ← time range header
│  │ Mobile Squad Standup          │  ← title
│  │ 6 attendees · Conference Rm 3 │  ← meta line (only when block is tall enough)
└──────────────────────────────────┘
   • height ∝ duration; min h-12
   • absolute positioned in the day column
   • kind treatment + team-color left edge
```

**Agenda view (row):**
```
┌──────────────────────────────────────────────────────────────┐
│  09:30 ─ 10:00  ⬛ [Meeting] Standup · Mobile Squad · 6 attendees  │  >
└──────────────────────────────────────────────────────────────┘
   • flex items-center gap-3 px-4 py-3 rounded-2xl border border-neutral-200 bg-white
   • time on left as fixed-width column
   • kind chip then title; meta in muted text
```

For all three views, the click action opens the detail page (or modal — see §6.1). For meetings overlay rows, click navigates to `/meetings/{id}`.

### 3.4 `<MonthView events meetings selectedDate />`

7-column × 5–6-row grid. Each cell shows the day number, all-day band at top, then up to 3 timed events as pills, then "+N more" link.

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Mon       Tue       Wed       Thu       Fri       Sat       Sun                │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────────│
│ 28       │ 29       │ 30       │ 31       │ 1        │ 2        │ 3            │   ← dimmed (prior month)
│          │          │          │          │          │          │              │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────────│
│ 4        │ 5        │ 6        │ 7        │ 8        │ 9        │ 10           │
│ ▪ Joan OOO ────────────────────────────────────▶                              │   ← all-day bar spans cells
│ • 09:30 │ • 09:30  │ • 09:30  │ • 09:30  │ • 09:30  │          │              │   ← daily standup
│ • 14:00 │ • 11:00  │          │ • 13:00  │          │          │              │
│ + 2 more│          │          │          │          │          │              │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────────│
│ 11      │ 12 (today) │ 13     │ 14       │ 15       │ 16       │ 17           │   ← today: ring-2 ring-neutral-900/30
...
```

**Sizing:**
- Cell: minimum `h-32` (128px) on desktop; `h-24` (96px) on tablet
- Day-number: `text-xs font-semibold text-neutral-600` for in-month; `text-neutral-300` for prior/next month
- Today badge: `inline-flex items-center justify-center h-6 w-6 rounded-full bg-neutral-900 text-white text-xs font-semibold`

**Overflow rule:**
- Max 3 timed events visible
- "+N more" link in `text-[10px] font-semibold text-neutral-500 hover:text-neutral-900 cursor-pointer`
- Click opens a popover anchored at the cell with the full list (scrollable)

**All-day band:**
- Lives between the day-number row and the timed events
- All-day events render as horizontal bars spanning the cells they cover
- If multiple all-day events on the same day, they stack (up to 2 visible, then "+N more" same as timed)

**Click interactions:**
- Click empty cell area → open create modal with `starts_at` defaulted to that day at 9:00 local
- Click day-number → switch to Week view anchored on that day
- Click event pill → open detail (modal or page — see §6.1)

### 3.5 `<WeekView events meetings selectedDate workingHours />`

Vertical timeline, 7 day columns × hours. The hardest view to lay out.

```
        Mon 4   Tue 5    Wed 6    Thu 7    Fri 8    Sat 9    Sun 10
       ┌───────┬────────┬────────┬────────┬────────┬────────┬────────┐
ALLDAY │▪ Joan OOO ─────────────────────────────────────────▶        │
       ├───────┼────────┼────────┼────────┼────────┼────────┼────────┤
 07:00 │       │        │        │        │        │        │        │
 08:00 │       │        │        │        │        │        │        │
 09:00 │       │        │ ┌─────┐│        │        │        │        │
       │       │        │ │Stand│       (current time line ─ ─ ─ ─ ─▶│
       │       │        │ │up   ││        │        │        │        │
 10:00 │       │        │ └─────┘│        │        │        │        │
       │       │        │        │        │        │        │        │
 11:00 │       │ ┌─────┐│        │        │        │        │        │
       │       │ │1:1  ││        │        │        │        │        │
 12:00 │       │ └─────┘│        │        │        │        │        │
 13:00 │       │        │ ┌────┐ │        │        │        │        │
       │       │        │ │Foc.│ │        │        │        │        │   ← focus block (patterned)
 14:00 │       │        │ └────┘ │        │        │        │        │
 ...
 20:00 │       │        │        │        │        │        │        │
       └───────┴────────┴────────┴────────┴────────┴────────┴────────┘
```

**Sizing:**
- Day column width: `flex-1` (equal split across 7 columns)
- Hour row height: `h-12` (48px) on desktop, `h-16` (64px) on tablet (more touch room)
- Time axis: 56px fixed-width left column with `text-[10px] text-neutral-400 tabular-nums`
- Default time range: from `user.working_hours_start` (default 07:00) to `user.working_hours_end` (default 20:00)
- Below working hours: collapsed initially; "Show earlier" / "Show later" toggles expand

**Current-time line:**
- A 1px dashed neutral-400 line at the current minute, with a small disc on the today-column edge
- Updates every minute via `$effect` + `setInterval`

**Today highlight:**
- Today's column header gets `bg-neutral-50 text-neutral-900` instead of `text-neutral-500`
- Today's column body gets a subtle `bg-neutral-50/40` tint

**Overlap rendering (CRITICAL):**
Use a **column-split algorithm** — for events that overlap in time:

1. Sort overlapping events by `starts_at` (ascending), then `ends_at` (descending)
2. Group them into "overlap clusters" (transitively-overlapping sets)
3. Within each cluster, assign each event a "column index" using the standard greedy algorithm: scan left-to-right, place each event in the first column whose last event has already ended; if none, add a new column
4. Render: width = `(100% / cluster_width)`, left offset = `(col_index * width)`, with a 2px gutter between columns
5. If cluster_width > 3, collapse to a stacked "+N events" badge with click-to-expand

**All-day band:**
- Lives between day-headers and the time axis, full-width across all 7 columns
- All-day events render as horizontal bars (max 3 stacked, then "+N more")
- Height: 24px per row + 8px padding; band auto-grows up to 3 rows

**Click-to-create:**
- Click empty time slot → open create modal with `starts_at` snapped to that 30-min boundary, duration 30 min
- Click event block → detail
- Right-click time slot → context menu: "Create event" / "Create focus block"

**Drag-to-create (v2 — flag for /sveltekit OQ list):**
Click + drag down to set duration. Probably v2.

### 3.6 `<AgendaView events meetings cursor />`

Linear list, grouped by date headers. Best on mobile; useful on desktop for "what's next".

```
TODAY · Thursday, May 12
┌─────────────────────────────────────────────────────────────────┐
│ 09:30 ─ 10:00  ⬛ [Meeting] Standup · Mobile Squad · 6 attendees │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ 11:00 ─ 12:00  ⬜ [Meeting · M] Steering Committee · Q3 Review   │   ← meetings overlay (dashed border + badge)
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ 13:00 ─ 14:00  ▦ [Focus] Deep work block                        │
└─────────────────────────────────────────────────────────────────┘

TOMORROW · Friday, May 13
┌─────────────────────────────────────────────────────────────────┐
│ ALL DAY  ╱╱╱ [OOO] Joan — Out of office until Monday            │
└─────────────────────────────────────────────────────────────────┘
...

[Load more]
```

**Structure:**
- Date header: `text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400` for "TODAY · Thursday, May 12"
- Group spacing: `space-y-2` within group, `space-y-6` between groups
- Cursor pagination ("Load more") — 50 events per page

**Empty groups:**
Days with zero events are skipped entirely. No "Nothing scheduled" rows that clutter the list.

**Mobile primary:**
Agenda is the default view on `< sm` breakpoint. On mobile, the row layout collapses: time-range moves above the title.

### 3.7 `<RecurrenceEditor bind:rrule />`

The hardest editor in this whole feature. Three rows of controls + a derived natural-language summary.

```
┌── Recurrence ───────────────────────────────────────────────────┐
│                                                                  │
│  Repeats:    ◯ Daily   ◉ Weekly   ◯ Monthly   ◯ Yearly           │
│                                                                  │
│  Every:      [ 2 ] week(s)                                       │
│                                                                  │
│  On:         (M) (T) [W] [T] [F] (S) (S)     ← when Weekly       │
│              ↑ chips: bracketed = selected; unbracketed unselected│
│                                                                  │
│  Ends:       ◉ Never                                             │
│              ◯ After [10] occurrences                            │
│              ◯ On [_____] (date picker)                          │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│  Summary:    Every 2 weeks on Wednesday and Friday, forever.    │
│                                                                  │
│  [Show raw RRULE ▾]   FREQ=WEEKLY;INTERVAL=2;BYDAY=WE,FR        │
└──────────────────────────────────────────────────────────────────┘
```

**Frequency-specific UI:**

| Frequency | Extra controls |
|---|---|
| `Daily` | nothing extra |
| `Weekly` | day-of-week chip row (Mo/Tu/We/Th/Fr/Sa/Su); multi-select |
| `Monthly` | radio: "On day N" (where N = day-of-month from `starts_at`) OR "On the [1st/2nd/3rd/4th/last] [Monday]" |
| `Yearly` | "On [month] [day]" derived from `starts_at`; no extra controls in v1 |

**Day-of-week chips:**
- Unselected: `inline-flex items-center justify-center h-9 w-9 rounded-full border border-neutral-300 bg-white text-xs font-semibold text-neutral-600 hover:border-neutral-400`
- Selected: `bg-neutral-900 text-white border-neutral-900`

**Summary line:**
Reads naturally based on the current state. Examples:
- Daily / every 1: "Every day, forever."
- Weekly / every 2 / Wed,Fri / never: "Every 2 weeks on Wednesday and Friday, forever."
- Monthly / every 1 / day 15 / after 10: "On the 15th of every month, for 10 occurrences."
- Yearly / by date 2026-12-15: "Every year on December 15, until December 15, 2026."

The summary is computed via `$derived` from the structured controls; users see what they're saving.

**Raw RRULE toggle:**
Power users can toggle "Show raw RRULE" — reveals a `text-xs font-mono text-neutral-500` line with the generated RRULE string. **Editable** for v2 (allows `BYSETPOS`, `BYMONTHDAY=-1`, etc.). v1 is **read-only** display only.

**Validation:**
- "After N occurrences": N must be `1–999`; default 10
- "On date": must be ≥ `starts_at`; default `starts_at + 3 months`
- Weekly with zero day-chips selected: implicit "use day-of-week from `starts_at`"

### 3.8 `<TimeInput bind:datetime timezone showOriginalTz />`

Combined date + time picker with timezone awareness.

```
Starts:                                                Ends:
┌─────────────┐ ┌──────────────┐  America/New_York   ┌──────────────┐
│ May 12, 2026│ │ 09:30        │                     │ 10:00        │
└─────────────┘ └──────────────┘                     └──────────────┘
                                  Originally in Europe/London     [Change TZ ▾]
```

**Layout:**
- Two-input row: date input + time input, with `gap-2`
- TZ display to the right: `text-xs text-neutral-500`
- "Originally in {tz}" hint: only when viewer's TZ ≠ `event.timezone` AND the user is *viewing* the event (not creating)
- "[Change TZ ▾]" dropdown on create/edit: opens a search-as-you-type IANA timezone picker

**Time format:**
- 12h for `en`, `es`, `ar`
- 24h for `fr`
- Determined at component-mount via `Intl.DateTimeFormat([locale]).resolvedOptions().hour12`

**Date input:**
- Native `<input type="date">` styled per Teams UI spec input pattern
- Locale-aware via `Intl` for the display label inside the input
- ISO 8601 (`YYYY-MM-DD`) for the underlying value

**Time input:**
- Native `<input type="time">` (covers `HH:MM` 24h; on 12h locales, the browser handles the AM/PM internally)
- Snap-to-30min behavior: when user types `9:17`, on blur we snap to `9:00` or `9:30` (whichever is closer). Configurable per call (`snapMinutes={30|15|null}`).

### 3.9 `<UpdateScopePrompt bind:scope onConfirm />`

Modal that appears **on save** of a recurring event's edit. **Never** shown for non-recurring events.

```
╔═══════════════════════════════════════════════╗
║  Apply changes to:                       (×)  ║
║                                               ║
║  ◯ This event only                            ║
║     Affects only the May 12 occurrence.       ║
║                                               ║
║  ◉ This and future events                     ║
║     Affects May 12 onwards. Past events       ║
║     remain unchanged.                         ║
║                                               ║
║  ◯ All events in the series                   ║
║     Rewrites the entire recurring series,     ║
║     including past events.                    ║
║                                               ║
║                       [Cancel] [Save changes] ║
╚═══════════════════════════════════════════════╝
```

Wraps the shared `<Modal>` from Teams UI spec OQ1 resolution. Default selection: **"This and future events"** (least surprising — past is preserved, future updated).

Sends the chosen scope as `?scope=this|future|all` query parameter on the PATCH/DELETE call.

### 3.10 `<EventForm bind:event mode />`

Single form for create + edit. Kind-aware: changing `kind` adds/removes form sections dynamically.

**Section order:**
1. **Kind selector** (always visible) — 4 large clickable cards in a 2×2 grid
2. **Identity** — Title, Description
3. **When** — TimeInput(starts_at) + TimeInput(ends_at), all-day toggle (hides time inputs)
4. **Recurrence** — toggle "Repeats" → expands `<RecurrenceEditor>`
5. **Attendees** — only when `kind=meeting` — `<UserPicker multiple>` + external-email input
6. **Where** — Location, Meeting link
7. **Reminder** — single picker: "None / 5 min before / 15 min before / 30 min before / 1 hour before / 1 day before / Custom..."
8. **Visibility** — `<VisibilityChip>`-styled radio: Private / Team / Org
9. **Team** — `<TeamPicker>` (re-uses UserPicker pattern), only when visibility=`team` OR explicitly opted in
10. **Dev Fill** button (per CLAUDE.md mandate)
11. Cancel + Create / Save Changes

**Kind-aware hiding:**

| Section | meeting | focus | out_of_office | reminder |
|---|---|---|---|---|
| Kind selector | ✓ | ✓ | ✓ | ✓ |
| Identity | ✓ | ✓ | ✓ | ✓ |
| When | ✓ | ✓ | ✓ | starts_at only (no ends_at) |
| Recurrence | ✓ | ✓ | ✓ | ✓ |
| Attendees | ✓ | ✗ | ✗ | ✗ |
| Where | ✓ | ✗ (no location for focus) | ✓ (just location, not link) | ✗ |
| Reminder | ✓ | ✓ | ✗ (OOO doesn't ping) | ✓ |
| Visibility | private/team default | team default | team default | private default |

**Conflict warning (per design §11):**
After fields are filled enough to compute, a soft warning appears inline above the submit button if the event overlaps an existing event of the creator's:

```
⚠ This overlaps with "Steering Committee" at 09:30. You can still save.
```

Hidden for `kind=reminder` (zero-duration).

### 3.11 `<MeetingOverlayBadge />`

Small absolute-positioned marker. Top-right of any `EventCell` rendering a row with `source: "meeting"`.

```
<span class="absolute top-1 right-1 h-4 w-4 inline-flex items-center
             justify-center rounded text-[9px] font-bold
             bg-neutral-200 text-neutral-700"
      aria-label="From Meetings (read-only here)">M</span>
```

Plus the parent `EventCell` gets `border-dashed` instead of `border-solid`.

---

## 4. Routes

For each route: ASCII layout sketch, data flow, empty / loading / error states, mobile collapse.

### 4.1 `/calendar` — Main page

```
─────────────────────────────────────────────────────────────────────
WORKSPACE
Calendar                                                  [+ New event]
Your events, scheduled meetings, and team availability.

┌── Toolbar (sticky on scroll) ───────────────────────────────────┐
│  [‹] Thursday, May 12, 2026 [›]  Today    Month  ▲Week  Agenda │
│                                                                 │
│  Filters:  [All kinds ▾] [Team: any ▾]   ✓ Meetings overlay    │
└─────────────────────────────────────────────────────────────────┘

┌── Calendar canvas (big card) ──────────────────────────────────┐
│  <MonthView> | <WeekView> | <AgendaView>                       │
│  (one rendered at a time based on view selector)               │
└────────────────────────────────────────────────────────────────┘
```

**Toolbar details:**
- Date navigator (`< Today >`) — controls anchored date
  - Month view: prev/next month
  - Week view: prev/next week
  - Agenda view: prev/next page (less common navigation)
- **"Today" pill button**: `rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-semibold hover:border-neutral-400`. Hidden when anchor is today.
- **View switcher**: 3-segment toggle:
  - Inactive: `bg-white text-neutral-600 border-neutral-300`
  - Active: `bg-neutral-900 text-white border-neutral-900`
- **Filters row**:
  - "All kinds" dropdown → multi-select kind toggles
  - "Team" dropdown → searchable team picker (uses `<UserPicker>` pattern but for teams)
  - "Meetings overlay" checkbox: ON by default; toggling OFF hides all `source:meeting` rows

**Empty states:**
- **No events at all (new user)** — full-canvas dashed empty card: "Your calendar is empty" + "Create your first event" CTA + "Subscribe to your iCal feed in [Settings →]" link
- **Empty week** — show the canvas as normal (empty time slots are fine); no special empty state
- **Filter matches nothing** — keep grid visible, show inline pill above: "No events match this filter — [Clear filters]"

**Loading:**
- Initial: centered spinner `py-28`
- View-switch / date-change: skeleton placeholders inside the cells (`animate-pulse bg-neutral-100` rectangles) for 200ms then fade in
- Meeting overlay loading separately: small loading dot in the "Meetings overlay" checkbox label until done

**Error:**
- Events failed: `<DataStateBanner>` rose-tinted card with retry
- Meetings overlay failed (but events succeeded): inline yellow pill at the top of the canvas: "Meetings couldn't load — [Retry]". Canvas keeps showing native events.

**Mobile:**
- Toolbar collapses: view switcher becomes a tab strip across the top of the canvas, filters move to a "Filters ▾" dropdown
- Default view: Agenda
- "+ New event" → floating action button (FAB) bottom-right, `fixed bottom-6 right-6 h-14 w-14 rounded-full bg-neutral-900 text-white shadow-lg`

### 4.2 `/calendar/events/new` — Create wizard

Single-page form, sections from `<EventForm>` §3.10.

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Calendar
New event                                                  [Cancel]

┌── Section 1 — Type ────────────────────────────────────────────┐
│  What kind of event is this?                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │ 📅          │ │ 🧠          │ │ ✈️          │ │ 🔔          │   │
│  │ Meeting    │ │ Focus      │ │ Out of     │ │ Reminder   │   │
│  │            │ │ block      │ │ office     │ │            │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  Selected: Meeting                                              │
└─────────────────────────────────────────────────────────────────┘

┌── Section 2 — Identity ────────────────────────────────────────┐
│  Title *                                                        │
│  [_______________________________________________]              │
│                                                                 │
│  Description (optional)                                         │
│  [_______________________________________________]              │
│  [_______________________________________________]              │
└─────────────────────────────────────────────────────────────────┘

┌── Section 3 — When ────────────────────────────────────────────┐
│  ☐ All-day                                                      │
│                                                                 │
│  Starts:   [May 12, 2026] [09:30]   America/New_York            │
│  Ends:     [May 12, 2026] [10:00]                               │
│                                                                 │
│  ☐ Repeats              ← toggle reveals RecurrenceEditor       │
└─────────────────────────────────────────────────────────────────┘

(Section 4: Attendees — only when kind=meeting)
(Section 5: Where — location + meeting link)
(Section 6: Reminder)
(Section 7: Visibility)
(Section 8: Team)

⚠ This overlaps with "Steering Committee" at 09:30. You can still save.

[Dev Fill]                              [Cancel] [Create event]
```

**Visibility radio:**
```
◉ Private        Only you and attendees see this event.
◯ Team           Members of [the selected team] can see this event.
◯ Org-wide       Anyone in your organization can see this event.
```

**Validation:**
- Title required (max 200), trimmed
- starts_at required
- ends_at required unless `kind=reminder` (UI hides the field)
- If visibility=`team` and no team selected: inline `text-xs text-rose-600` error: "Pick a team or change visibility to Private."
- If recurrence is on, RRULE must validate via `dateutil.rrule.rrulestr` (server-side validator returns 400 with a friendly message; client shows inline)

**Submit:**
- Success: route to `/calendar/events/{id}` with toast "Event created"
- Error: toast with the API message; field-level errors inline

**Mobile:**
- Sections stack normally; kind selector 2×2 grid stays
- Dev Fill / Cancel / Create form a sticky bottom bar

### 4.3 `/calendar/events/[id]` — Detail

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Calendar › Standup

┌── Header card ─────────────────────────────────────────────────┐
│ [Meeting]  [Private]                                       ⋯  │
│ Standup                                                        │
│ Mobile Squad daily standup. 15 min, focused on blockers.      │
│                                                                │
│ 🗓 Wednesday, May 12, 2026 · 09:30–10:00 EST                   │
│ ↻ Every weekday, until further notice                          │
│ 📍 Conference Room 3 · 🔗 zoom.us/j/...                        │
│                                                                │
│ [Joined ▾]   ← member, or [Edit] for creator                   │
└────────────────────────────────────────────────────────────────┘

┌── 2-column grid (lg+) ─────────────────────────────────────────┐
│ ┌── Attendees (col-span-2) ──┐ ┌── Reminder ───────────────┐  │
│ │ Attendees · 6              │ │ 15 minutes before          │  │
│ │ ── MemberRow × 6 ──        │ │ [Edit reminder]            │  │
│ │ [+ Add attendees]          │ └────────────────────────────┘  │
│ └────────────────────────────┘                                 │
│                                ┌── Recurrence ─────────────┐   │
│                                │ Daily, weekdays only       │   │
│                                │ Started May 4, 2026        │   │
│                                │ → 4 overrides              │   │
│                                │ [Manage occurrences →]      │   │
│                                └────────────────────────────┘   │
│                                                                │
│                                ┌── Team ───────────────────┐   │
│                                │ 📐 Mobile Squad           │   │
│                                │ → Open team               │   │
│                                └────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

**Header card details:**
- Pill row: KindChip + VisibilityChip + ellipsis menu
- Title: text-2xl font-bold tracking-wide
- Description: text-sm text-neutral-600
- Meta block: 3 lines max (date/time, recurrence summary if recurring, location/link)
- Action button:
  - Creator: `[Edit]` filled CTA
  - Attendee: `[Joined ▾]` with menu: Remove me from event, Notification prefs
  - Non-attendee (visible per visibility): no action button, just "i Read-only" hint

**Overrides panel (only for recurring events):**
- Shows count of overrides
- "Manage occurrences" → opens a popover/modal listing all overrides with edit/restore controls
- **Clean up orphans** CTA appears in `text-xs text-rose-600` if any overrides are orphaned (per design EC4)

**Empty states:**
- No attendees (creator-only meeting): inline "No attendees yet" with "+ Add attendees" CTA

**Error / 404:**
- Per design rule: **secret event for non-permitted user → 404, never 403** (never reveal existence)

**Mobile:**
- Grid collapses to single column: attendees → recurrence → team → reminder

### 4.4 `/calendar/events/[id]/edit` — Edit

Same form as `/calendar/events/new` (§4.2) but pre-filled. Two differences:

1. **`<UpdateScopePrompt>` modal** triggered on save **only when the event has `recurrence_rule`** (per critical UX rule)
2. **"Kind selector" is disabled / read-only** — changing the kind invalidates the form structure; require delete + recreate (or expose a "Convert..." button as v2)
3. Header text: "Edit event" instead of "New event"

### 4.5 User-settings extension (`/user-settings/calendar-scheduling`)

Extend the existing page with two new sections:

```
┌── Default reminder ─────────────────────────────────────────────┐
│  When you create a new event, this default applies              │
│  unless you set a per-event override.                           │
│                                                                  │
│  ◯ None    ◉ 15 minutes before    ◯ 30 minutes before           │
│  ◯ 1 hour before    ◯ 1 day before    ◯ Custom: [____] minutes  │
└──────────────────────────────────────────────────────────────────┘

┌── iCal feed ────────────────────────────────────────────────────┐
│  Subscribe to your developerOS calendar in Google Calendar,     │
│  Outlook, or Apple Calendar.                                     │
│                                                                  │
│  Your feed URL:                                                  │
│  ┌─────────────────────────────────────────────────┐ ┌────────┐│
│  │ https://app.developeros.pro/api/calendar/feed/  │ │ Copy   ││
│  │ ?token=abc123…                                   │ │        ││
│  └─────────────────────────────────────────────────┘ └────────┘│
│                                                                  │
│  [Rotate token]   ← regenerates the URL; old token invalidates  │
│                                                                  │
│  💡 Calendar clients typically refresh every 30 min — 24 hours. │
└──────────────────────────────────────────────────────────────────┘
```

**Rotate token interaction:**
- Click "Rotate token" → opens a confirm modal: "Rotate iCal feed token? Any existing calendar subscriptions will stop syncing until you re-subscribe with the new URL."
- On confirm: POST `/api/calendar/feed/rotate-token/`, replace the URL in-place, copy-to-clipboard the new URL automatically.

---

## 5. Mobile considerations

Calendar is genuinely harder than Teams to make mobile-friendly. Specific rules:

- **Default view: Agenda** on `< sm` (640px) breakpoint
- **Month view on mobile**: cells shrink to ~38px wide, only render single dot per timed event (no titles), max 3 dots + "+N"
- **Week view on mobile**: switch to **1-day-at-a-time** mode (day column = full width). Header gets prev/next day buttons. Sometimes called "Day view" — we don't add a separate Day view, just a responsive collapse of Week.
- **Agenda is the touch-friendly winner**: full-width rows with 44px+ touch targets
- **+ New event** → FAB bottom-right on small screens
- **Modal sheets** instead of centered modals on `< sm` — same pattern as Teams
- **No drag-to-resize / drag-to-move events on mobile** (v1) — touch UI is unreliable; click → edit instead

---

## 6. Empty / loading / error / interaction patterns

### 6.1 Event detail: modal vs page?

**Decision:** route-based (`/calendar/events/[id]`) as the canonical detail. Clicking an event in any view opens a quick-preview popover (similar to Google Calendar's click-popup) anchored to the event:

```
┌─────────────────────────────────────────┐
│ Standup                          [×]    │
│ [Meeting] [Private]                     │
│ 🗓 Today · 09:30–10:00 EST              │
│ 📍 Conference Room 3                    │
│ 👥 6 attendees                          │
│                                          │
│ [Open full detail →]                    │
└─────────────────────────────────────────┘
```

The popover is enough for 90% of "what's this event?" interactions. Click "Open full detail" or any link inside it routes to the detail page.

### 6.2 State cheat-sheet (inherited + extended)

| State | Pattern |
|---|---|
| **Loading (initial)** | Centered `animate-spin` `h-7 w-7` inside `py-28` |
| **Loading (view-switch)** | Skeleton rectangles in cells, 200ms fade |
| **Empty (filter)** | Inline pill at canvas top: "No events match — Clear filters" |
| **Empty (no events at all)** | Full-canvas dashed empty card with primary CTA |
| **Error** | `<DataStateBanner>` rose-tinted card with retry |
| **404** | Neutral-tinted card — never reveals private/secret existence |
| **Optimistic in-flight** | Event block at 60% opacity until server confirms |
| **Conflict warning (create form)** | Inline yellow box above submit — soft, not blocking |
| **Orphan override** | Red-tint warning inside the Manage Occurrences modal + "Clean up orphans" CTA |

---

## 7. Accessibility

WCAG 2.2 AA bar, plus specific calendar accommodations:

### Keyboard navigation

- **Tab order through the toolbar:** view switcher → date nav → filters → + New event
- **Inside Month view:**
  - `Arrow Up/Down/Left/Right`: move between cells
  - `Enter`: open the focused cell's first event detail (or create modal if cell is empty)
  - `Page Up/Page Down`: prev/next month
  - `T`: jump to today
- **Inside Week view:**
  - `Arrow Up/Down`: navigate by hour within current day column
  - `Arrow Left/Right`: navigate between day columns
  - `Enter`: open event at focused position
- **Inside Agenda:**
  - `Arrow Up/Down`: navigate between rows
  - `Enter`: open event
- **Inside any view:** `Esc` closes the popover / modal

Implementation hint: each cell / event block gets `tabindex="0"`; arrow keys handled at the parent view component.

### Screen reader

- Every event block gets `role="button"` + `aria-label` composed as:
  - "{kind}, {title}, from {start} to {end}, in {location}" for blocks
  - "{kind} reminder, {title}, at {time}" for reminders
  - "{kind}, {title}, all day on {date}" for all-day
- Recurring event additional context: "...repeats {summary}"
- Meetings overlay: "...from Meetings, read-only here, opens in Meetings app on activation"
- Cancelled: "...cancelled" appended

### Color & motion

- All 4 kind treatments differ in **shape and pattern**, not just color — color-blind safe
- Meetings overlay distinguished by **dashed border** (shape) + **M badge** (text), not by hue
- `prefers-reduced-motion`: spinner doesn't spin, view transitions become instant (no fade)

### Focus management

- Opening a popover moves focus into it (first interactive element)
- Closing returns focus to the originator
- Update-scope modal: focus on the default radio option

---

## 8. i18n

Keys all under `workspace.calendar.*` namespace, contributed in en/fr/es/ar.

Core keys (starter set — `/sveltekit` will round these out):

```
workspace.calendar.title                  → "Calendar"
workspace.calendar.eyebrow                → "Workspace"
workspace.calendar.helper                 → "Your events, scheduled meetings, and team availability."
workspace.calendar.new_event              → "New event"
workspace.calendar.views.month            → "Month"
workspace.calendar.views.week             → "Week"
workspace.calendar.views.agenda           → "Agenda"
workspace.calendar.today                  → "Today"
workspace.calendar.kind.meeting           → "Meeting"
workspace.calendar.kind.focus             → "Focus block"
workspace.calendar.kind.out_of_office     → "Out of office"
workspace.calendar.kind.reminder          → "Reminder"
workspace.calendar.visibility.private     → "Private"
workspace.calendar.visibility.team        → "Team"
workspace.calendar.visibility.org         → "Org-wide"
workspace.calendar.form.title             → "Title"
workspace.calendar.form.description       → "Description (optional)"
workspace.calendar.form.starts_at         → "Starts"
workspace.calendar.form.ends_at           → "Ends"
workspace.calendar.form.all_day           → "All day"
workspace.calendar.form.repeats           → "Repeats"
workspace.calendar.form.attendees         → "Attendees"
workspace.calendar.form.location          → "Location"
workspace.calendar.form.meeting_link      → "Meeting link"
workspace.calendar.form.reminder          → "Reminder"
workspace.calendar.form.visibility        → "Visibility"
workspace.calendar.form.team              → "Team"
workspace.calendar.rrule.repeats          → "Repeats"
workspace.calendar.rrule.every            → "Every"
workspace.calendar.rrule.ends             → "Ends"
workspace.calendar.rrule.ends.never       → "Never"
workspace.calendar.rrule.ends.after       → "After {n} occurrences"
workspace.calendar.rrule.ends.on          → "On {date}"
workspace.calendar.rrule.frequency.daily   → "Daily"
workspace.calendar.rrule.frequency.weekly  → "Weekly"
workspace.calendar.rrule.frequency.monthly → "Monthly"
workspace.calendar.rrule.frequency.yearly  → "Yearly"
workspace.calendar.scope.this             → "This event only"
workspace.calendar.scope.future           → "This and future events"
workspace.calendar.scope.all              → "All events in the series"
workspace.calendar.conflict_warning       → "This overlaps with \"{other}\" at {time}. You can still save."
workspace.calendar.empty.no_events        → "Your calendar is empty"
workspace.calendar.empty.no_events.cta    → "Create your first event"
workspace.calendar.error.load             → "Couldn't load events"
workspace.calendar.error.overlay          → "Meetings couldn't load"
workspace.calendar.reminder_default       → "Default reminder"
workspace.calendar.ical.title             → "iCal feed"
workspace.calendar.ical.helper            → "Subscribe to your developerOS calendar in Google Calendar, Outlook, or Apple Calendar."
workspace.calendar.ical.url_label         → "Your feed URL"
workspace.calendar.ical.copy              → "Copy"
workspace.calendar.ical.rotate            → "Rotate token"
workspace.calendar.ical.rotate_confirm    → "Rotate iCal feed token? Any existing calendar subscriptions will stop syncing until you re-subscribe."
```

**Day/month names:** NEVER hardcode. Use `Intl.DateTimeFormat([locale], { weekday: "short" })` and friends.

**RTL note:** Arabic flips horizontal layout. The Month grid's left-to-right week order becomes right-to-left in Arabic. Use Tailwind `rtl:` variants on grid templates. Day axis (Mon→Sun in en, Sat→Fri in ar) needs locale-aware ordering — read `Intl.Locale(locale).weekInfo.firstDay`.

**Translation effort estimate:** ~60 keys × 4 locales = 240 strings; significantly easier than Teams because most are short.

---

## 9. Open questions for `/sveltekit` (resolve at implementation time)

1. **Recurrence editor library** — should we use an existing Svelte library for RRULE editing, or build from scratch? My read: **build from scratch**. Existing libs (rrule-generator, etc.) are heavy and not Svelte-5-native. The §3.7 spec is detailed enough to implement in ~300 lines.
2. **Date / time picker** — native `<input type="date">` and `<input type="time">` are inconsistent across browsers. Consider a small custom picker (or `bits-ui`'s DateField if it ships Svelte-5-compatible by build time). My read for v1: **native inputs**. Polish in v2.
3. **TZ picker** — search-as-you-type IANA list (`Intl.supportedValuesOf("timeZone")` returns ~400). Probably a virtualized dropdown. My read: **use bits-ui Combobox** if available; otherwise build minimal one.
4. **Drag-to-create / drag-to-resize in Week view** — explicitly deferred per spec. Confirm not implemented.
5. **Quick-preview popover (§6.1)** — needs anchor positioning. My read: **use `floating-ui` if it's already in package.json**; else `position: absolute` + click-outside.
6. **Recurrence summary line localisation** — natural-language summary needs phrase templates per locale. Suggest building a `recurrenceSummary(rrule, locale, t)` function with locale-specific templates. ~20 templates per locale × 4 locales = 80 strings.
7. **Working-hours defaults from user-settings** — confirm the existing `user-settings/calendar-scheduling` payload includes `working_hours_start` / `_end`. If not, default to 07:00 / 20:00 and add fields in `/django-pro` if missing.

---

## Sign-off

This spec is the visual + interaction source of truth for Calendar. Implementation (`/sveltekit`) should produce:

- ~10 components in `client/src/lib/components/calendar/`
- 4 routes in `client/src/routes/calendar/`
- 2 new sections in `client/src/routes/user-settings/calendar-scheduling/+page.svelte`
- 1 event-kind static map in `client/src/lib/components/calendar/event-kinds.ts`
- ~60 i18n keys × 4 locales

Anything that contradicts this spec should bounce back here for resolution rather than getting decided silently in code.
