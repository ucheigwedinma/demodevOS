<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { SecuritySettings } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<SecuritySettings>>({});

  // CIDR input
  let cidrInput = $state("");
  let cidrError = $state("");

  // Country input
  let countryInput = $state("");
  let countryError = $state("");

  async function loadSettings() {
    try {
      const data = await api.get<SecuritySettings>("/settings/security/");
      form = data;
    } catch {
      toast.error("Load failed", "Could not load security settings.");
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
        encryption_at_rest,
        encryption_in_transit,
        ...payload
      } = form as SecuritySettings;
      await api.patch<SecuritySettings>("/settings/security/", payload);
      toast.success("Saved", "Security settings updated successfully.");
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

  function addCidr() {
    const value = cidrInput.trim();
    if (!value) return;
    // Basic CIDR validation
    const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (!cidrPattern.test(value)) {
      cidrError = "Enter a valid CIDR (e.g. 10.0.0.0/8)";
      return;
    }
    cidrError = "";
    const current = form.whitelisted_cidrs ?? [];
    if (!current.includes(value)) {
      form.whitelisted_cidrs = [...current, value];
    }
    cidrInput = "";
  }

  function removeCidr(cidr: string) {
    form.whitelisted_cidrs = (form.whitelisted_cidrs ?? []).filter((c) => c !== cidr);
  }

  function addCountry() {
    const value = countryInput.trim().toUpperCase();
    if (!value) return;
    if (!/^[A-Z]{2}$/.test(value)) {
      countryError = "Enter a 2-letter country code (e.g. US)";
      return;
    }
    countryError = "";
    const current = form.blocked_countries ?? [];
    if (!current.includes(value)) {
      form.blocked_countries = [...current, value];
    }
    countryInput = "";
  }

  function removeCountry(code: string) {
    form.blocked_countries = (form.blocked_countries ?? []).filter((c) => c !== code);
  }

  function handleCidrKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      addCidr();
    }
  }

  function handleCountryKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      addCountry();
    }
  }

  $effect(() => {
    loadSettings();
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
      <h2 class="text-xl font-bold text-neutral-800">Security Controls</h2>
      <p class="mt-1 text-sm text-neutral-500">Configure authentication policies, encryption status, and access restrictions.</p>
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

    <!-- Authentication -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Authentication</h3>

      <!-- MFA toggle -->
      <div class="flex items-center justify-between py-3 border-b border-neutral-100">
        <div>
          <p class="text-sm font-medium text-neutral-800">Enforce Multi-Factor Authentication</p>
          <p class="text-xs text-neutral-500 mt-0.5">Require all users to set up MFA before accessing the platform.</p>
        </div>
        <button
          type="button"
          onclick={() => (form.mfa_enforced = !form.mfa_enforced)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.mfa_enforced ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.mfa_enforced}
          aria-label="Toggle MFA enforcement"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.mfa_enforced ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>

      <!-- Password Policy -->
      <div class="py-4 border-b border-neutral-100">
        <p class="text-sm font-medium text-neutral-800 mb-3">Password Policy</p>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label for="pw_min" class="block text-sm font-medium text-neutral-700 mb-1.5">Minimum Length</label>
            <input
              id="pw_min"
              type="number"
              min="6"
              max="128"
              bind:value={form.password_min_length}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
          </div>
        </div>
        <div class="mt-4 space-y-2.5">
          {#each [
            { key: "password_require_uppercase" as const, label: "Require uppercase letter" },
            { key: "password_require_lowercase" as const, label: "Require lowercase letter" },
            { key: "password_require_digits" as const, label: "Require digit" },
            { key: "password_require_special" as const, label: "Require special character" },
          ] as rule}
            <label class="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form[rule.key] ?? false}
                onchange={() => (form[rule.key] = !form[rule.key])}
                class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800"
              />
              <span class="text-sm text-neutral-700">{rule.label}</span>
            </label>
          {/each}
        </div>
      </div>

      <!-- Session Timeout -->
      <div class="pt-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label for="session_timeout" class="block text-sm font-medium text-neutral-700 mb-1.5">Session Timeout (minutes)</label>
            <input
              id="session_timeout"
              type="number"
              min="5"
              max="1440"
              bind:value={form.session_timeout_minutes}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
            <p class="text-xs text-neutral-400 mt-1">Between 5 and 1440 minutes (24 hours).</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Data Encryption (read-only) -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-1">Data Encryption</h3>
      <p class="text-xs text-neutral-500 mb-5">Encryption status is determined by your infrastructure configuration.</p>

      <div class="space-y-3">
        <div class="flex items-center justify-between py-2">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
            <span class="text-sm text-neutral-700">Encryption at Rest</span>
          </div>
          {#if form.encryption_at_rest}
            <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">Enabled</span>
          {:else}
            <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-500">Not Configured</span>
          {/if}
        </div>
        <div class="flex items-center justify-between py-2">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
            </svg>
            <span class="text-sm text-neutral-700">Encryption in Transit</span>
          </div>
          {#if form.encryption_in_transit}
            <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">Enabled</span>
          {:else}
            <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-500">Not Configured</span>
          {/if}
        </div>
      </div>
    </section>

    <!-- IP Restrictions -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between mb-5">
        <h3 class="text-sm font-semibold text-neutral-800">IP Restrictions</h3>
        <button
          type="button"
          onclick={() => (form.ip_restriction_enabled = !form.ip_restriction_enabled)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.ip_restriction_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.ip_restriction_enabled}
          aria-label="Toggle IP restrictions"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.ip_restriction_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>

      {#if form.ip_restriction_enabled}
        <div>
          <label for="cidr_input" class="block text-sm font-medium text-neutral-700 mb-1.5">Whitelisted CIDR Ranges</label>
          <div class="flex gap-2">
            <input
              id="cidr_input"
              type="text"
              bind:value={cidrInput}
              onkeydown={handleCidrKeydown}
              placeholder="e.g. 10.0.0.0/8"
              class="flex-1 rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
            <button
              type="button"
              onclick={addCidr}
              class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Add
            </button>
          </div>
          {#if cidrError}
            <p class="text-xs text-red-600 mt-1">{cidrError}</p>
          {/if}

          {#if (form.whitelisted_cidrs ?? []).length > 0}
            <div class="flex flex-wrap gap-2 mt-3">
              {#each form.whitelisted_cidrs ?? [] as cidr}
                <span class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-100 px-3 py-1.5 text-sm text-neutral-700">
                  <code class="text-xs">{cidr}</code>
                  <button
                    type="button"
                    onclick={() => removeCidr(cidr)}
                    class="text-neutral-400 hover:text-neutral-700 transition-colors"
                    aria-label="Remove {cidr}"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <!-- Geo-Blocking -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between mb-5">
        <h3 class="text-sm font-semibold text-neutral-800">Geo-Blocking</h3>
        <button
          type="button"
          onclick={() => (form.geo_blocking_enabled = !form.geo_blocking_enabled)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.geo_blocking_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.geo_blocking_enabled}
          aria-label="Toggle geo-blocking"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.geo_blocking_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>

      {#if form.geo_blocking_enabled}
        <div>
          <label for="country_input" class="block text-sm font-medium text-neutral-700 mb-1.5">Blocked Countries</label>
          <div class="flex gap-2">
            <input
              id="country_input"
              type="text"
              bind:value={countryInput}
              onkeydown={handleCountryKeydown}
              placeholder="e.g. CN"
              maxlength="2"
              class="w-24 rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow uppercase"
            />
            <button
              type="button"
              onclick={addCountry}
              class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Add
            </button>
          </div>
          {#if countryError}
            <p class="text-xs text-red-600 mt-1">{countryError}</p>
          {/if}

          {#if (form.blocked_countries ?? []).length > 0}
            <div class="flex flex-wrap gap-2 mt-3">
              {#each form.blocked_countries ?? [] as code}
                <span class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-100 px-3 py-1.5 text-sm text-neutral-700">
                  <code class="text-xs font-semibold">{code}</code>
                  <button
                    type="button"
                    onclick={() => removeCountry(code)}
                    class="text-neutral-400 hover:text-neutral-700 transition-colors"
                    aria-label="Remove {code}"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </section>

  </div>
{/if}
