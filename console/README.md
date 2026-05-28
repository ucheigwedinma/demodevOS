# console

Internal admin app for **DeveloperOS platform operators** — the same audience
that uses Django `/admin/`. This is a SvelteKit (adapter-static) SPA that
provides a nicer UX over a subset of platform-wide admin concerns.

## What this is *not*

`console` is **not** a per-organization admin panel. Customer Organization
admins manage their own org (users, roles, settings) from inside the main
product at `client/` — specifically the `iam` and `settings` route groups.

If you're adding a feature here, ask: *"Would a single Organization's admin
need this?"* If yes, it belongs in `client/`. `console/` is for things that
require cross-org or platform-wide visibility.

## Audience

| App | Audience | Auth |
|-----|----------|------|
| `client/` | Organization Users (incl. their org admins) | scoped to one Organization |
| `console/` | Platform Operators (DeveloperOS staff) | `is_staff` / `is_superuser` |
| `/admin/` (Django) | Platform Operators | same as console |

See [`docs/glossary.md`](../docs/glossary.md) for full definitions of
Organization, Platform Operator, and related terms.

## Local dev

```bash
npm install
npm run dev      # http://localhost:5174
npm run build    # static SPA in build/
npm run check    # typecheck + svelte-check
```

The console talks to the same Django/DRF backend as `client/`; only the
audience and route surface differ.
