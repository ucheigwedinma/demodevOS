<script lang="ts">
  import { page } from "$app/stores";

  let { children } = $props();

  type MenuItem = {
    label: string;
    href?: string;
    exact?: boolean;
  };

  type MenuSection = {
    title: string;
    items: MenuItem[];
  };

  const menuSections: MenuSection[] = [
    {
      title: "Workspace",
      items: [
        { href: "/reports", label: "Reports Library" },
      ],
    },
    {
      title: "Execution",
      items: [
        { href: "/reports/run", label: "Run Reports", exact: true },
        { href: "/reports/exports", label: "Export Results", exact: true },
        { href: "/reports/scheduled", label: "My Scheduled Reports", exact: true },
        { href: "/reports/drill-through", label: "Drill-through Navigation", exact: true },
      ],
    },
    {
      title: "Personalization",
      items: [
        { href: "/reports/saved-views", label: "Saved Views", exact: true },
        { href: "/reports/subscriptions", label: "Subscriptions", exact: true },
        { href: "/reports/dashboard", label: "Dashboard Integration", exact: true },
        { href: "/reports/notifications", label: "Notifications", exact: true },
      ],
    },
    {
      title: "Builder",
      items: [
        { href: "/reports/builder", label: "Simple Report Builder", exact: true },
      ],
    },
  ];

  function isActive(href?: string, exact?: boolean): boolean {
    if (!href) return false;
    if (exact) return $page.url.pathname === href;
    if (href === "/reports") {
      return $page.url.pathname === "/reports" || /^\/reports\/\d+$/.test($page.url.pathname);
    }
    return $page.url.pathname.startsWith(href);
  }
</script>

<div class="h-screen flex flex-col bg-neutral-50 font-sans">
  <header class="bg-neutral-900 shrink-0">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <a href="/" class="text-lg">
          <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
        </a>
        <span class="text-neutral-600">|</span>
        <h1 class="text-sm font-semibold text-white">Reporting Workspace</h1>
      </div>
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to app
      </a>
    </div>
  </header>

  <div class="max-w-7xl mx-auto px-6 flex gap-8 flex-1 min-h-0 w-full">
    <aside class="w-56 shrink-0 overflow-y-auto py-8">
      {#each menuSections as section}
        <div class="mb-8">
          <p class="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3 px-3">
            {section.title}
          </p>
          <nav class="space-y-0.5">
            {#each section.items as item}
              <a
                href={item.href}
                class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                       {isActive(item.href, item.exact)
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>
      {/each}
    </aside>

    <div class="flex-1 min-w-0 overflow-y-auto py-8">
      {@render children()}
    </div>
  </div>
</div>
