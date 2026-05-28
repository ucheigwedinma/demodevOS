<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    BillingCycle,
    OrganizationSubscription,
    PlatformEdition,
    SubscriptionAddOn,
    SubscriptionEvent,
    SupportTier,
  } from "$lib/types";

  let subscription = $state<OrganizationSubscription | null>(null);
  let editions = $state<PlatformEdition[]>([]);
  let events = $state<SubscriptionEvent[]>([]);
  let addOnCatalog = $state<SubscriptionAddOn[]>([]);
  let loading = $state(true);

  // Drawer state
  type DrawerMode = "checkout" | "cancel" | "payment-method" | null;
  let drawerOpen = $state<DrawerMode>(null);

  // Checkout flow
  type CheckoutStep = "form" | "processing" | "success";
  let checkoutStep = $state<CheckoutStep>("form");
  let selectedEdition = $state<PlatformEdition | null>(null);
  let selectedCycle = $state<BillingCycle>("monthly");

  // Card form
  let cardForm = $state({
    card_number: "",
    expiry_month: "",
    expiry_year: "",
    cvc: "",
    cardholder_name: "",
  });

  // Cancel form
  let cancelReason = $state("");
  let cancelImmediately = $state(false);

  // Shared
  let saving = $state(false);
  let errors = $state<Record<string, string[]>>({});

  const supportLabels: Record<SupportTier, string> = {
    community: "Community",
    standard: "Standard",
    priority: "Priority",
    dedicated: "Dedicated",
  };

  function formatDate(d: string | null): string {
    if (!d) return "\u2014";
    return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  function formatLimit(v: number | null): string {
    return v === null ? "Unlimited" : String(v);
  }

  function formatPrice(p: string | null, currency: string): string {
    if (!p) return "Custom";
    return `${currency === "USD" ? "$" : currency} ${Number(p).toLocaleString()}`;
  }

  function usagePercent(used: number, max: number | null): number {
    if (max === null || max === 0) return 0;
    return Math.min(100, Math.round((used / max) * 100));
  }

  async function fetchData() {
    loading = true;
    try {
      const [sub, eds, evts, addOns] = await Promise.all([
        api.get<OrganizationSubscription>("/platform/subscription/").catch(() => null),
        api.get<{ results: PlatformEdition[] }>("/settings/platform-editions/").then((r) => r.results).catch(() => []),
        api.get<{ results: SubscriptionEvent[] }>("/platform/subscription/events/").then((r) => r.results).catch(() => []),
        api.get<{ results: SubscriptionAddOn[] }>("/platform/subscription/add-ons/").then((r) => r.results).catch(() => []),
      ]);
      subscription = sub;
      editions = eds;
      events = evts;
      addOnCatalog = addOns;
    } finally {
      loading = false;
    }
  }

  async function refreshEvents() {
    events = await api
      .get<{ results: SubscriptionEvent[] }>("/platform/subscription/events/")
      .then((r) => r.results)
      .catch(() => []);
  }

  let moduleAddOns = $derived(addOnCatalog.filter((a) => a.add_on_type === "module"));
  let storageAddOns = $derived(addOnCatalog.filter((a) => a.add_on_type === "storage"));

  function isAddOnActive(key: string): boolean {
    return !!subscription?.active_add_ons?.some((a) => a.add_on.key === key);
  }

  function activeAddOnId(key: string): number | null {
    const active = subscription?.active_add_ons?.find((a) => a.add_on.key === key);
    return active?.id ?? null;
  }

  let addOnSaving = $state<string | null>(null);

  async function purchaseAddOn(key: string) {
    addOnSaving = key;
    try {
      const result = await api.post<OrganizationSubscription>("/platform/subscription/add-ons/purchase/", {
        add_on_key: key,
      });
      subscription = result;
      toast.success("Add-on activated");
      await refreshEvents();
    } catch (e) {
      if (e instanceof ApiError) {
        toast.error("Failed to activate add-on", (e.data?.detail as string) || "Please try again.");
      } else {
        toast.error("Failed to activate add-on");
      }
    } finally {
      addOnSaving = null;
    }
  }

  async function cancelAddOn(activeId: number) {
    addOnSaving = String(activeId);
    try {
      const result = await api.post<OrganizationSubscription>(`/platform/subscription/add-ons/${activeId}/cancel/`, {});
      subscription = result;
      toast.success("Add-on removed");
      await refreshEvents();
    } catch (e) {
      if (e instanceof ApiError) {
        toast.error("Failed to remove add-on", (e.data?.detail as string) || "Please try again.");
      } else {
        toast.error("Failed to remove add-on");
      }
    } finally {
      addOnSaving = null;
    }
  }

  let currentEdition = $derived(editions.find((e) => e.id === subscription?.edition));

  let checkoutActionLabel = $derived.by(() => {
    if (!subscription || !selectedEdition) return "Subscribe";
    if (subscription.status === "expired" || subscription.status === "cancelled") return "Renew";
    if (subscription.status === "trialing") return "Activate";
    const cur = editions.find((e) => e.id === subscription!.edition);
    if (!cur) return "Subscribe";
    if (selectedEdition.tier_level > cur.tier_level) return "Upgrade";
    if (selectedEdition.tier_level < cur.tier_level) return "Downgrade";
    return "Update";
  });

  let checkoutPrice = $derived.by(() => {
    if (!selectedEdition) return "Custom";
    const price = selectedCycle === "annual" ? selectedEdition.annual_price : selectedEdition.monthly_price;
    return formatPrice(price, selectedEdition.currency);
  });

  function editionActionLabel(ed: PlatformEdition): string {
    if (!subscription) return "Subscribe";
    if (subscription.status === "expired" || subscription.status === "cancelled") return "Renew";
    if (subscription.status === "trialing") return "Activate";
    const cur = editions.find((e) => e.id === subscription!.edition);
    if (!cur) return "Subscribe";
    if (ed.tier_level > cur.tier_level) return "Upgrade";
    if (ed.tier_level < cur.tier_level) return "Downgrade";
    return "Update";
  }

  // ── Drawer openers ──────────────────────────────────────────────

  function resetCardForm() {
    cardForm = { card_number: "", expiry_month: "", expiry_year: "", cvc: "", cardholder_name: "" };
  }

  function openCheckout(edition: PlatformEdition) {
    selectedEdition = edition;
    selectedCycle = subscription?.billing_cycle ?? "monthly";
    resetCardForm();
    checkoutStep = "form";
    errors = {};
    drawerOpen = "checkout";
  }

  function openCancel() {
    cancelReason = "";
    cancelImmediately = false;
    errors = {};
    drawerOpen = "cancel";
  }

  function openPaymentMethod() {
    resetCardForm();
    errors = {};
    drawerOpen = "payment-method";
  }

  function closeDrawer() {
    drawerOpen = null;
    checkoutStep = "form";
    selectedEdition = null;
    errors = {};
  }

  // ── API actions ─────────────────────────────────────────────────

  async function handleCheckout() {
    if (!selectedEdition) return;
    saving = true;
    errors = {};
    checkoutStep = "processing";

    // Simulated 1.5s processing delay
    await new Promise((r) => setTimeout(r, 1500));

    try {
      const result = await api.post<OrganizationSubscription>("/platform/subscription/checkout/", {
        edition_key: selectedEdition.key,
        billing_cycle: selectedCycle,
        payment: {
          card_number: cardForm.card_number,
          expiry_month: parseInt(cardForm.expiry_month) || 0,
          expiry_year: parseInt(cardForm.expiry_year) || 0,
          cvc: cardForm.cvc,
          cardholder_name: cardForm.cardholder_name,
        },
      });
      subscription = result;
      checkoutStep = "success";
      toast.success("Subscription updated");
      await refreshEvents();
    } catch (e) {
      checkoutStep = "form";
      if (e instanceof ApiError) {
        errors = e.fieldErrors;
        const detail = (e.data?.detail as string) || Object.values(e.fieldErrors).flat()[0] || "Please check the form and try again.";
        toast.error("Checkout failed", detail);
      } else {
        toast.error("Checkout failed");
      }
    } finally {
      saving = false;
    }
  }

  async function handleCancel() {
    saving = true;
    errors = {};
    try {
      const result = await api.post<OrganizationSubscription>("/platform/subscription/cancel/", {
        reason: cancelReason,
        cancel_immediately: cancelImmediately,
      });
      subscription = result;
      toast.success("Subscription cancelled");
      closeDrawer();
      await refreshEvents();
    } catch (e) {
      if (e instanceof ApiError) {
        errors = e.fieldErrors;
        toast.error("Cancellation failed", (e.data?.detail as string) || "Please try again.");
      } else {
        toast.error("Cancellation failed");
      }
    } finally {
      saving = false;
    }
  }

  async function handleReactivate() {
    saving = true;
    try {
      const result = await api.post<OrganizationSubscription>("/platform/subscription/reactivate/", {});
      subscription = result;
      toast.success("Subscription reactivated");
      await refreshEvents();
    } catch (e) {
      if (e instanceof ApiError) {
        toast.error("Reactivation failed", (e.data?.detail as string) || "Please try again.");
      } else {
        toast.error("Reactivation failed");
      }
    } finally {
      saving = false;
    }
  }

  async function handlePaymentMethodUpdate() {
    saving = true;
    errors = {};
    try {
      const result = await api.post<OrganizationSubscription>("/platform/subscription/payment-method/", {
        payment: {
          card_number: cardForm.card_number,
          expiry_month: parseInt(cardForm.expiry_month) || 0,
          expiry_year: parseInt(cardForm.expiry_year) || 0,
          cvc: cardForm.cvc,
          cardholder_name: cardForm.cardholder_name,
        },
      });
      subscription = result;
      toast.success("Payment method updated");
      closeDrawer();
      await refreshEvents();
    } catch (e) {
      if (e instanceof ApiError) {
        errors = e.fieldErrors;
        toast.error("Update failed", (e.data?.detail as string) || "Please check the form.");
      } else {
        toast.error("Update failed");
      }
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    fetchData();
  });
</script>

<div class="max-w-5xl">
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-neutral-800 tracking-tight">Subscription</h1>
    <p class="mt-1 text-sm text-neutral-500">Manage your platform edition, usage, and billing</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else}
    <!-- Current Plan Card -->
    {#if subscription}
      <div class="bg-white border border-neutral-200 rounded-xl p-6 mb-6">
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-3 mb-1">
              <h2 class="text-lg font-bold text-neutral-800">{subscription.edition_name}</h2>
              <StatusBadge status={subscription.status} />
            </div>
            <p class="text-sm text-neutral-500">
              {subscription.billing_cycle === "annual" ? "Annual" : "Monthly"} billing
              {#if subscription.auto_renew}&middot; Auto-renews{/if}
              {#if subscription.payment_method_summary}&middot; {subscription.payment_method_summary}{/if}
            </p>
          </div>
          {#if currentEdition}
            <div class="text-right">
              <p class="text-2xl font-bold text-neutral-800 tabular-nums">
                {formatPrice(
                  subscription.billing_cycle === "annual" ? currentEdition.annual_price : currentEdition.monthly_price,
                  currentEdition.currency,
                )}
              </p>
              <p class="text-xs text-neutral-400">/{subscription.billing_cycle === "annual" ? "year" : "month"}</p>
            </div>
          {/if}
        </div>

        {#if subscription.current_period_start || subscription.current_period_end}
          <div class="mt-4 pt-4 border-t border-neutral-100 flex gap-8 text-sm">
            <div>
              <span class="text-neutral-400">Period start</span>
              <p class="font-medium text-neutral-700">{formatDate(subscription.current_period_start)}</p>
            </div>
            <div>
              <span class="text-neutral-400">Period end</span>
              <p class="font-medium text-neutral-700">{formatDate(subscription.current_period_end)}</p>
            </div>
            {#if subscription.trial_end}
              <div>
                <span class="text-neutral-400">Trial ends</span>
                <p class="font-medium text-neutral-700">{formatDate(subscription.trial_end)}</p>
              </div>
            {/if}
          </div>
        {/if}

        <!-- Action buttons -->
        <div class="mt-4 pt-4 border-t border-neutral-100 flex items-center gap-3">
          {#if subscription.status === "active" || subscription.status === "trialing"}
            <button
              onclick={openPaymentMethod}
              class="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Update Payment Method
            </button>
            <button
              onclick={openCancel}
              class="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
            >
              Cancel Subscription
            </button>
          {/if}
          {#if subscription.status === "cancelled"}
            <button
              onclick={handleReactivate}
              disabled={saving}
              class="px-4 py-2.5 text-sm font-medium text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {saving ? "Reactivating..." : "Reactivate Subscription"}
            </button>
          {/if}
          {#if subscription.status === "expired"}
            <button
              onclick={() => { if (currentEdition) openCheckout(currentEdition); }}
              class="px-4 py-2.5 text-sm font-medium text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 transition-colors"
            >
              Renew Subscription
            </button>
          {/if}
        </div>
      </div>

      <!-- Usage Meters -->
      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-white border border-neutral-200 rounded-xl p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-neutral-700">User Seats</h3>
            <span class="text-xs text-neutral-400 tabular-nums">
              {subscription.seats_used} / {formatLimit(subscription.effective_max_users)}
            </span>
          </div>
          {#if subscription.effective_max_users !== null}
            <div class="h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-neutral-800 rounded-full transition-all"
                style="width: {usagePercent(subscription.seats_used, subscription.effective_max_users)}%"
              ></div>
            </div>
          {:else}
            <div class="h-2 bg-neutral-100 rounded-full"></div>
          {/if}
        </div>

        <div class="bg-white border border-neutral-200 rounded-xl p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-neutral-700">Storage</h3>
            <span class="text-xs text-neutral-400 tabular-nums">
              {Number(subscription.storage_used_gb).toFixed(1)} GB / {subscription.effective_max_storage_gb !== null ? `${subscription.effective_max_storage_gb} GB` : "Unlimited"}
            </span>
          </div>
          {#if subscription.effective_max_storage_gb !== null && subscription.effective_max_storage_gb !== undefined}
            <div class="h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-neutral-800 rounded-full transition-all"
                style="width: {usagePercent(Number(subscription.storage_used_gb), subscription.effective_max_storage_gb)}%"
              ></div>
            </div>
          {:else}
            <div class="h-2 bg-neutral-100 rounded-full"></div>
          {/if}
        </div>
      </div>
    {:else}
      <!-- No subscription banner -->
      <div class="bg-white border border-neutral-200 rounded-xl p-6 mb-6">
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z" />
            </svg>
          </div>
          <div>
            <h2 class="text-sm font-bold text-neutral-800">No active subscription</h2>
            <p class="text-sm text-neutral-500">Review the available editions below to get started.</p>
          </div>
        </div>
      </div>
    {/if}

    <!-- Add-ons -->
    {#if addOnCatalog.length > 0 && subscription}
      <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden mb-6">
        <div class="px-6 py-4 border-b border-neutral-200">
          <h3 class="text-sm font-bold text-neutral-800">Add-ons</h3>
          <p class="text-xs text-neutral-400 mt-0.5">Extend your plan with additional modules and storage</p>
        </div>

        <!-- Module Add-ons -->
        {#if moduleAddOns.length > 0}
          <div class="px-6 py-4">
            <h4 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Modules</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {#each moduleAddOns as addOn}
                {@const active = isAddOnActive(addOn.key)}
                {@const aid = activeAddOnId(addOn.key)}
                <div class="relative rounded-xl border p-4 transition-colors {active ? 'border-neutral-800 bg-neutral-50/50' : 'border-neutral-200'}">
                  {#if active}
                    <div class="absolute top-0 left-0 w-1 h-full bg-neutral-800 rounded-l-xl"></div>
                  {/if}
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="flex items-center gap-2 mb-1">
                        <h5 class="text-sm font-semibold text-neutral-800">{addOn.name}</h5>
                        {#if active}
                          <span class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-neutral-800 text-white">Active</span>
                        {/if}
                      </div>
                      <p class="text-xs text-neutral-500 line-clamp-2">{addOn.description}</p>
                    </div>
                    <div class="text-right shrink-0">
                      <p class="text-sm font-bold text-neutral-800 tabular-nums">${Number(addOn.monthly_price).toLocaleString()}</p>
                      <p class="text-[10px] text-neutral-400">/month</p>
                    </div>
                  </div>
                  <div class="mt-3">
                    {#if active && aid !== null}
                      <button
                        onclick={() => cancelAddOn(aid!)}
                        disabled={addOnSaving === String(aid)}
                        class="px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                      >
                        {addOnSaving === String(aid) ? "Removing..." : "Remove"}
                      </button>
                    {:else}
                      <button
                        onclick={() => purchaseAddOn(addOn.key)}
                        disabled={addOnSaving === addOn.key}
                        class="px-3 py-1.5 text-xs font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                      >
                        {addOnSaving === addOn.key ? "Activating..." : "Add to Plan"}
                      </button>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Storage Add-ons -->
        {#if storageAddOns.length > 0}
          <div class="px-6 py-4 {moduleAddOns.length > 0 ? 'border-t border-neutral-100' : ''}">
            <h4 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Extra Storage</h4>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {#each storageAddOns as addOn}
                {@const active = isAddOnActive(addOn.key)}
                {@const aid = activeAddOnId(addOn.key)}
                <div class="relative rounded-xl border p-4 text-center transition-colors {active ? 'border-neutral-800 bg-neutral-50/50' : 'border-neutral-200'}">
                  {#if active}
                    <div class="absolute top-0 left-0 w-1 h-full bg-neutral-800 rounded-l-xl"></div>
                  {/if}
                  <p class="text-lg font-bold text-neutral-800 tabular-nums">{addOn.storage_gb} GB</p>
                  <p class="text-xs text-neutral-400 mb-3">${Number(addOn.monthly_price).toLocaleString()}/mo</p>
                  {#if active && aid !== null}
                    <button
                      onclick={() => cancelAddOn(aid!)}
                      disabled={addOnSaving === String(aid)}
                      class="w-full px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                    >
                      {addOnSaving === String(aid) ? "Removing..." : "Remove"}
                    </button>
                  {:else}
                    <button
                      onclick={() => purchaseAddOn(addOn.key)}
                      disabled={addOnSaving === addOn.key}
                      class="w-full px-3 py-1.5 text-xs font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                    >
                      {addOnSaving === addOn.key ? "Adding..." : "Add"}
                    </button>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Edition Comparison -->
    {#if editions.length > 0}
      <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden mb-6">
        <div class="px-6 py-4 border-b border-neutral-200">
          <h3 class="text-sm font-bold text-neutral-800">Available Editions</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200 bg-neutral-50/50">
                <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Feature</th>
                {#each editions as ed}
                  <th class="text-center px-5 py-3 font-medium text-xs uppercase tracking-wider {ed.id === subscription?.edition ? 'text-neutral-800' : 'text-neutral-500'}">
                    {ed.name}
                    {#if ed.id === subscription?.edition}
                      <span class="ml-1 text-[10px] font-semibold bg-neutral-800 text-white px-1.5 py-0.5 rounded-full">Current</span>
                    {/if}
                  </th>
                {/each}
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">Max Users</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{formatLimit(ed.max_users)}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700">Storage</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{ed.max_storage_gb !== null ? `${ed.max_storage_gb} GB` : "Unlimited"}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">API Rate Limit</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{ed.api_rate_limit_rpm !== null ? `${ed.api_rate_limit_rpm} rpm` : "Unlimited"}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">Max Projects</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{formatLimit(ed.max_projects)}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700">Data Retention</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{ed.data_retention_days !== null ? `${ed.data_retention_days} days` : "Unlimited"}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-700">Support</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600">{supportLabels[ed.support_tier]}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700">Response SLA</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{ed.support_response_hours !== null ? `${ed.support_response_hours}h` : "\u2014"}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-50 text-teal-700">Monthly</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center font-medium text-neutral-800 tabular-nums">{formatPrice(ed.monthly_price, ed.currency)}</td>
                {/each}
              </tr>
              <tr>
                <td class="px-5 py-3"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">Annual</span></td>
                {#each editions as ed}
                  <td class="px-5 py-3 text-center font-medium text-neutral-800 tabular-nums">{formatPrice(ed.annual_price, ed.currency)}</td>
                {/each}
              </tr>
              <!-- Action row -->
              <tr class="bg-neutral-50/30">
                <td class="px-5 py-4"></td>
                {#each editions as ed}
                  <td class="px-5 py-4 text-center">
                    {#if ed.id === subscription?.edition && (subscription?.status === "active" || subscription?.status === "trialing")}
                      <span class="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-neutral-100 text-neutral-500">
                        Current Plan
                      </span>
                    {:else}
                      <button
                        onclick={() => openCheckout(ed)}
                        class="inline-flex items-center px-4 py-1.5 rounded-lg text-xs font-semibold bg-neutral-800 text-white hover:bg-neutral-800 transition-colors"
                      >
                        {editionActionLabel(ed)}
                      </button>
                    {/if}
                  </td>
                {/each}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <!-- Subscription Event Timeline -->
    {#if events.length > 0}
      <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-neutral-200">
          <h3 class="text-sm font-bold text-neutral-800">Subscription History</h3>
        </div>
        <div class="divide-y divide-neutral-100">
          {#each events as evt}
            <div class="px-6 py-3.5 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-2 h-2 rounded-full bg-neutral-300 shrink-0"></div>
                <div>
                  <p class="text-sm font-medium text-neutral-800">
                    {evt.event_type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </p>
                  {#if evt.from_edition_name && evt.to_edition_name}
                    <p class="text-xs text-neutral-400">{evt.from_edition_name} &rarr; {evt.to_edition_name}</p>
                  {/if}
                </div>
              </div>
              <div class="text-right">
                <p class="text-xs text-neutral-400">{formatDate(evt.occurred_at)}</p>
                {#if evt.actor_email}
                  <p class="text-xs text-neutral-400">{evt.actor_email}</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- ─── Checkout Drawer ─────────────────────────────────────────── -->
{#if drawerOpen === "checkout" && selectedEdition}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-800">{checkoutActionLabel}</h2>
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <button onclick={closeDrawer} class="p-1 rounded hover:bg-neutral-100 transition-colors">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {#if checkoutStep === "form"}
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          <!-- Plan summary -->
          <div class="rounded-xl border border-neutral-200 bg-neutral-50/50 p-4">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-bold text-neutral-800">{selectedEdition.name}</h3>
              <span class="text-lg font-bold text-neutral-800 tabular-nums">{checkoutPrice}</span>
            </div>
            <p class="text-xs text-neutral-500 mb-3">
              {formatLimit(selectedEdition.max_users)} users &middot;
              {selectedEdition.max_storage_gb !== null ? `${selectedEdition.max_storage_gb} GB storage` : "Unlimited storage"} &middot;
              {supportLabels[selectedEdition.support_tier]} support
            </p>
            <!-- Billing cycle toggle -->
            <div class="flex rounded-lg border border-neutral-200 overflow-hidden">
              <button
                type="button"
                onclick={() => (selectedCycle = "monthly")}
                class="flex-1 px-3 py-2 text-xs font-medium transition-colors {selectedCycle === 'monthly' ? 'bg-neutral-800 text-white' : 'bg-white text-neutral-600 hover:bg-neutral-50'}"
              >Monthly</button>
              <button
                type="button"
                onclick={() => (selectedCycle = "annual")}
                class="flex-1 px-3 py-2 text-xs font-medium transition-colors {selectedCycle === 'annual' ? 'bg-neutral-800 text-white' : 'bg-white text-neutral-600 hover:bg-neutral-50'}"
              >Annual</button>
            </div>
          </div>

          <!-- Card form -->
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-neutral-700">Payment Details</h3>
            <div>
              <label for="ch-name" class="block text-xs font-medium text-neutral-500 mb-1">Cardholder Name</label>
              <input
                id="ch-name"
                type="text"
                bind:value={cardForm.cardholder_name}
                placeholder="John Doe"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
            <div>
              <label for="ch-num" class="block text-xs font-medium text-neutral-500 mb-1">Card Number</label>
              <input
                id="ch-num"
                type="text"
                bind:value={cardForm.card_number}
                placeholder="4242 4242 4242 4242"
                maxlength="19"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
            <div class="grid grid-cols-3 gap-3">
              <div>
                <label for="ch-mm" class="block text-xs font-medium text-neutral-500 mb-1">Month</label>
                <input
                  id="ch-mm"
                  type="text"
                  bind:value={cardForm.expiry_month}
                  placeholder="MM"
                  maxlength="2"
                  class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
                />
              </div>
              <div>
                <label for="ch-yy" class="block text-xs font-medium text-neutral-500 mb-1">Year</label>
                <input
                  id="ch-yy"
                  type="text"
                  bind:value={cardForm.expiry_year}
                  placeholder="YYYY"
                  maxlength="4"
                  class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
                />
              </div>
              <div>
                <label for="ch-cvc" class="block text-xs font-medium text-neutral-500 mb-1">CVC</label>
                <input
                  id="ch-cvc"
                  type="text"
                  bind:value={cardForm.cvc}
                  placeholder="123"
                  maxlength="4"
                  class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
                />
              </div>
            </div>
          </div>

          <!-- Errors -->
          {#if Object.keys(errors).length > 0}
            <div class="rounded-lg bg-red-50 border border-red-200 p-3 space-y-1">
              {#each Object.entries(errors) as [, messages]}
                {#each messages as msg}
                  <p class="text-xs text-red-600">{msg}</p>
                {/each}
              {/each}
            </div>
          {/if}
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
          <button onclick={closeDrawer} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors">Cancel</button>
          <button
            onclick={handleCheckout}
            disabled={saving}
            class="px-5 py-2.5 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {checkoutActionLabel} &mdash; {checkoutPrice}
          </button>
        </div>

      {:else if checkoutStep === "processing"}
        <div class="flex-1 flex flex-col items-center justify-center px-6">
          <div class="h-10 w-10 border-[3px] border-neutral-200 border-t-neutral-800 rounded-full animate-spin mb-6"></div>
          <p class="text-sm font-semibold text-neutral-800 mb-1">Processing payment...</p>
          <p class="text-xs text-neutral-400">Please wait while we verify your payment details</p>
        </div>

      {:else if checkoutStep === "success"}
        <div class="flex-1 flex flex-col items-center justify-center px-6">
          <div class="w-14 h-14 rounded-full bg-emerald-50 flex items-center justify-center mb-6">
            <svg class="w-7 h-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
          </div>
          <p class="text-lg font-bold text-neutral-800 mb-1">Payment Successful</p>
          <p class="text-sm text-neutral-500 mb-6 text-center">
            Your subscription to <span class="font-medium text-neutral-800">{selectedEdition.name}</span>
            ({selectedCycle}) is now active.
          </p>
          <button
            onclick={closeDrawer}
            class="px-5 py-2.5 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 transition-colors"
          >
            Done
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- ─── Cancel Drawer ───────────────────────────────────────────── -->
{#if drawerOpen === "cancel" && subscription}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-800">Cancel Subscription</h2>
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <button onclick={closeDrawer} class="p-1 rounded hover:bg-neutral-100 transition-colors">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        <!-- Warning -->
        <div class="rounded-xl bg-amber-50 border border-amber-200 p-4">
          <p class="text-sm font-semibold text-amber-800 mb-1">Are you sure?</p>
          <p class="text-xs text-amber-700">
            Cancelling will end your access to {subscription.edition_name} features.
            {#if !cancelImmediately && subscription.current_period_end}
              Your subscription will remain active until {formatDate(subscription.current_period_end)}.
            {/if}
          </p>
        </div>

        <!-- Reason -->
        <div>
          <label for="cancel-reason" class="block text-xs font-medium text-neutral-500 mb-1">Reason (optional)</label>
          <textarea
            id="cancel-reason"
            bind:value={cancelReason}
            rows={3}
            placeholder="Let us know why you're cancelling..."
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none transition-shadow"
          ></textarea>
        </div>

        <!-- Cancel immediately -->
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            bind:checked={cancelImmediately}
            class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800"
          />
          <span class="text-sm text-neutral-700">Cancel immediately (lose access now)</span>
        </label>
      </div>

      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={closeDrawer} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors">
          Keep Subscription
        </button>
        <button
          onclick={handleCancel}
          disabled={saving}
          class="px-5 py-2.5 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          {saving ? "Cancelling..." : "Confirm Cancellation"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ─── Payment Method Drawer ───────────────────────────────────── -->
{#if drawerOpen === "payment-method" && subscription}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-800">Update Payment Method</h2>
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <button onclick={closeDrawer} class="p-1 rounded hover:bg-neutral-100 transition-colors">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {#if subscription.payment_method_summary}
          <div class="rounded-lg bg-neutral-50 border border-neutral-200 p-3 text-sm text-neutral-600">
            Current: <span class="font-medium text-neutral-800">{subscription.payment_method_summary}</span>
          </div>
        {/if}

        <div class="space-y-4">
          <h3 class="text-sm font-semibold text-neutral-700">New Payment Details</h3>
          <div>
            <label for="pm-name" class="block text-xs font-medium text-neutral-500 mb-1">Cardholder Name</label>
            <input
              id="pm-name"
              type="text"
              bind:value={cardForm.cardholder_name}
              placeholder="John Doe"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
          </div>
          <div>
            <label for="pm-num" class="block text-xs font-medium text-neutral-500 mb-1">Card Number</label>
            <input
              id="pm-num"
              type="text"
              bind:value={cardForm.card_number}
              placeholder="4242 4242 4242 4242"
              maxlength="19"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label for="pm-mm" class="block text-xs font-medium text-neutral-500 mb-1">Month</label>
              <input
                id="pm-mm"
                type="text"
                bind:value={cardForm.expiry_month}
                placeholder="MM"
                maxlength="2"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
            <div>
              <label for="pm-yy" class="block text-xs font-medium text-neutral-500 mb-1">Year</label>
              <input
                id="pm-yy"
                type="text"
                bind:value={cardForm.expiry_year}
                placeholder="YYYY"
                maxlength="4"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
            <div>
              <label for="pm-cvc" class="block text-xs font-medium text-neutral-500 mb-1">CVC</label>
              <input
                id="pm-cvc"
                type="text"
                bind:value={cardForm.cvc}
                placeholder="123"
                maxlength="4"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm text-center focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
          </div>
        </div>

        <!-- Errors -->
        {#if Object.keys(errors).length > 0}
          <div class="rounded-lg bg-red-50 border border-red-200 p-3 space-y-1">
            {#each Object.entries(errors) as [, messages]}
              {#each messages as msg}
                <p class="text-xs text-red-600">{msg}</p>
              {/each}
            {/each}
          </div>
        {/if}
      </div>

      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={closeDrawer} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors">
          Cancel
        </button>
        <button
          onclick={handlePaymentMethodUpdate}
          disabled={saving}
          class="px-5 py-2.5 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Updating..." : "Update Payment Method"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
