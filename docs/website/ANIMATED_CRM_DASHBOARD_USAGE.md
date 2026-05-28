# Animated CRM Dashboard (Astro)

Component file:
- `docs/website/AnimatedCRMDashboard.astro`

Import into your Astro page:

```astro
---
import AnimatedCRMDashboard from "../components/AnimatedCRMDashboard.astro";
---

<AnimatedCRMDashboard />
```

Notes:
- Uses real CRM module labels/routes from `app-feature-catalog.json`.
- No animation library required.
- Motion is native CSS + browser JavaScript.
- Works with hover/click-free auto-animation, and honors `prefers-reduced-motion`.
- If you currently have `DeveloperOSModuleExplorer.astro` on the page, replace it with this component.
