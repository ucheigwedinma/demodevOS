# Workspace → Teams — UI/UX Spec

**Companion to:** [`workspace-teams-design.md`](./workspace-teams-design.md)
**Status:** Locked, ready for `/sveltekit` implementation
**Audience:** the engineer (or skill) writing the Svelte components

This is the **visual + interaction** spec. The model, API, permissions, and audit decisions live in the companion design doc. **Don't duplicate** — refer back to it for anything not visual.

---

## 1. Design tokens

### 1.1 Type scale (Raleway, everywhere)

| Use | Tailwind classes | Pixel size |
|---|---|---|
| Page header (h1) | `text-2xl font-bold tracking-wide text-neutral-800` | 24/32 |
| Section header (h2) | `text-lg font-semibold text-neutral-950` | 18/28 |
| Eyebrow above page header | `text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600` | 11 |
| Eyebrow above panel | `text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400` | 11 |
| Subhead inside panel | `text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400` | 12 |
| Body | `text-sm text-neutral-700` | 14/22 |
| Body secondary | `text-sm text-neutral-500` | 14/22 |
| Helper / footnote | `text-xs text-neutral-500` | 12/18 |
| Stat value | `text-2xl font-semibold text-neutral-950 tabular-nums` | 24 |
| Stat label | `text-[10px] uppercase tracking-wider text-neutral-500` | 10 |
| Chip | `text-[10px] font-semibold` or `text-xs font-semibold` | 10 / 12 |

The codebase already loads Raleway globally; no per-component font setting needed.

### 1.2 Surface tokens

| Surface | Classes | When |
|---|---|---|
| Page background | `bg-neutral-50` | inherited from layout |
| Big card | `rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm` | the page-level wrapper card (e.g. directory list, members list) |
| Mid card | `rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5` | filter shelf, members panel, danger-zone block |
| Inset block | `rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3` | input controls, stat chips |
| Empty state card | `rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center` | "no teams yet" |
| Error state card | `rounded-2xl border border-rose-200 bg-rose-50 px-6 py-8 text-center` | already used in CRM via `<DataStateBanner>` — reuse it |

### 1.3 Spacing rhythm

- Outer page gutter is set by the layout — components don't add their own.
- Vertical rhythm between sections inside a page: `space-y-4` (compact) or `space-y-6` (more air on detail/edit pages).
- Inside a card: header → body separation is `mt-4` after the header block.
- Field-to-field in a form: `space-y-5` (matches the support-desk ticket form).

### 1.4 Radii

- `rounded-full` → chips, the round-icon avatar buttons, single-stat pills
- `rounded-lg` → small action buttons, secondary CTAs
- `rounded-xl` → mid-size buttons, the TeamAvatar **square** disc (not full — see §2.1)
- `rounded-2xl` → inputs, mid cards, member rows
- `rounded-3xl` → page-level cards (matches support-desk and risk-alerts)

### 1.5 Focus + interaction

- Focus ring: `focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10`
- Hover on bordered button: `hover:border-neutral-400`
- Hover on filled CTA: `hover:bg-neutral-800` (CTAs are `bg-neutral-900 text-white`)
- Disabled: `opacity-60 cursor-not-allowed`
- Loading spinner: `h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900` (already a pattern in risk-alerts)

### 1.6 Team color palette (the only colour on the page)

10 tokens. Each token resolves to a fixed Tailwind class trio (no dynamic class names — the static-scanner rule from CLAUDE.md). Implemented as a static lookup map in `team-colors.ts`:

| Token | Avatar disc bg | Chip bg | Chip text | Chip border |
|---|---|---|---|---|
| `rose` | `bg-rose-500` | `bg-rose-100` | `text-rose-700` | `border-rose-200` |
| `orange` | `bg-orange-500` | `bg-orange-100` | `text-orange-700` | `border-orange-200` |
| `amber` | `bg-amber-500` | `bg-amber-100` | `text-amber-700` | `border-amber-200` |
| `lime` | `bg-lime-600` | `bg-lime-100` | `text-lime-700` | `border-lime-200` |
| `emerald` | `bg-emerald-500` | `bg-emerald-100` | `text-emerald-700` | `border-emerald-200` |
| `teal` | `bg-teal-500` | `bg-teal-100` | `text-teal-700` | `border-teal-200` |
| `sky` | `bg-sky-500` | `bg-sky-100` | `text-sky-700` | `border-sky-200` |
| `indigo` | `bg-indigo-500` | `bg-indigo-100` | `text-indigo-700` | `border-indigo-200` |
| `violet` | `bg-violet-500` | `bg-violet-100` | `text-violet-700` | `border-violet-200` |
| `fuchsia` | `bg-fuchsia-500` | `bg-fuchsia-100` | `text-fuchsia-700` | `border-fuchsia-200` |

**Default color** (when none picked) = `sky`.

**Avatar contrast:** all 10 disc backgrounds carry the chosen emoji at white-friendly luminance. The emoji itself is a Unicode glyph, so no foreground color is set — it inherits the system emoji rendering.

**Chip contrast:** every `bg-{token}-100 / text-{token}-700` pair clears WCAG AA (4.5:1) for normal text. Verified against Tailwind's published palette.

**Color-blindness note:** the team color is *identity*, not *meaning*. Name + emoji are the primary identifiers; color is decorative. No state (active, archived, etc.) is encoded in the team color.

### 1.7 Iconography

Inline SVG, heroicons-outline shape language, `stroke-width="1.5"` (1.75 for stat-card icons), `fill="none"`, `stroke="currentColor"`. Default size `h-5 w-5`. No icon library imported.

Reusable inline SVGs needed for this feature: globe (public), lock (private), eye-slash (secret), users (members), folder (project linked), bell + bell-slash (notification toggle), trash, archive, ellipsis-v (row menu), check, plus, search, x.

---

## 2. Components

### 2.1 `<TeamAvatar emoji color size />`

Square disc with rounded corners (Linear-style), color from §1.6.

```
Props:
  emoji: string (default "👥")
  color: ColorToken (default "sky")
  size?: "sm" | "md" | "lg" | "xl"  (default "md")

Sizes:
  sm  → h-7  w-7  text-base       (28px) — used inline in chips
  md  → h-10 w-10 text-xl         (40px) — used in TeamCard, MemberRow's team chip
  lg  → h-14 w-14 text-3xl        (56px) — used in detail page header
  xl  → h-20 w-20 text-5xl        (80px) — used in create-wizard preview
```

```
Outer:  inline-flex items-center justify-center
        rounded-xl shrink-0
        {bg-{color}-500} (looked up via static map)
Inner:  emoji glyph centered, no extra wrapping
```

A11y: `<span role="img" aria-label="{teamName} icon">{emoji}</span>` when standalone; `aria-hidden="true"` when paired with the team name in the same focusable element.

### 2.2 `<TeamCard team />`

Directory cell. Used in `/teams` directory grid.

```
┌──────────────────────────────────────────────────────┐
│  ┌──┐                                          ┌──┐  │
│  │📐│  Mobile Launch Squad                     │•••│  │
│  └──┘  Cross-functional release team             └──┘  │
│                                                       │
│  [Initiative]  [🌐 Public]      14 members  · 3 tickets│
└──────────────────────────────────────────────────────┘
```

Structure:
- Outer: `group relative rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:border-neutral-400 hover:shadow`
- Top row: TeamAvatar (md) + name + description (truncate to 1 line, `line-clamp-1 text-sm text-neutral-500`); name is `text-base font-semibold text-neutral-900`
- Bottom row: chips on the left, counts on the right
  - **Purpose chip**: `rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600` — purpose label localised
  - **Visibility chip**: same pill shape, with the visibility icon + label (globe/lock/eye-slash). Secret teams display as the lock+strikethrough variant if a non-member somehow renders it (defensive — should be filtered out by API).
  - **Counts**: `text-xs text-neutral-500 tabular-nums` — `{n} members · {m} tickets` (i18n keys: `workspace.teams.member_count`, `workspace.teams.ticket_count`)
- Whole card is a `<a href="/teams/{id}">` so it's keyboard-navigable. Ellipsis menu in the top right is a separate button (`<button class="absolute right-3 top-3">`) that stops propagation.
- Archived state: add `opacity-70 grayscale-[0.4]` and a small "Archived" pill in the top-right (replacing the ellipsis menu for non-admins).

### 2.3 `<MemberRow user role amIOwnerOrAdmin />`

```
┌────────────────────────────────────────────────────────────┐
│  ⭕  Joan Reyes                              [Admin ▾] •••  │
│      joan@example.com                                      │
└────────────────────────────────────────────────────────────┘
```

Structure:
- Outer: `flex items-center gap-3 rounded-2xl border border-neutral-200 bg-white px-4 py-3`
- Avatar: a placeholder circle from initials (`bg-neutral-200 text-neutral-700`, `h-10 w-10 rounded-full`). No image upload — initials only.
- Name + email stack: `text-sm font-semibold text-neutral-900` / `text-xs text-neutral-500`
- Role chip on the right: see §2.5 RoleSelect — when not editable, render as a static chip
- Ellipsis menu (only when `amIOwnerOrAdmin`): rendered with the same `toggleMenu` pattern from risk-alerts. Menu items: Change role, Transfer ownership (owner-only, member-only target), Remove from team, Resend digest
- The current user's row gets a tiny `(you)` chip after their name in `text-[10px] uppercase tracking-wider text-neutral-400`

### 2.4 `<UserPicker multiple value onChange />`

Async user search. New, will be reused elsewhere. `<input>` with debounced search hitting `/api/accounts/users/?q=…`, dropdown of results with avatar + name + email + role-in-org subtitle.

```
┌────────────────────────────────────────────────────────────┐
│  Add members            ┌──────────────────────────────┐   │
│                         │ search org...                 │   │
│                         └──────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────┐    │
│  │ ⭕ Joan Reyes        joan@…   • Project Manager     │ ←  │
│  │ ⭕ Marco Levin       marco@…  • Architect           │    │
│  │ ⭕ Aisha Bello       aisha@…  • Senior Engineer     │    │
│  └────────────────────────────────────────────────────┘    │
│  Selected:  [⭕ Joan ×]  [⭕ Marco ×]                       │
└────────────────────────────────────────────────────────────┘
```

- Input: `rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3`
- Dropdown: `absolute z-30 mt-1 max-h-72 overflow-auto rounded-2xl border border-neutral-200 bg-white shadow-md`
- Result row: `flex items-center gap-3 px-4 py-2 hover:bg-neutral-50`; arrow keys navigate, Enter selects, Esc closes
- Selected pills: `inline-flex items-center gap-1 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-700`
- Empty state: "Type to search teammates" → "No matches" after a debounced query
- Loading: subtle pulse on the dropdown frame, no full-page spinner
- A11y: `role="combobox"`, `aria-expanded`, `aria-activedescendant` per WAI-ARIA Combobox 1.2 pattern. Tested with VoiceOver / NVDA in mind.

### 2.5 `<RoleSelect role canEdit canPromoteToOwner />`

Renders as a chip. Click opens a small popover with the four roles.

```
[Admin ▾]      ←  closed state
                 (hover/focus shows caret)
                 click ↓
┌────────────┐
│ Owner    ✓ │
│ Admin      │
│ Member     │
│ Guest      │
└────────────┘
```

- Closed-state chip: `inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold` with role-specific styling:
  - **owner**: `border-amber-200 bg-amber-50 text-amber-700` (a soft warm chip — leadership signal, no urgency)
  - **admin**: `border-neutral-300 bg-neutral-100 text-neutral-700`
  - **member**: `border-neutral-200 bg-white text-neutral-600`
  - **guest**: `border-dashed border-neutral-300 bg-neutral-50 text-neutral-500` (the dashed border signals "limited access")
- When `canEdit=false`: render the chip without caret, `cursor-default`
- When opening popover: enforce role rules client-side (admin cannot demote owner; owner option only shown when `canPromoteToOwner=true`, which means *this is the owner row* AND we're transferring)
- A11y: `role="button" aria-haspopup="listbox" aria-expanded`. Popover: `role="listbox"`, options `role="option" aria-selected`.

---

## 3. Routes

For each route: ASCII layout sketch, data flow, empty state, error state, loading state, mobile collapse.

### 3.1 `/teams` — Directory

```
─────────────────────────────────────────────────────────────────────
WORKSPACE
Teams                                              [+ New team]
Lightweight teams for project pods, initiatives, and guilds.

┌── filter shelf (mid card) ─────────────────────────────────────┐
│  [My teams] [All] [Archived]    [All purposes ▾]   ┌──────────┐│
│                                                    │🔍 search ││
│                                                    └──────────┘│
└────────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ TeamCard        │  │ TeamCard        │  │ TeamCard        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
┌─────────────────┐  ┌─────────────────┐
│ TeamCard        │  │ TeamCard        │
└─────────────────┘  └─────────────────┘

                     [Load more]   showing 25 of 47
```

- **Header:** eyebrow "Workspace" (text-blue-600 — same as risk-alerts), title "Teams", helper text. Right side: solid `bg-neutral-900 text-white rounded-xl px-4 py-2 text-sm font-semibold` "+ New team" button.
- **Filter shelf:** mid card. Three filter chip groups separated by `gap-3`.
  - Tab chips: pill buttons with active-state `bg-neutral-900 text-white` and inactive `border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400`. **Default tab: "My teams"** (calls `/api/workspace/teams/?mine=true`).
  - Purpose dropdown: `<select>` styled like the existing support-desk filter selects.
  - Search input: 🔍 icon + debounced text input, fires `?q=…` after 250ms.
- **Grid:** `grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` — 4 columns on wide, 3 on lg, 2 on sm, 1 on mobile.
- **Pagination:** Cursor-based "Load more" button at the bottom (matches the load-more-button pattern, not numeric pagination — feels lighter for this kind of directory).
- **Empty states:**
  - **No teams yet (My tab, user is in zero teams):** dashed-border empty card with "👥" emoji + "You're not in any teams yet" + helper "Browse all teams or create your own" + two CTAs: "Browse all" (text-only link), "+ New team" (filled button).
  - **No teams in this org (All tab, zero teams):** "No teams yet" + "Be the first to create a team" + "+ New team" CTA.
  - **Search returns nothing:** "No teams match \"{query}\"" + "Clear search" link.
  - **Archived tab empty:** "No archived teams" — flat text only, no CTA.
- **Error state:** `<DataStateBanner>` (existing component) with rose-tinted card, "Couldn't load teams" + retry button.
- **Loading:** the existing animate-spin pattern (h-7 w-7 spinner) centered in `py-28`.
- **Mobile:** filter shelf collapses to a sticky bar at the top; chips wrap; search input takes full width below the chips. Grid drops to 1 column. The "+ New team" button moves below the title.

### 3.2 `/teams/new` — Create wizard (single page)

A long-form, single-page create flow (not a modal — too many decisions for a modal). Sections separated visually:

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Teams
New team                                                   [Cancel]

┌── Section 1 of 3 — Identity ───────────────────────────────────┐
│  Name *                                                         │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ e.g. Mobile Launch Squad                                   ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Description (optional)                                         │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ What does this team do?                                    ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Avatar                                                         │
│  ┌──────────┐ ┌──────────────────────────────────────────────┐ │
│  │  [Big    │ │  emoji picker grid (8x4)                     │ │
│  │  preview │ │   👥 🚀 ⚡️ 🎯 🛠️ 🌱 📐 💡                  │ │
│  │  TeamAv. │ │   ...                                         │ │
│  │  xl size]│ └──────────────────────────────────────────────┘ │
│  └──────────┘                                                   │
│                                                                 │
│             colour swatches (10 dots in a row)                  │
│             ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤                           │
└─────────────────────────────────────────────────────────────────┘

┌── Section 2 of 3 — Purpose ───────────────────────────────────┐
│  What kind of team is this?                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │  Project   │ │ Initiative │ │   Guild    │                 │
│  │  📐         │ │     🎯      │ │     🌱      │                 │
│  │  Tied to a │ │ Cross-fn   │ │ Voluntary  │                 │
│  │  delivery  │ │ task force │ │ community  │                 │
│  └────────────┘ └────────────┘ └────────────┘                 │
│                                                                 │
│  (only when "Project" selected)                                │
│  Linked project                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ ▾ Choose a project                                         ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌── Section 3 of 3 — Visibility ────────────────────────────────┐
│  Who can find and join this team?                              │
│  ◯ 🌐 Public — anyone in the org can find and join            │
│  ◯ 🔒 Private — discoverable, join requires approval          │
│  ◯ 👁‍🗨 Secret — hidden from the directory; invite-only        │
└─────────────────────────────────────────────────────────────────┘

[Dev Fill]                                  [Cancel] [Create team]
```

- **Single page**, not stepped — every field visible at once. The "Section N of 3" labels are visual structure, not a wizard. Submit button at the bottom.
- **Purpose cards:** big tap targets, three-up grid on desktop, stacked on mobile. Selected state: `border-neutral-900 ring-2 ring-neutral-900/10 bg-neutral-50`. Unselected: `border-neutral-200 bg-white hover:border-neutral-400`.
- **Project picker:** appears with `transition-all` *only* when purpose=project. Uses a simple `<select>` with org's active projects.
- **Visibility:** native radio buttons styled with the existing pattern (custom `appearance-none` + checkmark via inset shadow). Each option line: `<label>` with icon + bold name + helper text.
- **Avatar preview:** xl TeamAvatar showing the live combo of selected emoji + color. Updates as the user clicks.
- **Emoji picker:** small fixed list of ~32 curated emojis (no full Unicode picker — YAGNI). Picked emoji highlights with `ring-2 ring-neutral-900/10`.
- **Color swatches:** 10 colored dots, each `h-8 w-8 rounded-full` with the corresponding `bg-{token}-500`. Selected dot: `ring-2 ring-neutral-900 ring-offset-2`.
- **Dev Fill button:** required by CLAUDE.md ("every form needs a Dev Fill button for localhost testing"). Random sensible defaults.
- **Validation:**
  - name required, max 120, trimmed
  - if purpose=project, project FK required
  - shows inline `text-xs text-rose-600` error per field on submit attempt
- **Submit success:** route to `/teams/{id}` (the new detail page). Toast: "Team created"
- **Submit error:** toast with the API message; field-level errors inline.
- **Loading:** submit button switches to spinner + "Creating…", form is disabled.
- **Mobile:** sections stack normally; purpose cards become a vertical stack; Dev Fill / Cancel / Create form a sticky bottom bar.

### 3.3 `/teams/[id]` — Detail

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Teams › Mobile Launch Squad

┌── Header card (mid) ───────────────────────────────────────────┐
│ ┌──┐                                                            │
│ │📐│ Mobile Launch Squad         [Initiative] [🌐 Public]   ⋯  │
│ └──┘ Cross-functional release team for the Q3 mobile launch.   │
│      Created by Joan Reyes · 3 weeks ago                        │
│                                                                 │
│      [Joined ✓ ▾]  ←  appears as either Join, Joined, Request,│
│                       or hidden depending on my_role + visibility│
└─────────────────────────────────────────────────────────────────┘

┌── 2-column grid (lg+) ─────────────────────────────────────────┐
│ ┌── Members (2/3 width) ────┐  ┌── Linked work (1/3 width) ─┐ │
│ │ Members  · 14              │  │ Support Desk               │ │
│ │ ────────────────────────── │  │ ──────────────────────────│ │
│ │ ⭕ Joan Reyes  [Owner]  ⋯  │  │  3                         │ │
│ │ ⭕ Marco L.    [Admin]  ⋯  │  │  open team-scoped tickets  │ │
│ │ ⭕ Aisha B.    [Member] ⋯  │  │                            │ │
│ │ ⭕ Sam K.      [Member]    │  │  → View tickets             │ │
│ │ ... 10 more                │  └────────────────────────────┘ │
│ │ [+ Add member]   [See all]│                                  │
│ └────────────────────────────┘  ┌── Notifications ──────────┐ │
│                                 │ Real-time   [On  ●]        │ │
│                                 │ Daily digest [On  ●]       │ │
│                                 │ → Manage in settings        │ │
│                                 └────────────────────────────┘ │
│                                                                 │
│                                 ┌── Project (if linked) ────┐ │
│                                 │ 📁 Phoenix Tower           │ │
│                                 │    On track · Q3 2026      │ │
│                                 │    → Open project           │ │
│                                 └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

- **Breadcrumbs:** `Workspace › Teams › {team.name}` — text-xs uppercase tracking-wider with `›` separators in `text-neutral-300`.
- **Header card:** big mid card. Lg TeamAvatar + name (text-2xl) + chips + ellipsis menu (Edit, Archive, Transfer ownership, Delete — gated by my_role).
- **Action button** is the most important interactive surface and changes by role/visibility:
  - non-member, public → `Join` (filled button)
  - non-member, private → `Request to join` (outline button)
  - non-member, secret → page renders 404
  - member/guest → `Joined ✓ ▾` (chevron opens menu: Notification prefs, Leave team)
  - owner → `Joined ✓ ▾` with extra menu items (Transfer ownership, Settings)
- **Members panel (lg col-span-2):** `rounded-2xl border bg-white p-5`. First 8 members shown inline as MemberRows; if >8, "See all" link at the bottom routes to `/teams/[id]/members`. "+ Add member" button at the top only when my_role in (owner, admin).
- **Linked work panel:** stat tile-ish — big number (the open ticket count) with helper line and a "View tickets" link that filters Support Desk tickets to this team. Empty state: "No team-scoped tickets yet" with "Create one in Support Desk" link.
- **Notifications panel:** quick toggles for the *current user's* prefs on this team. Toggle component uses neutral-900 active / neutral-200 inactive style. "Manage in settings" routes to `/teams/[id]/settings`.
- **Project panel:** appears only when `team.purpose=project AND team.project != null`. Empty state: "(project removed)" if the linked project was deleted.
- **Empty states:**
  - **No members yet** (rare — owner is auto-added at create): empty MemberRow placeholder with "Invite your first teammate" CTA.
- **Error state:** if detail fetch fails, replace the entire grid with `<DataStateBanner>` retry card.
- **404 state:** when secret team is requested by non-member: full-page "Team not found" using neutral-tinted empty card (no info leakage).
- **Mobile:** grid collapses to a single column. Members panel first, then Linked work, then Notifications, then Project. The header card's ellipsis menu becomes a full-width action sheet on tap.

### 3.4 `/teams/[id]/edit` — Edit metadata

Same layout as `/teams/new` *Section 1* and *Section 3* (no purpose change once created — purpose is structural). Differences:

- Page title: "Edit team"
- Visibility transitions get inline warnings:
  - public → secret: "Members of this team won't change, but it will disappear from the directory."
  - private → public: "Anyone in the org can now find and join this team."
- "Danger zone" link at the bottom: "Manage transfer / archive / delete in [Settings](./settings)" — keeps destructive actions out of edit.
- Submit success: route back to `/teams/[id]` with toast "Saved".

### 3.5 `/teams/[id]/members` — Member management

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Teams › Mobile Launch Squad › Members

Members of Mobile Launch Squad                  [+ Add members]

┌── filter shelf ────────────────────────────────────────────────┐
│  [All] [Owner] [Admins] [Members] [Guests]   ┌──────────┐     │
│                                              │🔍 search ││     │
│                                              └──────────┘     │
└────────────────────────────────────────────────────────────────┘

┌── Members list (big card) ─────────────────────────────────────┐
│ MemberRow                                                       │
│ MemberRow                                                       │
│ ...                                                             │
│ [Load more]    showing 25 of 32                                 │
└────────────────────────────────────────────────────────────────┘
```

- **Filter chips** by role; "All" is the default. Search filters by name + email (server-side via the API).
- **+ Add members** button opens a modal with `<UserPicker multiple>`. After picking, role defaults to "Member" (with a small `<RoleSelect>` per added person).
- **Optimistic add:** new MemberRows render immediately with a soft `opacity-60` until the POST resolves; rollback on error.
- **Optimistic remove:** clicked row fades out before the DELETE resolves; reappears on error.
- **Optimistic role change:** chip swaps immediately, rolls back on 409 (concurrent edit) — a toast shows "Someone else changed this role; latest is {role}".
- **Empty state:** "No members match this filter" — neutral text, no CTA.
- **Mobile:** filter chips wrap; member rows are full-width.

### 3.6 `/teams/[id]/settings` — Notifications + danger zone

```
─────────────────────────────────────────────────────────────────────
WORKSPACE › Teams › Mobile Launch Squad › Settings

┌── My notifications for this team ──────────────────────────────┐
│  Real-time alerts (added/promoted/owner-transfer)              │
│                                                  [On  ●]        │
│  Daily digest                                                   │
│  Frequency:  ◉ Daily   ◯ Weekly   ◯ Off                        │
│                                                                 │
│  💡 Digest is sent at 08:00 in your org's timezone.             │
└────────────────────────────────────────────────────────────────┘

┌── Team management (owner/admin only) ─────────────────────────┐
│  Edit team                                       [Edit →]      │
│  Archive this team                               [Archive]     │
│  ─────────────────────────────────────                         │
│  Danger zone (owner only)                                      │
│  Transfer ownership                              [Transfer →]  │
│  Delete this team permanently                    [Delete...]   │
└────────────────────────────────────────────────────────────────┘
```

- **My notifications** card is shown to every member (incl. guests).
- **Team management** card is visible only when `my_role in (owner, admin)`. Inside, danger-zone block is owner-only.
- **Archive button:** `border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400`. Opens a confirm modal: "Archive Mobile Launch Squad? It will be hidden from the directory and won't receive new tickets."
- **Transfer button:** opens a modal with `<UserPicker single>` filtered to current team members. Shows confirm: "Transfer ownership to {user}? You'll keep your admin role."
- **Delete button:** label `text-rose-700`, opens a destructive confirm modal: rose-tinted, types-the-team-name-to-confirm pattern. Mentions the linked-ticket fallback ("3 tickets will keep their data but lose this team's tag").
- **Mobile:** all sections stack; modals become full-page sheets.

---

## 4. Mobile considerations

The rest of the app is responsive — Tailwind 4 with `sm`, `md`, `lg`, `xl` breakpoints. Specific notes:

- **Sidebar:** the existing global sidebar collapses on small screens (already handled). No teams-specific work.
- **Touch targets:** all interactive elements ≥44×44pt. The MemberRow ellipsis button, chip popovers, and emoji picker cells are sized accordingly.
- **Modals:** full-screen sheets on `< sm`; centered modals on `≥ sm`. Use the existing modal component pattern from CRM if one exists; otherwise a `fixed inset-0 bg-black/40` overlay with `rounded-t-3xl bg-white p-6 sm:rounded-3xl sm:max-w-lg sm:mx-auto sm:my-12` panel.
- **Sticky CTAs:** the "+ New team" CTA in `/teams` becomes a floating action button on `< sm` (`fixed bottom-6 right-6 h-14 w-14 rounded-full bg-neutral-900 text-white shadow-lg`).
- **Truncation:** team names truncate at 1 line on small cards (`line-clamp-1`); description at 2 lines (`line-clamp-2`).

---

## 5. Accessibility

- **WCAG 2.2 AA** as the bar.
- **Color contrast:** all text/background pairs verified ≥4.5:1 normal, ≥3:1 large. The team color is decorative, not informational — name + emoji + role chip carry the meaning.
- **Keyboard navigation:** every interactive element reachable via Tab; focus rings present. Tab order follows visual order. Esc closes popovers and modals.
- **Screen reader:**
  - TeamAvatar announces `aria-label="{teamName} icon"` when standalone, hidden when paired with the name.
  - Visibility chip uses `aria-label="Public team"` / `Private team` / `Secret team` — the icon alone isn't enough.
  - Role chip on MemberRow announces `aria-label="Joan Reyes — Admin role"` so screen readers don't read the chip as a fragment.
  - `<UserPicker>` follows ARIA Combobox 1.2 pattern (combobox + listbox + option roles, `aria-activedescendant`).
- **Forms:** every input has a visible `<label>` with `for=` associated; required fields marked with `*` AND `aria-required="true"`.
- **Toasts** for action feedback (the existing `toast` store) — already screen-reader friendly via `aria-live`.
- **Reduced motion:** respect `prefers-reduced-motion` for the load spinner and any transitions (`transition-all` becomes `transition-none` under that media query — Tailwind handles this if we use `motion-safe:` prefixes on transitions).

---

## 6. Empty / loading / error states (cheat-sheet)

| State | Pattern |
|---|---|
| **Loading** | Centered `animate-spin` (`h-7 w-7` or `h-5 w-5`) inside `py-28` (page-level) or inline beside button text |
| **Empty (no data)** | Dashed-border card with emoji + headline + helper + 1–2 CTAs. Always offer at least one action. |
| **Empty (filtered)** | Flat text inside the existing card frame — "No teams match \"{q}\"" + "Clear filters" link. No emoji, smaller typography. |
| **Error (network/500)** | `<DataStateBanner>` rose-tinted card with retry button (existing component). |
| **Error (404 / not authorised)** | Neutral-tinted card with "Team not found" — never reveal whether it exists (defends secret-team confidentiality). |
| **Optimistic in-flight** | Affected row gets `opacity-60` + `pointer-events-none`; revert on error with a toast. |

---

## 7. Internationalisation (i18n)

Keys all under `workspace.teams.*` namespace, contributed in en/fr/es/ar.

Core keys (a starter set — `/sveltekit` will round these out as it builds):

```
workspace.teams.title                  → "Teams"
workspace.teams.eyebrow                → "Workspace"
workspace.teams.helper                 → "Lightweight teams for project pods, initiatives, and guilds."
workspace.teams.new                    → "New team"
workspace.teams.tabs.mine              → "My teams"
workspace.teams.tabs.all               → "All"
workspace.teams.tabs.archived          → "Archived"
workspace.teams.purpose.project        → "Project"
workspace.teams.purpose.initiative     → "Initiative"
workspace.teams.purpose.guild          → "Guild"
workspace.teams.visibility.public      → "Public"
workspace.teams.visibility.private     → "Private"
workspace.teams.visibility.secret      → "Secret"
workspace.teams.role.owner             → "Owner"
workspace.teams.role.admin             → "Admin"
workspace.teams.role.member            → "Member"
workspace.teams.role.guest             → "Guest"
workspace.teams.member_count           → "{count, plural, one {# member} other {# members}}"
workspace.teams.ticket_count           → "{count, plural, one {# ticket} other {# tickets}}"
workspace.teams.action.join            → "Join"
workspace.teams.action.request_join    → "Request to join"
workspace.teams.action.joined          → "Joined"
workspace.teams.action.leave           → "Leave team"
workspace.teams.action.archive         → "Archive"
workspace.teams.action.unarchive       → "Unarchive"
workspace.teams.action.transfer        → "Transfer ownership"
workspace.teams.action.delete          → "Delete team"
workspace.teams.empty.mine.title       → "You're not in any teams yet"
workspace.teams.empty.mine.helper      → "Browse all teams or create your own."
workspace.teams.empty.org.title        → "No teams yet"
workspace.teams.empty.org.helper       → "Be the first to create a team."
workspace.teams.empty.search           → "No teams match \"{query}\""
workspace.teams.empty.archived         → "No archived teams"
workspace.teams.error.load             → "Couldn't load teams"
workspace.teams.danger.delete_confirm  → "Type the team name to confirm"
```

**RTL note:** Arabic (`ar`) flips horizontal layout. Tailwind's `rtl:` variants and `flex-row-reverse` should already work — this spec uses `gap-` and `space-x-` rather than left/right margins, so RTL is largely automatic. The eyebrow's wide letter-spacing remains correct in RTL.

---

## 8. Open questions for `/sveltekit` (resolve at implementation time)

1. **Modal component** — does the codebase already have a generic `<Modal>` or does each page roll its own? If the latter, build a shared `<ConfirmModal>` here so danger-zone reuse is consistent.
2. **Toggle component** — same question. The notifications panel needs an iOS-style toggle. If absent, build `<Toggle bind:checked />` as a teams-component (small enough to live in `lib/components/teams/`, can be promoted later).
3. **Emoji picker** — confirm the curated 32-emoji list is enough. Suggested: 👥 🚀 ⚡️ 🎯 🛠️ 🌱 📐 💡 🔥 🌊 🏔️ ⛰️ 🎨 🧪 🔍 📊 📈 🌟 ✨ 🌀 🦊 🐢 🐝 🦉 🌻 🌸 🌳 🪴 ☕️ 🥁 🎻 🛰️.
4. **Avatar fallback for users without photos** — initials disc or a generic icon? This codebase doesn't seem to have user photos at all, so initials is the answer; confirm during implementation.
5. **Cursor pagination shape** — confirm the API returns `next` / `previous` URLs vs. a `cursor=` token. Match what other paginated endpoints in this repo return.

---

## Sign-off

This spec is the visual + interaction source of truth. Implementation (`/sveltekit`) should produce:

- 5 components in `client/src/lib/components/teams/`
- 6 routes in `client/src/routes/teams/`
- 1 colour-token map in `client/src/lib/components/teams/team-colors.ts`
- ~40 i18n keys in en/fr/es/ar

Anything that contradicts this spec should bounce back here for resolution rather than getting decided silently in code.
