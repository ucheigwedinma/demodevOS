<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { onboarding } from "$lib/stores/onboarding.svelte";

  interface Edition {
    id: number;
    key: string;
    name: string;
    tier_level: number;
    is_custom: boolean;
    description: string;
    max_users: number | null;
    max_projects: number | null;
    monthly_price: string | null;
    annual_price: string | null;
    support_tier: string;
  }

  const TIER_LABELS: Record<string, string> = {
    essentials: "STARTUP",
    growth: "EXPANDING",
    scale: "ENTERPRISE",
    custom: "TAILORED",
  };

  const TIER_FEATURES: Record<string, string[]> = {
    essentials: [
      "8 Users max",
      "5 Projects max",
      "Core Modules",
      "Community Support",
    ],
    growth: [
      "Everything in Essentials +",
      "20 Users max",
      "15 Projects max",
      "Finance & HR",
    ],
    scale: [
      "Everything in Growth +",
      "Unlimited Users",
      "Unlimited Projects",
      "CRM & Tenants",
    ],
    custom: [
      "Min. 6 Modules",
      "Min. 20 Users",
      "Asset Management",
      "Dedicated Support",
    ],
  };

  let editions = $state<Edition[]>([]);
  let billing = $state<"monthly" | "annual">("monthly");
  let loading = $state(true);
  let startingTrial = $state<string | null>(null);

  onMount(async () => {
    try {
      const res = await api.get<{ results: Edition[] } | Edition[]>(
        "/settings/platform-editions/"
      );
      editions = Array.isArray(res) ? res : res.results;
      editions.sort((a, b) => a.tier_level - b.tier_level);
    } catch {
      editions = [];
    }
    loading = false;
  });

  function formatPrice(edition: Edition): string {
    if (billing === "monthly") {
      if (!edition.monthly_price) return "Custom";
      const num = parseFloat(edition.monthly_price);
      return `$${num % 1 === 0 ? num.toFixed(0) : num.toFixed(2)}`;
    }
    // Annual: show per-month equivalent (total / 12)
    if (!edition.annual_price) return "Custom";
    const perMonth = parseFloat(edition.annual_price) / 12;
    return `$${perMonth % 1 === 0 ? perMonth.toFixed(0) : perMonth.toFixed(0)}`;
  }

  function hasPrice(edition: Edition): boolean {
    const price = billing === "monthly" ? edition.monthly_price : edition.annual_price;
    return !!price;
  }

  async function handleStartTrial(editionKey: string) {
    startingTrial = editionKey;
    await onboarding.startTrial(editionKey);
    startingTrial = null;
  }

  function handleRequestQuote() {
    window.open("mailto:hello@developeros.com?subject=Custom%20Plan%20Enquiry", "_blank");
  }

  function handleMaybeLater() {
    onboarding.dismissTrialPrompt();
  }
</script>

<div class="fixed inset-0 z-50 flex flex-col bg-white picker-enter">
  <!-- Top bar with logo -->
  <div class="shrink-0 px-6 py-5">
    <span class="font-semibold text-neutral-900 text-xl">developer</span><span class="font-bold text-neutral-400 text-xl">OS</span>
  </div>

  <!-- Scrollable content -->
  <div class="flex-1 overflow-y-auto">
    <div class="mx-auto max-w-6xl px-6 pb-12 sm:pb-16">
      <!-- Header -->
      <div class="text-center mb-12">
        <h1 class="text-3xl sm:text-4xl font-bold text-neutral-900 tracking-tight">
          Choose your plan
        </h1>
        <p class="mt-3 text-neutral-500 text-base max-w-lg mx-auto">
          Start with a 14-day free trial. No credit card required.
        </p>

        <!-- Billing toggle -->
        <div class="mt-8 inline-flex items-center rounded-full bg-neutral-100 p-1">
          <button
            onclick={() => (billing = "monthly")}
            class="rounded-full px-5 py-2 text-sm font-medium transition-all {billing === 'monthly' ? 'bg-neutral-900 text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}"
          >
            Monthly
          </button>
          <button
            onclick={() => (billing = "annual")}
            class="rounded-full px-5 py-2 text-sm font-medium transition-all {billing === 'annual' ? 'bg-neutral-900 text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}"
          >
            Annual
            <span class="ml-1 text-xs {billing === 'annual' ? 'text-neutral-300' : 'text-neutral-400'}">Save ~17%</span>
          </button>
        </div>
      </div>

      <!-- Pricing cards -->
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="h-8 w-8 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else}
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {#each editions as edition (edition.id)}
            {@const isFeatured = edition.key === "growth"}
            {@const isCustom = edition.is_custom}
            <div
              class="relative flex flex-col rounded-2xl border p-6 transition-all {isFeatured
                ? 'border-neutral-900 bg-neutral-900 text-white shadow-xl ring-1 ring-neutral-900 scale-[1.02]'
                : 'border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-md'}"
            >
              <!-- Featured badge -->
              {#if isFeatured}
                <div class="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span class="rounded-full bg-white px-3 py-1 text-xs font-bold text-neutral-900 shadow-sm">
                    MOST POPULAR
                  </span>
                </div>
              {/if}

              <!-- Tier label -->
              <p class="text-[11px] font-semibold tracking-widest {isFeatured ? 'text-neutral-400' : 'text-neutral-400'}">
                {TIER_LABELS[edition.key] ?? edition.key.toUpperCase()}
              </p>

              <!-- Edition name -->
              <h3 class="mt-2 text-xl font-bold {isFeatured ? 'text-white' : 'text-neutral-900'}">
                {edition.name}
              </h3>

              <!-- Price -->
              <div class="mt-4">
                <div class="flex items-baseline gap-1.5">
                  <span class="text-3xl font-bold {isFeatured ? 'text-white' : 'text-neutral-900'}">
                    {formatPrice(edition)}
                  </span>
                  {#if hasPrice(edition)}
                    <span class="text-xs leading-tight {isFeatured ? 'text-neutral-400' : 'text-neutral-500'}">
                      per<br />organisation/month{#if billing === "annual"},<br />billed annually{/if}
                    </span>
                  {/if}
                </div>
              </div>

              <!-- Description -->
              <p class="mt-3 text-sm leading-relaxed {isFeatured ? 'text-neutral-300' : 'text-neutral-500'}">
                {edition.description}
              </p>

              <!-- Divider -->
              <div class="my-5 border-t {isFeatured ? 'border-neutral-700' : 'border-neutral-100'}"></div>

              <!-- Features -->
              <ul class="flex-1 space-y-3">
                {#each TIER_FEATURES[edition.key] ?? [] as feature}
                  <li class="flex items-start gap-2.5">
                    <svg class="mt-0.5 h-4 w-4 shrink-0 {isFeatured ? 'text-neutral-400' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                    <span class="text-sm {isFeatured ? 'text-neutral-200' : 'text-neutral-600'}">{feature}</span>
                  </li>
                {/each}
              </ul>

              <!-- CTA -->
              <div class="mt-6">
                {#if isCustom}
                  <button
                    onclick={handleRequestQuote}
                    class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-50"
                  >
                    Request a Quote
                  </button>
                {:else if isFeatured}
                  <button
                    onclick={() => handleStartTrial(edition.key)}
                    disabled={startingTrial === edition.key}
                    class="w-full rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-100 disabled:opacity-60"
                  >
                    {startingTrial === edition.key ? "Starting..." : "Start Free Trial"}
                  </button>
                {:else}
                  <button
                    onclick={() => handleStartTrial(edition.key)}
                    disabled={startingTrial === edition.key}
                    class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
                  >
                    {startingTrial === edition.key ? "Starting..." : "Start Free Trial"}
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Maybe later -->
      <div class="mt-10 text-center">
        <button
          onclick={handleMaybeLater}
          class="text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          Maybe later
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .picker-enter {
    animation: pickerFadeIn 0.4s ease-out both;
  }

  @keyframes pickerFadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
</style>
