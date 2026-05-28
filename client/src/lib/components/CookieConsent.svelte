<script lang="ts">
  import { onMount } from "svelte";
  import { fly, fade } from "svelte/transition";
  import { toast } from "$lib/stores/toast.svelte";

  interface CookieCategory {
    id: string;
    name: string;
    description: string;
    isEssential?: boolean;
  }

  let {
    categories = [
      {
        id: "essential",
        name: "Essential Cookies",
        description: "Required for core website functionality, such as navigation and security.",
        isEssential: true,
      },
      {
        id: "analytics",
        name: "Analytics Cookies",
        description: "Track anonymous usage to improve our services.",
      },
      {
        id: "marketing",
        name: "Marketing Cookies",
        description: "Enable personalized ads across websites.",
      },
    ],
    cookiePolicyUrl = "/cookies",
    inverted = false,
    onaccept,
    ondecline,
  }: {
    categories?: CookieCategory[];
    cookiePolicyUrl?: string;
    inverted?: boolean;
    onaccept?: (preferences: boolean[]) => void;
    ondecline?: () => void;
  } = $props();

  const STORAGE_KEY = "cookie_preferences";
  const CONSENT_KEY = "cookie_consent_given";

  let mounted = $state(false);
  let showBanner = $state(false);
  let showDialog = $state(false);
  const defaultPreferences = $derived.by(() => categories.map((c) => !!c.isEssential));
  let preferences: boolean[] = $state([]);

  $effect(() => {
    if (!mounted) {
      preferences = [...defaultPreferences];
    }
  });

  onMount(() => {
    mounted = true;

    try {
      const consentGiven = localStorage.getItem(CONSENT_KEY) === "true";
      const stored = localStorage.getItem(STORAGE_KEY);

      if (consentGiven && stored) {
        const parsed = JSON.parse(stored) as boolean[];
        if (Array.isArray(parsed) && parsed.length === categories.length) {
          preferences = parsed;
          onaccept?.(parsed);
          return;
        }
      }

      showBanner = true;
    } catch {
      showBanner = true;
    }
  });

  function save(prefs: boolean[]) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
      localStorage.setItem(CONSENT_KEY, "true");
    } catch {
      // localStorage unavailable
    }
    showBanner = false;
    showDialog = false;
    onaccept?.(prefs);
  }

  function acceptAll() {
    const all = categories.map(() => true);
    preferences = all;
    save(all);
    toast.success("Preferences saved", "All cookies accepted.");
  }

  function rejectAll() {
    const essential = categories.map((c) => !!c.isEssential);
    preferences = essential;
    save(essential);
    ondecline?.();
    toast.success("Preferences saved", "Only essential cookies enabled.");
  }

  function saveCustom() {
    save(preferences);
    const accepted = categories.filter((_, i) => preferences[i]).map((c) => c.name);
    toast.success("Preferences saved", `Enabled: ${accepted.join(", ")}.`);
  }

  function toggle(index: number) {
    if (categories[index]?.isEssential) return;
    preferences = preferences.map((value, i) => (i === index ? !value : value));
  }

  function handleKeydown(e: KeyboardEvent) {
    if (showDialog && e.key === "Escape") showDialog = false;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if mounted && showBanner}
  <div
    class="fixed bottom-0 left-0 right-0 sm:left-4 sm:bottom-4 z-50 w-full sm:max-w-md"
    transition:fly={{ y: 100, duration: 400 }}
  >
    <div class="m-3 rounded-xl border shadow-2xl {inverted ? 'border-neutral-700 bg-neutral-900' : 'border-neutral-200 bg-white'}">
      <!-- Header -->
      <div class="flex items-center gap-3 p-6 pb-4">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg {inverted ? 'bg-neutral-800' : 'bg-neutral-100'}">
          <svg class="h-5 w-5 {inverted ? 'text-neutral-400' : 'text-neutral-600'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8.25v-1.5m0 1.5c-1.355 0-2.697.056-4.024.166C6.845 8.51 6 9.473 6 10.608v2.513m6-4.871c1.355 0 2.697.056 4.024.166C17.155 8.51 18 9.473 18 10.608v2.513M15 8.25v-1.5m-6 1.5v-1.5m12 9.75-1.5.75a3.354 3.354 0 0 1-3 0 3.354 3.354 0 0 0-3 0 3.354 3.354 0 0 1-3 0 3.354 3.354 0 0 0-3 0 3.354 3.354 0 0 1-3 0L3 16.5m15-3.379a48.474 48.474 0 0 0-6-.371c-2.032 0-4.034.126-6 .371m12 0c.39.049.777.102 1.163.16 1.07.16 1.837 1.094 1.837 2.175v5.169c0 .621-.504 1.125-1.125 1.125H4.125A1.125 1.125 0 0 1 3 20.625v-5.17c0-1.08.768-2.014 1.837-2.174A47.78 47.78 0 0 1 6 13.12" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold {inverted ? 'text-white' : 'text-neutral-900'}">Cookie Preferences</h2>
      </div>

      <!-- Body -->
      <div class="px-6 pb-4">
        <p class="text-sm leading-relaxed {inverted ? 'text-neutral-400' : 'text-neutral-500'}">
          We use cookies to enhance your experience, personalize content, and analyze traffic.
        </p>
        <a
          href={cookiePolicyUrl}
          class="mt-3 inline-flex items-center gap-1 text-xs font-medium transition-colors hover:underline {inverted ? 'text-white' : 'text-neutral-900'}"
        >
          Cookie Policy
          <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </a>
      </div>

      <!-- Actions -->
      <div class="flex flex-col gap-3 border-t p-4 sm:flex-row rounded-b-xl {inverted ? 'border-neutral-700 bg-neutral-800' : 'border-neutral-100 bg-neutral-50'}">
        <button
          onclick={acceptAll}
          class="w-full rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors sm:flex-1 {inverted ? 'bg-white text-neutral-900 hover:bg-neutral-100' : 'bg-neutral-900 text-white hover:bg-neutral-800'}"
        >
          Accept All
        </button>
        <button
          onclick={() => (showDialog = true)}
          class="w-full rounded-lg border px-4 py-2.5 text-sm font-semibold transition-colors sm:flex-1 {inverted ? 'border-neutral-600 bg-neutral-700 text-neutral-300 hover:bg-neutral-600' : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
        >
          Customize
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Customize Dialog -->
{#if showDialog}
  <div class="fixed inset-0 z-200 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 cursor-default bg-black/40 backdrop-blur-sm"
      onclick={() => (showDialog = false)}
      tabindex="-1"
      aria-label="Close dialog"
      transition:fade={{ duration: 200 }}
    ></button>

    <!-- Panel -->
    <div
      class="relative w-full max-w-[500px] rounded-2xl border border-neutral-200 bg-white shadow-2xl flex flex-col max-h-[85vh] dialog-enter"
      role="dialog"
      aria-modal="true"
      aria-label="Manage Cookies"
    >
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4 shrink-0">
        <div>
          <h2 class="text-xl font-semibold text-neutral-900">Manage Cookies</h2>
          <p class="mt-1 text-sm text-neutral-500">Customize your cookie preferences below.</p>
        </div>
        <button
          onclick={() => (showDialog = false)}
          class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          aria-label="Close"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Categories -->
      <div class="space-y-4 overflow-y-auto px-6 py-6">
        {#each categories as category, i}
          {@const switchId = `cookie-${i}`}
          <div
            class="rounded-xl border p-4 transition-all duration-200 {preferences[i]
              ? 'border-neutral-300 bg-neutral-50'
              : 'border-neutral-200 hover:border-neutral-300'}"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="flex h-9 w-9 items-center justify-center rounded-lg {preferences[i] ? 'bg-neutral-200' : 'bg-neutral-100'}">
                  <svg class="h-4 w-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 8.25v-1.5m0 1.5c-1.355 0-2.697.056-4.024.166C6.845 8.51 6 9.473 6 10.608v2.513m6-4.871c1.355 0 2.697.056 4.024.166C17.155 8.51 18 9.473 18 10.608v2.513M15 8.25v-1.5m-6 1.5v-1.5m12 9.75-1.5.75a3.354 3.354 0 0 1-3 0 3.354 3.354 0 0 0-3 0 3.354 3.354 0 0 1-3 0 3.354 3.354 0 0 0-3 0 3.354 3.354 0 0 1-3 0L3 16.5m15-3.379a48.474 48.474 0 0 0-6-.371c-2.032 0-4.034.126-6 .371m12 0c.39.049.777.102 1.163.16 1.07.16 1.837 1.094 1.837 2.175v5.169c0 .621-.504 1.125-1.125 1.125H4.125A1.125 1.125 0 0 1 3 20.625v-5.17c0-1.08.768-2.014 1.837-2.174A47.78 47.78 0 0 1 6 13.12" />
                  </svg>
                </div>
                <div>
                  <label for={switchId} class="text-sm font-semibold text-neutral-900 cursor-pointer">
                    {category.name}
                  </label>
                  {#if category.isEssential}
                    <span class="ml-2 inline-flex items-center rounded-full bg-neutral-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-600">
                      Required
                    </span>
                  {/if}
                </div>
              </div>

              <!-- Toggle Switch -->
              <button
                id={switchId}
                role="switch"
                aria-checked={preferences[i]}
                aria-label={`Toggle ${category.name}`}
                disabled={category.isEssential}
                onclick={() => toggle(i)}
                class="relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:ring-offset-2 disabled:opacity-50 {preferences[i] ? 'bg-neutral-900' : 'bg-neutral-300'}"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 {preferences[i] ? 'translate-x-5' : 'translate-x-0'}"
                ></span>
              </button>
            </div>
            <p class="mt-3 text-sm leading-relaxed text-neutral-500">{category.description}</p>
          </div>
        {/each}
      </div>

      <!-- Footer -->
      <div class="flex flex-col-reverse gap-3 border-t border-neutral-100 bg-neutral-50 px-6 py-4 sm:flex-row sm:justify-end rounded-b-2xl shrink-0">
        <button
          onclick={rejectAll}
          class="min-w-[120px] rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          Reject All
        </button>
        <button
          onclick={saveCustom}
          class="min-w-[140px] rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
        >
          Save Preferences
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .dialog-enter {
    animation: dialogIn 0.2s ease-out;
  }

  @keyframes dialogIn {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(8px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
