<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type PasswordPolicy = {
    password_min_length: number;
    password_require_uppercase: boolean;
    password_require_digits: boolean;
    password_require_special: boolean;
    password_max_age_days: number;
    password_history_count: number;
  };

  let policy = $state<PasswordPolicy>({
    password_min_length: 12,
    password_require_uppercase: true,
    password_require_digits: true,
    password_require_special: false,
    password_max_age_days: 0,
    password_history_count: 0,
  });
  let original = $state<PasswordPolicy | null>(null);
  let loading = $state(true);
  let saving = $state(false);

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const POLICY_PRESETS: { name: string; policy: PasswordPolicy }[] = [
    { name: "Strict (NIST 800-63 high)", policy: { password_min_length: 14, password_require_uppercase: true, password_require_digits: true, password_require_special: true, password_max_age_days: 90, password_history_count: 5 } },
    { name: "Balanced", policy: { password_min_length: 12, password_require_uppercase: true, password_require_digits: true, password_require_special: false, password_max_age_days: 0, password_history_count: 3 } },
    { name: "Relaxed", policy: { password_min_length: 8, password_require_uppercase: false, password_require_digits: true, password_require_special: false, password_max_age_days: 0, password_history_count: 0 } },
  ];
  let presetIdx = 0;
  function devFill() {
    policy = { ...POLICY_PRESETS[presetIdx % POLICY_PRESETS.length].policy };
    presetIdx++;
  }

  async function load() {
    loading = true;
    try {
      const data = await api.get<PasswordPolicy>("/iam/auth/password-policy/");
      policy = data;
      original = { ...data };
    } catch {
      toast.error("Load failed", "Could not load password policy.");
    } finally {
      loading = false;
    }
  }

  async function save() {
    saving = true;
    try {
      const data = await api.patch<PasswordPolicy>("/iam/auth/password-policy/", policy);
      policy = data;
      original = { ...data };
      toast.success("Saved", "Password policy updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please review the form.");
      }
    } finally {
      saving = false;
    }
  }

  function reset() {
    if (original) policy = { ...original };
  }

  let dirty = $derived.by(() => {
    if (!original) return false;
    return Object.keys(policy).some((k) => (policy as Record<string, unknown>)[k] !== (original as unknown as Record<string, unknown>)[k]);
  });

  $effect(() => { load(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Password Policy</h1>
    <p class="mt-1 text-sm text-neutral-500">
      These rules apply to all users in your organization on registration, password change, and reset.
      Enforcement is performed at the API tier — see <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">apps.accounts.password_validators</code>.
    </p>
  </div>

  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
      <div class="px-6 py-5">
        <h2 class="text-sm font-semibold text-neutral-900">Strength requirements</h2>
        <p class="mt-0.5 text-xs text-neutral-400">Minimum length and character classes.</p>
      </div>

      <div class="px-6 py-5 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium text-neutral-900">Minimum length</p>
          <p class="mt-0.5 text-xs text-neutral-400">8–128 characters.</p>
        </div>
        <input type="number" min="8" max="128" bind:value={policy.password_min_length}
          class="w-24 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </div>

      <div class="px-6 py-5">
        <p class="text-sm font-medium text-neutral-900 mb-3">Complexity rules</p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
            <input type="checkbox" bind:checked={policy.password_require_uppercase} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
            <span class="text-sm text-neutral-700">Uppercase letter</span>
          </label>
          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
            <input type="checkbox" bind:checked={policy.password_require_digits} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
            <span class="text-sm text-neutral-700">Number</span>
          </label>
          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
            <input type="checkbox" bind:checked={policy.password_require_special} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
            <span class="text-sm text-neutral-700">Special character</span>
          </label>
        </div>
      </div>

      <div class="px-6 py-5 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium text-neutral-900">Password expiry</p>
          <p class="mt-0.5 text-xs text-neutral-400">Force rotation after N days. 0 = never expires.</p>
        </div>
        <div class="flex items-center gap-2">
          <input type="number" min="0" max="3650" bind:value={policy.password_max_age_days}
            class="w-24 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-500">days</span>
        </div>
      </div>

      <div class="px-6 py-5 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium text-neutral-900">Password reuse prevention</p>
          <p class="mt-0.5 text-xs text-neutral-400">Block reuse of the last N passwords. 0 = no check.</p>
        </div>
        <div class="flex items-center gap-2">
          <input type="number" min="0" max="50" bind:value={policy.password_history_count}
            class="w-24 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-500">passwords</span>
        </div>
      </div>

      <div class="px-6 py-4 bg-neutral-50/50 rounded-b-xl flex items-center gap-3">
        {#if isDev}
          <button onclick={devFill} class="rounded-lg bg-orange-500 px-3 py-2 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">
            Dev Fill
          </button>
        {/if}
        <p class="text-xs text-neutral-400 {isDev ? '' : 'mr-auto'}">
          {dirty ? "Unsaved changes" : "Saved"}
        </p>
        {#if dirty}
          <button onclick={reset} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
            Discard
          </button>
        {/if}
        <button onclick={save} disabled={saving || !dirty}
          class="rounded-lg bg-neutral-900 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-50">
          {saving ? "Saving..." : "Save changes"}
        </button>
      </div>
    </div>
  {/if}
</div>
