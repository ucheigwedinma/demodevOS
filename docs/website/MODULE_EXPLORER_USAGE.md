# DeveloperOS Animated Module Explorer (Astro)

This file now forwards to the CRM dashboard component:
- `DeveloperOSModuleExplorer.astro` -> `AnimatedCRMDashboard.astro`

1. Copy `docs/website/DeveloperOSModuleExplorer.astro` and `docs/website/app-feature-catalog.json` into your Astro project (same folder).
2. Import on your page:

```astro
---
import DeveloperOSModuleExplorer from "../components/DeveloperOSModuleExplorer.astro";
---

<DeveloperOSModuleExplorer />
```

3. No framework hydration is required. The component uses plain browser JavaScript and CSS animations.

## Why this one animates reliably

- No external animation library.
- No `client:*` directive dependency.
- All motion is in native CSS transitions/keyframes plus `requestAnimationFrame` for KPI counters.
- Hover, focus, click, and auto-cycle are all implemented.
