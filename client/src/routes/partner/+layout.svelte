<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { ApiError, api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import type { PartnerPortalContextResponse } from "$lib/types";

  let { children } = $props();

  type PartnerNavItem = {
    href: string;
    label: string;
  };

  const navItems: PartnerNavItem[] = [
    { href: "/partner", label: "Dashboard" },
    { href: "/partner/documents", label: "Data Room" },
    { href: "/partner/communication", label: "Communication" },
    { href: "/partner/approvals", label: "Approvals" },
    { href: "/partner/financial", label: "Financials" },
    { href: "/partner/compliance", label: "Compliance" },
    { href: "/partner/notifications", label: "Notifications" },
    { href: "/partner/profile", label: "Profile & Legal" },
  ];

  let context = $state<PartnerPortalContextResponse | null>(null);
  let checkingSession = $state(true);
  let sessionError = $state("");
  let showLogoutModal = $state(false);
  let guardPathname = "";

  const isLoginRoute = $derived($page.url.pathname === "/partner/login");
  const isLegalRoute = $derived($page.url.pathname === "/partner/legal");
  const isForgotPasswordRoute = $derived($page.url.pathname === "/partner/forgot-password");
  const isResetPasswordRoute = $derived($page.url.pathname === "/partner/reset-password");
  const isAuthRoute = $derived(isLoginRoute || isLegalRoute || isForgotPasswordRoute || isResetPasswordRoute);

  function isPartnerAuthPath(pathname: string): boolean {
    return (
      pathname === "/partner/login" ||
      pathname === "/partner/legal" ||
      pathname === "/partner/forgot-password" ||
      pathname === "/partner/reset-password"
    );
  }

  function clearTokens() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }

  function isNavActive(href: string, pathname: string): boolean {
    if (href === "/partner") return pathname === "/partner";
    return pathname.startsWith(href);
  }

  async function handleLogout() {
    clearTokens();
    context = null;
    showLogoutModal = false;
    await goto("/partner/login");
  }

  async function runSessionGuard(pathname: string) {
    checkingSession = true;
    sessionError = "";

    if (pathname === "/partner/forgot-password" || pathname === "/partner/reset-password") {
      checkingSession = false;
      sessionError = "";
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
      context = null;
      checkingSession = false;
      if (!isPartnerAuthPath(pathname)) {
        await goto("/partner/login");
      }
      return;
    }

    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;

      if (!ctx.legal.accepted && pathname !== "/partner/legal") {
        await goto("/partner/legal");
        return;
      }

      if (ctx.legal.accepted && (pathname === "/partner/login" || pathname === "/partner/legal")) {
        await goto("/partner");
        return;
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearTokens();
        context = null;
        if (!isPartnerAuthPath(pathname)) {
          await goto("/partner/login");
          return;
        }
      }
      sessionError = parsePortalError(error, "Could not initialize portal session.");
    } finally {
      checkingSession = false;
    }
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    const pathname = $page.url.pathname;
    if (!pathname.startsWith("/partner")) return;
    if (guardPathname === pathname) return;
    guardPathname = pathname;
    runSessionGuard(pathname);
  });
</script>

{#if checkingSession}
  <div class="flex min-h-screen items-center justify-center bg-neutral-50">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if isAuthRoute}
  <div class="min-h-screen bg-neutral-950 text-neutral-100">
    {@render children()}
  </div>
{:else}
  <div class="min-h-screen bg-linear-to-b from-neutral-100 to-neutral-50 text-neutral-900">
    <header class="sticky top-0 z-20 border-b border-neutral-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <div class="flex min-w-0 items-center gap-4">
          <a href="/partner" class="inline-flex h-9 items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-900">
            <img src="/logo-light.png" alt="developerOS" class="h-6" />
            <span class="hidden sm:inline">Partner Portal</span>
          </a>
          <nav class="hidden items-center gap-1 lg:flex">
            {#each navItems as item}
              <a
                href={item.href}
                class="rounded-lg px-3 py-2 text-sm font-medium transition-colors {isNavActive(item.href, $page.url.pathname)
                  ? 'bg-neutral-900 text-white'
                  : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>

        <div class="flex items-center gap-3">
          {#if context?.portal_roles?.length}
            <span class="hidden rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-700 sm:inline">
              {context.portal_roles[0].replaceAll("_", " ")}
            </span>
          {/if}
          <button
            onclick={() => (showLogoutModal = true)}
            class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100"
          >
            Log out
          </button>
        </div>
      </div>

      <div class="border-t border-neutral-100 px-4 py-2 lg:hidden">
        <div class="mx-auto flex w-full max-w-7xl gap-2 overflow-x-auto pb-1">
          {#each navItems as item}
            <a
              href={item.href}
              class="whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors {isNavActive(item.href, $page.url.pathname)
                ? 'bg-neutral-900 text-white'
                : 'bg-neutral-100 text-neutral-600'}"
            >
              {item.label}
            </a>
          {/each}
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-7xl px-6 py-8">
      {#if sessionError}
        <div class="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {sessionError}
        </div>
      {/if}
      {@render children()}
    </main>
  </div>
{/if}

{#if showLogoutModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm logout-backdrop-enter"
      onclick={() => (showLogoutModal = false)}
      aria-label="Close modal"
    ></button>

    <div class="relative mx-4 w-full max-w-sm overflow-hidden rounded-2xl border border-red-200 bg-white shadow-2xl logout-modal-enter">
      <div class="h-1 bg-red-600"></div>

      <div class="p-8 text-center">
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-red-200 bg-red-50">
          <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" />
          </svg>
        </div>

        <h2 class="inline-flex flex-wrap items-center justify-center gap-1.5 text-lg font-bold text-neutral-900">
          Log out of <img src="/logo-light.png" alt="developerOS" class="inline h-6" />?
        </h2>
        <p class="mt-2 text-sm leading-relaxed text-neutral-500">
          You will need to sign in again to access your partner workspace.
        </p>

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

<style>
  .logout-backdrop-enter {
    animation: fadeIn 0.2s ease-out both;
  }

  .logout-modal-enter {
    animation: modalSlideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
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
