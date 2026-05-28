<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { LOCALES, type LocaleCode } from "$lib/i18n/locales";
  import type {
    SystemPreferences,
    SystemPreferencesRole,
    LandingPageOption,
    CurrencyOption,
  } from "$lib/types";

  function resolveCurrencySymbol(code: string): string {
    try {
      const parts = new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: code,
        currencyDisplay: "narrowSymbol",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).formatToParts(0);
      return parts.find((part) => part.type === "currency")?.value ?? code;
    } catch {
      return code;
    }
  }

  const symbolMap: Record<string, string> = {};

  function getCurrencySymbol(code: string): string {
    const normalized = code.trim().toUpperCase();
    if (!normalized) return "";
    if (!symbolMap[normalized]) {
      symbolMap[normalized] = resolveCurrencySymbol(normalized);
    }
    return symbolMap[normalized];
  }

  function normalizeCurrencyOptions(options: CurrencyOption[]): CurrencyOption[] {
    const seen = new Set<string>();
    const normalized: CurrencyOption[] = [];
    for (const option of options) {
      const code = option.code.trim().toUpperCase();
      if (!code || seen.has(code)) continue;
      seen.add(code);
      normalized.push({
        code,
        label: option.label?.trim() || code,
      });
    }
    return normalized;
  }

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<SystemPreferences>>({});
  let roles = $state<SystemPreferencesRole[]>([]);
  let landingPages = $state<LandingPageOption[]>([]);
  let currencyOptions = $state<CurrencyOption[]>([]);

  const DATE_FORMAT_OPTIONS = [
    { value: "DD/MM/YYYY", label: "DD/MM/YYYY", preview: "25/03/2026" },
    { value: "MM/DD/YYYY", label: "MM/DD/YYYY", preview: "03/25/2026" },
    { value: "YYYY-MM-DD", label: "YYYY-MM-DD", preview: "2026-03-25" },
  ];

  const NUMBER_FORMAT_OPTIONS = [
    { value: "1,234.56", label: "1,234.56", preview: "1,234,567.89" },
    { value: "1.234,56", label: "1.234,56", preview: "1.234.567,89" },
  ];

  function getDefaultCurrencyCode(): string {
    const formCode = form.default_currency?.trim().toUpperCase();
    if (formCode) return formCode;
    if (currencyOptions.length > 0) return currencyOptions[0].code;
    return currency.config.code;
  }

  function ensureCurrentCurrencyOption(code: string | null | undefined) {
    const normalized = code?.trim().toUpperCase();
    if (!normalized) return;
    if (currencyOptions.some((option) => option.code === normalized)) return;
    currencyOptions = [...currencyOptions, { code: normalized, label: normalized }];
  }

  function initializeCurrencyOptions(data: SystemPreferences) {
    currencyOptions = normalizeCurrencyOptions(data.available_currencies ?? []);
    ensureCurrentCurrencyOption(data.default_currency);
    if (currencyOptions.length === 0) {
      currencyOptions = [{ code: currency.config.code, label: currency.config.code }];
    }
  }

  async function loadPreferences() {
    try {
      const data = await api.get<SystemPreferences>("/settings/preferences/");
      roles = data.available_roles;
      landingPages = data.available_landing_pages;
      initializeCurrencyOptions(data);
      form = data;
      form.default_currency = data.default_currency?.trim().toUpperCase() || getDefaultCurrencyCode();
    } catch {
      toast.error("Load failed", "Could not load system preferences.");
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      const {
        id,
        created_at,
        updated_at,
        available_roles,
        available_landing_pages,
        available_currencies,
        ...payload
      } = form as SystemPreferences;
      await api.patch<SystemPreferences>("/settings/preferences/", payload);
      const selectedCurrency = payload.default_currency?.trim().toUpperCase() || getDefaultCurrencyCode();
      currency.update({
        code: selectedCurrency,
        symbol: getCurrencySymbol(selectedCurrency),
        position: payload.currency_position,
        decimals: payload.currency_decimal_places,
      });
      toast.success("Saved", "System preferences updated successfully.");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  function setDashboardRole(slug: string, page: string) {
    const current = { ...(form.dashboard_by_role ?? {}) };
    if (page) {
      current[slug] = page;
    } else {
      delete current[slug];
    }
    form.dashboard_by_role = current;
  }

  $effect(() => {
    loadPreferences();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">System Preferences</h2>
      <p class="mt-1 text-sm text-neutral-500">Configure organization-wide display, localization, and dashboard defaults.</p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <div class="space-y-6 max-w-3xl">

    <!-- Dashboard Defaults -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-1">Dashboard Defaults</h3>
      <p class="text-xs text-neutral-500 mb-5">Set the default landing page for each role when users log in.</p>

      {#if roles.length > 0}
        <div class="space-y-3">
          {#each roles as role}
            <div class="flex items-center gap-4">
              <span class="text-sm text-neutral-700 w-48 shrink-0 truncate" title={role.name}>{role.name}</span>
              <select
                value={form.dashboard_by_role?.[role.slug] ?? ""}
                onchange={(e) => setDashboardRole(role.slug, (e.target as HTMLSelectElement).value)}
                class="flex-1 rounded-lg border border-neutral-300 bg-white px-3.5 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              >
                <option value="">Default (Overview)</option>
                {#each landingPages as lp}
                  <option value={lp.value}>{lp.label}</option>
                {/each}
              </select>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-neutral-400">No roles configured yet.</p>
      {/if}
    </section>

    <!-- Theme & Branding -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Theme & Branding</h3>

      <!-- Theme Mode -->
      <div class="mb-5">
        <span class="block text-sm font-medium text-neutral-700 mb-2">Theme Mode</span>
        <div class="flex gap-2">
          {#each [
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
            { value: "auto", label: "Auto" },
          ] as option}
            <button
              type="button"
              onclick={() => (form.theme_mode = option.value as "light" | "dark" | "auto")}
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors border
                     {form.theme_mode === option.value
                       ? 'bg-neutral-800 text-white border-neutral-800'
                       : 'bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-50'}"
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>

      <!-- Accent Color -->
      <div>
        <label for="accent_color" class="block text-sm font-medium text-neutral-700 mb-1.5">Accent Color</label>
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-lg border border-neutral-200 shrink-0"
            style="background-color: {form.accent_color ?? '#171717'}"
          ></div>
          <input
            id="accent_color"
            type="text"
            bind:value={form.accent_color}
            placeholder="#171717"
            maxlength="7"
            class="w-32 rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 font-mono placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          <input
            type="color"
            value={form.accent_color ?? "#171717"}
            oninput={(e) => (form.accent_color = (e.target as HTMLInputElement).value)}
            class="w-10 h-10 rounded-lg border border-neutral-200 cursor-pointer p-0.5"
          />
        </div>
      </div>
    </section>

    <!-- Localization -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Localization</h3>

      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <!-- Date Format -->
        <div>
          <label for="date_format" class="block text-sm font-medium text-neutral-700 mb-1.5">Date Format</label>
          <select
            id="date_format"
            bind:value={form.date_format}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            {#each DATE_FORMAT_OPTIONS as opt}
              <option value={opt.value}>{opt.label} — {opt.preview}</option>
            {/each}
          </select>
        </div>

        <!-- Number Format -->
        <div>
          <label for="number_format" class="block text-sm font-medium text-neutral-700 mb-1.5">Number Format</label>
          <select
            id="number_format"
            bind:value={form.number_format}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            {#each NUMBER_FORMAT_OPTIONS as opt}
              <option value={opt.value}>{opt.label} — {opt.preview}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Measurement Units -->
      <div class="mt-5">
        <span class="block text-sm font-medium text-neutral-700 mb-2">Measurement Units</span>
        <div class="flex gap-2">
          {#each [
            { value: "sqm", label: "Square Meters (m\u00B2)" },
            { value: "sqft", label: "Square Feet (ft\u00B2)" },
          ] as option}
            <button
              type="button"
              onclick={() => (form.measurement_unit = option.value as "sqm" | "sqft")}
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors border
                     {form.measurement_unit === option.value
                       ? 'bg-neutral-800 text-white border-neutral-800'
                       : 'bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-50'}"
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>
    </section>

    <!-- Language -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="mb-5">
        <h3 class="text-sm font-semibold text-neutral-800">Language</h3>
        <p class="mt-1 text-xs text-neutral-500">
          Choose the language used for the platform interface. Saved per device — applies immediately.
        </p>
      </div>

      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {#each i18n.available as locale (locale.code)}
          {@const isActive = i18n.locale === locale.code}
          <button
            type="button"
            onclick={() => {
              i18n.setLocale(locale.code as LocaleCode);
              toast.success("Language updated", `Switched to ${locale.english}.`);
            }}
            class="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors
              {isActive
                ? 'border-neutral-800 bg-neutral-800 text-white'
                : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400 hover:bg-neutral-50'}"
            aria-pressed={isActive}
          >
            <span class="flex flex-col min-w-0">
              <span class="text-sm font-semibold truncate">{locale.name}</span>
              <span class="text-[10px] {isActive ? 'text-neutral-300' : 'text-neutral-400'}">{locale.english}</span>
            </span>
            <span class="text-[10px] font-mono uppercase tabular-nums opacity-70">{locale.code}</span>
          </button>
        {/each}
      </div>

      {#if LOCALES[i18n.locale].direction === "rtl"}
        <p class="mt-4 text-[11px] text-neutral-500">
          {LOCALES[i18n.locale].name} is a right-to-left language — the layout has flipped to match.
        </p>
      {/if}
    </section>

    <!-- Currency -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Currency</h3>

      {#if currency.isLocationDetected}
        <div class="mb-5 flex flex-wrap items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
          </svg>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-amber-900">Currency detected from your location</p>
            <p class="mt-0.5 text-[11px] text-amber-800/80">
              We've auto-selected <span class="font-mono font-semibold">{currency.config.code}</span> based on your browser locale. Save changes to make this your organization's default — until then, other users in the org will see their own location-based currency.
            </p>
          </div>
          <button
            type="button"
            onclick={handleSave}
            disabled={saving}
            class="shrink-0 rounded-lg bg-amber-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-800 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Make this explicit"}
          </button>
        </div>
      {/if}

      <div class="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <!-- Default Currency -->
        <div>
          <label for="default_currency" class="block text-sm font-medium text-neutral-700 mb-1.5">Default Currency</label>
          <select
            id="default_currency"
            bind:value={form.default_currency}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            {#each currencyOptions as opt}
              <option value={opt.code}>{opt.label} ({getCurrencySymbol(opt.code)})</option>
            {/each}
          </select>
        </div>

        <!-- Currency Position -->
        <div>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Symbol Position</span>
          <div class="flex gap-2">
            {#each [
              {
                value: "prefix",
                get label() {
                  const code = getDefaultCurrencyCode();
                  return `${getCurrencySymbol(code)}1,000`;
                },
              },
              {
                value: "suffix",
                get label() {
                  const code = getDefaultCurrencyCode();
                  return `1,000${getCurrencySymbol(code)}`;
                },
              },
            ] as option}
              <button
                type="button"
                onclick={() => (form.currency_position = option.value as "prefix" | "suffix")}
                class="flex-1 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors border
                       {form.currency_position === option.value
                         ? 'bg-neutral-800 text-white border-neutral-800'
                         : 'bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Decimal Places -->
        <div>
          <label for="currency_decimals" class="block text-sm font-medium text-neutral-700 mb-1.5">Decimal Places</label>
          <input
            id="currency_decimals"
            type="number"
            min="0"
            max="4"
            bind:value={form.currency_decimal_places}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      <!-- Preview -->
      {#if true}
        {@const code = getDefaultCurrencyCode()}
        {@const sym = getCurrencySymbol(code)}
        {@const dec = form.currency_decimal_places ?? 2}
        {@const num = (1234567.89).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec })}
        <div class="mt-4 px-4 py-3 rounded-lg bg-neutral-50 border border-neutral-100">
          <p class="text-xs text-neutral-500 mb-1">Preview</p>
          <p class="text-sm font-medium text-neutral-800 font-mono">
            {form.currency_position === "prefix" ? `${sym}${num}` : `${num}${sym}`}
          </p>
        </div>
      {/if}
    </section>

  </div>
{/if}
