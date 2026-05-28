<script lang="ts">
  import "../app.css";
  import { afterNavigate, beforeNavigate, goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import Toaster from "$lib/components/Toaster.svelte";
  import Tooltip from "$lib/components/Tooltip.svelte";
  import LanguageSelector from "$lib/components/LanguageSelector.svelte";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { VERSION, CODENAME, RELEASE_DATE } from "$lib/version";
  import WelcomeTour from "$lib/components/onboarding/WelcomeTour.svelte";
  import DemoTour from "$lib/components/onboarding/DemoTour.svelte";
  import CompanySetup from "$lib/components/onboarding/CompanySetup.svelte";
  import InviteStaff from "$lib/components/onboarding/InviteStaff.svelte";
  import SubscriptionPicker from "$lib/components/onboarding/SubscriptionPicker.svelte";
  import TrialSuccess from "$lib/components/onboarding/TrialSuccess.svelte";
  import GettingStarted from "$lib/components/onboarding/GettingStarted.svelte";
  import NotificationBell from "$lib/components/NotificationBell.svelte";
  import PresenceIndicator from "$lib/components/PresenceIndicator.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { SIDEBAR_MODULE_MAP, SIDEBAR_SUBITEM_MODULE_MAP, SIDEBAR_TIER_MAP, TOP_NAV_MODULE_MAP, getRouteModule, getRouteTier, getUserTierLevel, isModuleEnabled } from "$lib/modules";
  import { currency } from "$lib/stores/currency.svelte";
  import { statusRegistry } from "$lib/stores/statusRegistry.svelte";
  import { clearTokens } from "$lib/api";
  import { ws } from "$lib/stores/websocket.svelte";
  import { initSessionFingerprint, startSessionGuard } from "$lib/sessionGuard";
  import { commandPalette } from "$lib/stores/commandPalette.svelte";
  import CommandPalette from "$lib/components/CommandPalette.svelte";
  import type { NavDomainSection } from "$lib/types";
  import { domains, flattenSections, domainIconPath, subItemIconPath, navLabel } from "$lib/navigation";

  let { children } = $props();

  let sidebarOpen = $state(true);
  let mobileMenuOpen = $state(false);
  let mainEl = $state<HTMLElement | null>(null);
  let sectionPanelEl = $state<HTMLElement | null>(null);
  let accordionPanelEl = $state<HTMLElement | null>(null);

  afterNavigate(({ to }) => {
    mobileMenuOpen = false;
    expandedSectionKey = null;
    mainEl?.scrollTo(0, 0);
    // Report current page for presence tracking
    if (to?.url?.pathname) ws.setPage(to.url.pathname);
  });
  let showLogoutModal = $state(false);
  let showSessionChangedModal = $state(false);
  let avatarImageBroken = $state(false);
  let hoveredDomainKey = $state<string | null>(null);
  let expandedSectionKey = $state<string | null>(null);

  function handleLogout() {
    ws.disconnect();
    clearTokens();
    onboarding.reset();
    currency.reset();
    statusRegistry.reset();
    showLogoutModal = false;
    goto("/login");
  }

  function handleSessionExpired() {
    clearTokens();
    onboarding.reset();
    currency.reset();
    statusRegistry.reset();
    showSessionChangedModal = false;
    window.location.href = "/login";
  }

  onMount(() => {
    initSessionFingerprint();
    commandPalette.loadRecent();

    // Connect WebSocket for real-time updates
    const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
    if (token) ws.connect(token);
    let accordionCloseFrame = 0;
    const handleOutsideAccordionClick = (event: MouseEvent) => {
      if (!expandedSectionKey) return;
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (sectionPanelEl?.contains(target) || accordionPanelEl?.contains(target)) return;
      cancelAnimationFrame(accordionCloseFrame);
      accordionCloseFrame = requestAnimationFrame(() => {
        expandedSectionKey = null;
      });
    };
    document.addEventListener("click", handleOutsideAccordionClick);
    const cleanup = startSessionGuard(() => {
      const path = window.location.pathname;
      if (path.startsWith("/login") || path === "/signup" || path.startsWith("/partner/login")) return;
      showSessionChangedModal = true;
    });
    return () => {
      cancelAnimationFrame(accordionCloseFrame);
      document.removeEventListener("click", handleOutsideAccordionClick);
      cleanup();
    };
  });

  // ── Module & tier gating ─────────────────────────────────────────────
  const enabledModules = $derived(onboarding.enabledModules);
  const addonModules = $derived(onboarding.addonModules);
  const isTrialing = $derived(onboarding.isTrialing);
  const userTierLevel = $derived(
    onboarding.user?.is_superuser ? Infinity : getUserTierLevel(onboarding.user?.subscription ?? null)
  );

  // Filter domains: remove module-gated and tier-gated sections, then remove empty domains
  const filteredDomains = $derived(
    domains
      .map((d) => ({
        ...d,
        sections: d.sections
          .filter((s) =>
            isModuleEnabled(enabledModules, SIDEBAR_MODULE_MAP[s.key])
            && (SIDEBAR_TIER_MAP[s.key] === undefined || userTierLevel >= SIDEBAR_TIER_MAP[s.key])
          )
          .map((s) => ({
            ...s,
            subItems: s.subItems.filter((item) =>
              isModuleEnabled(enabledModules, SIDEBAR_SUBITEM_MODULE_MAP[item.href])
            ),
          })),
      }))
      .filter((d) => d.sections.length > 0)
  );

  // Flat list for CommandPalette (unfiltered — palette does its own gating)
  const allSections = flattenSections(domains);

  // ── Active state (derived from URL) ──────────────────────────────────

  function isConstructionLinkedProjectPath(path: string): boolean {
    return (
      path === "/projects/tasks"
      || path.startsWith("/projects/tasks/")
      || path === "/projects/field-operations"
      || path.startsWith("/projects/field-operations/")
    );
  }

  function isSectionActive(section: NavDomainSection, pathname: string): boolean {
    const ref = $page.url.searchParams.get("ref");
    const target = ref || pathname;

    if (section.key === "construction") {
      return target.startsWith("/construction") || isConstructionLinkedProjectPath(target);
    }
    if (section.key === "project-planning") {
      return target.startsWith("/project-planning");
    }
    if (section.key === "hr") {
      if (target === section.href) return true;
      return section.subItems.some((item) => {
        if (item.matchPaths) {
          return item.matchPaths.some((p) => target === p);
        }
        if (item.exact) return target === item.href;
        return target === item.href || target.startsWith(item.href + "/");
      });
    }
    if (section.key === "boq") {
      return target.startsWith("/boq");
    }
    if (section.key === "projects") {
      return target.startsWith("/projects") && !isConstructionLinkedProjectPath(target);
    }
    if (section.key === "procurement") {
      return target.startsWith("/procurement");
    }
    if (section.href === "/") return target === "/";
    if (target === section.href || target.startsWith(section.href + "/")) return true;
    // Also match if any sub-item href matches the current path
    return section.subItems.some((item) =>
      target === item.href || target.startsWith(item.href + "/")
    );
  }

  function isSubActive(
    item: { href: string; exact?: boolean; matchPaths?: string[] },
    pathname: string
  ): boolean {
    if (item.matchPaths) {
      return item.matchPaths.some((p) => pathname === p);
    }
    if (item.exact) return pathname === item.href;
    return pathname.startsWith(item.href);
  }

  const activeDomain = $derived.by(() => {
    const pathname = $page.url.pathname;
    const ref = $page.url.searchParams.get("ref");
    const target = ref || pathname;

    // Dashboard detection: "/" or /dashboard/* (legacy /portfolio-analysis
    // path also matches so the cluster stays active during the redirect stub).
    const isDashboardPath =
      target === "/" ||
      target.startsWith("/dashboard") ||
      target.startsWith("/portfolio-analysis");

    if (isDashboardPath) {
      return filteredDomains.find((d) => d.key === "dashboard") ?? filteredDomains[0];
    }

    // Accounting detection: its sections live under /finance/* so check before Finance
    const accountingDomain = filteredDomains.find((d) => d.key === "accounting");
    if (accountingDomain?.sections.some((s) => isSectionActive(s, target))) {
      return accountingDomain;
    }

    return (
      filteredDomains.find((d) =>
        d.sections.some((s) => isSectionActive(s, pathname))
      ) ?? filteredDomains[0]
    );
  });

  const activeSection = $derived.by(() => {
    if (!activeDomain) return null;
    const pathname = $page.url.pathname;
    // Find the first section that matches — order matters (more specific first)
    return (
      activeDomain.sections.find((s) => isSectionActive(s, pathname)) ??
      activeDomain.sections[0] ??
      null
    );
  });

  // Display domain: hovered domain takes priority, falls back to URL domain
  const displayDomain = $derived(
    (hoveredDomainKey
      ? filteredDomains.find((d) => d.key === hoveredDomainKey)
      : null) ?? activeDomain ?? filteredDomains[0]
  );

  // Expanded section (for floating accordion)
  const expandedSection = $derived(
    expandedSectionKey
      ? displayDomain?.sections.find((s) => s.key === expandedSectionKey) ?? null
      : null
  );

  // ── Route type detection ─────────────────────────────────────────────

  const isPublicRoute = $derived(
    $page.url.pathname.startsWith("/login") ||
    $page.url.pathname === "/signup" ||
    ($page.url.pathname.startsWith("/partner") && !$page.url.pathname.startsWith("/partners")) ||
    $page.url.pathname.startsWith("/help") ||
    $page.url.pathname === "/terms" ||
    $page.url.pathname === "/privacy" ||
    $page.url.pathname === "/cookies" ||
    $page.url.pathname === "/forgot-password" ||
    $page.url.pathname === "/reset-password" ||
    $page.url.pathname === "/verify-email" ||
    $page.url.pathname === "/contact-support" ||
    $page.url.pathname === "/request-demo" ||
    $page.url.pathname === "/demo"
  );

  const isSettingsRoute = $derived(
    $page.url.pathname.startsWith("/settings")
  );

  const isIamRoute = $derived(
    $page.url.pathname.startsWith("/iam")
  );

  const isUserSettingsRoute = $derived(
    $page.url.pathname.startsWith("/user-settings")
  );

  const isReportsRoute = $derived(
    $page.url.pathname.startsWith("/reports")
  );

  const isNotificationsRoute = $derived(
    $page.url.pathname.startsWith("/notifications")
  );

  // ── User display ─────────────────────────────────────────────────────

  const sidebarAvatarImage = $derived(onboarding.user?.profile_photo_url ?? null);
  const sidebarDisplayName = $derived(
    (onboarding.user?.display_name || onboarding.user?.full_name || onboarding.user?.email || "").trim()
  );
  const sidebarAvatarInitial = $derived(sidebarDisplayName ? sidebarDisplayName[0]?.toUpperCase() : "?");

  // ── Route guard (preventive) ─────────────────────────────────────────

  function isUnauthorizedRoute(pathname: string): boolean {
    const routeModule = getRouteModule(pathname);
    if (routeModule && !enabledModules.has(routeModule)) return true;
    const routeTier = getRouteTier(pathname);
    if (routeTier !== undefined && userTierLevel < routeTier) return true;
    return false;
  }

  beforeNavigate(({ to, cancel }) => {
    if (!to?.url || !onboarding.loaded) return;
    const pathname = to.url.pathname;
    // Allow public routes
    if (
      pathname.startsWith("/login") ||
      pathname === "/signup" ||
      pathname.startsWith("/help") ||
      pathname === "/" ||
      pathname.startsWith("/dashboard")
    ) return;
    if (isUnauthorizedRoute(pathname)) {
      cancel();
      goto("/");
    }
  });

  // ── Effects ──────────────────────────────────────────────────────────

  $effect(() => {
    if (typeof window === "undefined") return;
    if (isPublicRoute) return;
    const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
    if (!token) {
      goto("/login");
    } else if (!onboarding.loaded) {
      onboarding.load();
      currency.load();
      statusRegistry.load();
    } else if (isUnauthorizedRoute($page.url.pathname)) {
      goto("/");
    }
  });

  $effect(() => {
    if (sidebarAvatarImage) {
      avatarImageBroken = false;
    }
  });

  // Sync <html lang> and <html dir> with the user's chosen locale.
  // Required so the browser swaps text direction (LTR ↔ RTL) and
  // accessibility tools announce the page in the right language.
  $effect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.lang = i18n.locale;
    document.documentElement.dir = i18n.direction;
  });

  // Hydrate the i18n store from the server-side user preference once
  // onboarding has loaded. The server's value beats localStorage so
  // the user's chosen language follows them across devices.
  $effect(() => {
    if (!onboarding.loaded) return;
    i18n.applyServerLocale(onboarding.user?.default_language ?? null);
  });

  function getSectionNavigationHref(section: NavDomainSection): string {
    return section.subItems[0]?.href ?? section.href;
  }

  function toggleSection(section: NavDomainSection) {
    expandedSectionKey = expandedSectionKey === section.key ? null : section.key;
  }

  function handleSubItemClick() {
    expandedSectionKey = null;
    mobileMenuOpen = false;
  }

  function handleGlobalKeydown(e: KeyboardEvent) {
    if (e.key === "Escape" && expandedSectionKey) {
      expandedSectionKey = null;
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      commandPalette.toggle();
    }
  }

  // Close accordion when domain changes
  let prevDisplayDomainKey = $state<string | undefined>(undefined);
  $effect(() => {
    const currentKey = displayDomain?.key;
    if (prevDisplayDomainKey !== undefined && currentKey !== prevDisplayDomainKey) {
      expandedSectionKey = null;
    }
    prevDisplayDomainKey = currentKey;
  });



</script>

<svelte:window onkeydown={handleGlobalKeydown} />

{#if isPublicRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else if !onboarding.loaded}
  <div class="min-h-screen bg-neutral-50"></div>
{:else if isSettingsRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else if isIamRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else if isReportsRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else if isUserSettingsRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else if isNotificationsRoute}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
    {@render children()}
  </div>
{:else}
  <div class="min-h-screen bg-neutral-50 text-neutral-900 font-sans flex">
    <!-- Mobile menu overlay -->
    {#if mobileMenuOpen}
      <button
        class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
        onclick={() => (mobileMenuOpen = false)}
        aria-label="Close menu"
      ></button>
    {/if}

    <!-- ═══ Layer 1: Icon Rail (52px, always visible on desktop) ═══ -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="w-[52px] bg-neutral-900 flex-col items-center shrink-0 h-screen sticky top-0 z-50
             hidden lg:flex"
      style={mobileMenuOpen ? "display:flex; position:fixed; left:0; top:0;" : ""}
      onmouseleave={() => (hoveredDomainKey = null)}
    >
      <!-- Logo -->
      <div class="h-14 flex items-center justify-center">
        <a href="/" class="block w-9 h-9">
          <img src="/logo-dark.png" alt="developerOS" class="w-full h-full object-contain" />
        </a>
      </div>

      <!-- Domain Icons -->
      <nav class="flex-1 flex flex-col items-center gap-1 py-3">
        {#each filteredDomains as domain}
          {@const href = domain.key === "dashboard" ? "/" : domain.sections[0]?.href ?? "/"}
          {@const label = navLabel(domain, i18n.t)}
          <Tooltip text={label}>
            <a
              {href}
              class="w-9 h-9 flex items-center justify-center rounded-lg transition-colors
                     {activeDomain?.key === domain.key
                       ? 'bg-white/15 text-white'
                       : 'text-neutral-500 hover:bg-white/10 hover:text-neutral-300'}"
              aria-label={label}
              onmouseenter={() => (hoveredDomainKey = domain.key)}
            >
              <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d={domainIconPath(domain.key)} />
              </svg>
            </a>
          </Tooltip>
        {/each}
      </nav>

      <!-- User Avatar + Logout -->
      <div class="py-4 flex flex-col items-center gap-3">
        <Tooltip text="User settings">
          <a
            href="/user-settings"
            class="w-8 h-8 rounded-full bg-neutral-700 border border-neutral-600/70 flex items-center justify-center text-xs font-semibold text-neutral-300 overflow-hidden hover:border-neutral-400 transition-colors"
            aria-label="User settings"
          >
            {#if sidebarAvatarImage && !avatarImageBroken}
              <img
                src={sidebarAvatarImage}
                alt={sidebarDisplayName || "User avatar"}
                class="h-full w-full object-cover"
                onerror={() => (avatarImageBroken = true)}
              />
            {:else}
              {sidebarAvatarInitial || "?"}
            {/if}
          </a>
        </Tooltip>
        <Tooltip text="Log out">
          <button
            onclick={() => (showLogoutModal = true)}
            class="w-8 h-8 rounded-lg flex items-center justify-center text-neutral-500 hover:bg-white/10 hover:text-red-400 transition-colors"
            aria-label="Log out"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" />
            </svg>
          </button>
        </Tooltip>

        <LanguageSelector />

        <Tooltip text="{CODENAME} · released {RELEASE_DATE}">
          <span
            class="rounded-md border border-neutral-700/60 bg-neutral-800/60 px-1.5 py-0.5 text-[9px] font-semibold tabular-nums tracking-wider text-neutral-300 hover:border-neutral-500 hover:bg-neutral-700 hover:text-white transition-colors cursor-default"
            aria-label="developerOS version {VERSION}, codename {CODENAME}"
          >
            v{VERSION}
          </span>
        </Tooltip>
      </div>
    </div>

    <!-- ═══ Layer 2: White Section Panel (180px, collapsible) ═══ -->
    <div
      class="relative shrink-0 transition-[margin-left] duration-200 hidden lg:flex"
      style={mobileMenuOpen ? "display:flex; position:fixed; left:52px; top:0; z-index:50;" : sidebarOpen ? "" : "margin-left:-180px;"}
    >
      <div bind:this={sectionPanelEl} class="w-[180px] bg-white border-r border-neutral-200 h-screen sticky top-0 flex flex-col z-20">
        <!-- Domain label header -->
        <div class="h-14 flex items-center px-4 border-b border-neutral-100">
          <h2 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
            {displayDomain?.label ?? ""}
          </h2>
        </div>

        <!-- Section links -->
        <nav class="flex-1 py-2 px-2 space-y-0.5 overflow-y-auto">
          {#each displayDomain?.sections ?? [] as section}
            {@const sectionLabel = navLabel(section, i18n.t)}
            <div
              class="flex items-center gap-1 rounded-lg text-[13px] font-medium transition-colors
                     {activeSection?.key === section.key
                       ? 'bg-neutral-100 text-neutral-900'
                       : 'text-neutral-500 hover:bg-neutral-50 hover:text-neutral-700'}"
            >
              <a
                href={getSectionNavigationHref(section)}
                onclick={() => (expandedSectionKey = null)}
                class="min-w-0 flex-1 px-3 py-2 flex items-center gap-2"
              >
                <span class="truncate">{sectionLabel}</span>
                {#if isTrialing && addonModules.has(SIDEBAR_MODULE_MAP[section.key])}
                  <span class="shrink-0 rounded bg-neutral-900 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">ADD-ON</span>
                {/if}
              </a>
              {#if section.subItems.length > 0}
                <button
                  type="button"
                  onclick={() => toggleSection(section)}
                  class="mr-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-black/5 hover:text-neutral-600"
                  aria-label={expandedSectionKey === section.key ? `Collapse ${sectionLabel}` : `Expand ${sectionLabel}`}
                  aria-expanded={expandedSectionKey === section.key}
                >
                  <svg
                    class="w-3.5 h-3.5 transition-transform {expandedSectionKey === section.key ? 'rotate-90' : ''}"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              {/if}
            </div>
          {/each}
        </nav>

        <!-- User Info (bottom) -->
        <div class="px-3 py-4 border-t border-neutral-100">
          <div class="flex items-center gap-3 px-2">
            <div class="text-xs">
              <p class="font-medium text-neutral-900 truncate">{onboarding.user?.full_name ?? ""}</p>
              <p class="text-neutral-400 capitalize">{onboarding.user?.organization?.role ?? ""}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Layer 3: Floating Accordion (absolute, dark) ═══ -->
      {#if expandedSection && expandedSection.subItems.length > 0}
        <div bind:this={accordionPanelEl} class="absolute left-[180px] top-0 w-[220px] h-screen bg-neutral-900 shadow-2xl z-20 flex flex-col">
          <!-- Section title header -->
          <div class="h-14 flex items-center px-4 border-b border-white/5">
            <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              {navLabel(expandedSection, i18n.t)}
            </h2>
          </div>

          <!-- Sub-items -->
          <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
            {#each expandedSection.subItems as item}
              <a
                href={item.href}
                onclick={handleSubItemClick}
                class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors
                       {isSubActive(item, $page.url.pathname)
                         ? 'bg-white/10 text-white'
                         : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'}"
              >
                <svg
                  class="h-4 w-4 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  stroke-width="1.75"
                  aria-hidden="true"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d={subItemIconPath(item.href)} />
                </svg>
                <span class="truncate">{navLabel(item, i18n.t)}</span>
                {#if item.badge}
                  <span class="ml-auto inline-flex rounded-full border border-emerald-300/30 bg-emerald-900/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-emerald-400">
                    {item.badge}
                  </span>
                {/if}
              </a>
            {/each}
          </nav>
        </div>
      {/if}
    </div>

    <!-- ═══ Main Content ═══ -->
    <div class="flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative">
      <!-- Top bar -->
      <header class="h-14 bg-neutral-900 flex items-center justify-between px-6 shrink-0">
        <Tooltip text="Toggle sidebar" position="bottom">
          <button
            onclick={() => {
              if (window.innerWidth < 1024) {
                mobileMenuOpen = !mobileMenuOpen;
              } else {
                sidebarOpen = !sidebarOpen;
              }
            }}
            class="p-2 -ml-2 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="Toggle sidebar"
          >
            <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </Tooltip>

        <div class="flex items-center gap-1">
          <Tooltip text="Search (⌘K)" position="bottom">
            <button
              onclick={() => commandPalette.open()}
              class="p-2 rounded-lg text-neutral-400 hover:bg-white/10 hover:text-neutral-300 transition-colors"
              aria-label="Search"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
            </button>
          </Tooltip>
          <PresenceIndicator />
          <Tooltip text="Notifications" position="bottom">
            <NotificationBell />
          </Tooltip>
          {#if isModuleEnabled(enabledModules, TOP_NAV_MODULE_MAP["reports"])}
            <Tooltip text="Reports" position="bottom">
              <a
                href="/reports"
                class="p-2 rounded-lg transition-colors {$page.url.pathname.startsWith('/reports') ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/10 hover:text-neutral-300'}"
                aria-label="Reports"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.5h16.5v15H3.75v-15Zm3 3h10.5m-10.5 3.75h10.5m-10.5 3.75h6.75" />
                </svg>
              </a>
            </Tooltip>
          {/if}
          {#if isModuleEnabled(enabledModules, TOP_NAV_MODULE_MAP["iam"])}
            <Tooltip text="Identity & Access" position="bottom">
              <a
                href="/iam/users"
                class="p-2 rounded-lg transition-colors {$page.url.pathname.startsWith('/iam') ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/10 hover:text-neutral-300'}"
                aria-label="Identity & Access Management"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/><path d="M14 13.12c0 2.38 0 6.38-1 8.88"/><path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/><path d="M2 12a10 10 0 0 1 18-6"/><path d="M2 16h.01"/><path d="M21.8 16c.2-2 .131-5.354 0-6"/><path d="M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2"/><path d="M8.65 22c.21-.66.45-1.32.57-2"/><path d="M9 6.8a6 6 0 0 1 9 5.2v2"/>
                </svg>
              </a>
            </Tooltip>
          {/if}
          <Tooltip text="Settings" position="bottom">
            <a
              href="/settings"
              class="p-2 rounded-lg transition-colors {$page.url.pathname.startsWith('/settings') ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/10 hover:text-neutral-300'}"
              aria-label="Settings"
            >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            </a>
          </Tooltip>
        </div>
      </header>

      <!-- Page content -->
      <main bind:this={mainEl} class="flex-1 min-h-0 px-3 py-4 sm:px-5 sm:py-8 overflow-y-auto">
        {@render children()}
      </main>
    </div>
  </div>
{/if}

<!-- Command Palette -->
{#if !isPublicRoute}
  <CommandPalette sections={allSections} {enabledModules} />
{/if}

<!-- Onboarding Modals -->
{#if !isPublicRoute && onboarding.showDemoTour}
  <DemoTour />
{/if}
{#if !isPublicRoute && onboarding.showTour}
  <WelcomeTour />
{/if}
{#if !isPublicRoute && onboarding.showCompanySetup}
  <CompanySetup />
{/if}
{#if !isPublicRoute && onboarding.showInviteStaff}
  <InviteStaff />
{/if}
{#if !isPublicRoute && onboarding.showTrialPrompt}
  <SubscriptionPicker />
{/if}
{#if !isPublicRoute && onboarding.showTrialSuccess}
  <TrialSuccess />
{/if}
{#if !isPublicRoute && onboarding.showGettingStarted}
  <GettingStarted />
{/if}

<!-- Logout Confirmation Modal -->
{#if showLogoutModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm logout-backdrop-enter"
      onclick={() => (showLogoutModal = false)}
      aria-label="Close modal"
    ></button>

    <!-- Modal -->
    <div class="relative w-full max-w-sm mx-4 rounded-2xl bg-white shadow-2xl border border-red-200 overflow-hidden logout-modal-enter">
      <!-- Top accent -->
      <div class="h-1 bg-red-600"></div>

      <div class="p-8 text-center">
        <!-- Icon -->
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-red-200 bg-red-50">
          <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" />
          </svg>
        </div>

        <h2 class="text-lg font-bold text-neutral-900 inline-flex items-center gap-1.5 flex-wrap justify-center">Log out of <img src="/logo-light.png" alt="developerOS" class="h-6 inline" />?</h2>
        <p class="mt-2 text-sm text-neutral-500 leading-relaxed">
          You'll need to sign in again to access<br />your projects and data.
        </p>

        <!-- Actions -->
        <div class="mt-7 flex flex-col gap-2.5">
          <button
            onclick={handleLogout}
            class="w-full rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-700"
          >
            Yes, log me out
          </button>
          <button
            onclick={() => (showLogoutModal = false)}
            class="w-full rounded-lg border border-red-200 bg-white px-4 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Session Changed Modal (cross-tab isolation) -->
{#if showSessionChangedModal}
  <div class="fixed inset-0 z-9999 flex items-center justify-center bg-black/50 backdrop-blur-sm">
    <div class="w-full max-w-sm mx-4 rounded-2xl border border-neutral-200 bg-white p-8 shadow-xl text-center">
      <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-100">
        <svg class="w-6 h-6 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
        </svg>
      </div>
      <h2 class="text-lg font-bold text-neutral-900">Session Changed</h2>
      <p class="mt-2 text-sm text-neutral-500 leading-relaxed">
        Another account signed in from this browser.<br />Please sign in again to continue.
      </p>
      <button
        onclick={handleSessionExpired}
        class="mt-6 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
      >
        Sign In
      </button>
    </div>
  </div>
{/if}

<Toaster />

<style>
  .logout-backdrop-enter {
    animation: fadeIn 0.2s ease-out both;
  }

  .logout-modal-enter {
    animation: modalSlideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes modalSlideUp {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
