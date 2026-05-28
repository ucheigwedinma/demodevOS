<script lang="ts">
  import { api } from "$lib/api";

  interface MFAChoice {
    value: string;
    label: string;
  }

  interface MFAStats {
    total_users: number;
    mfa_enabled: number;
    mfa_disabled: number;
    adoption_pct: number;
  }

  interface MFASettingsResponse {
    mfa_enforcement: string;
    mfa_enforcement_display: string;
    enforcement_choices: MFAChoice[];
    stats: MFAStats;
  }

  let enforcement = $state("");
  let enforcementDisplay = $state("");
  let choices = $state<MFAChoice[]>([]);
  let stats = $state<MFAStats>({ total_users: 0, mfa_enabled: 0, mfa_disabled: 0, adoption_pct: 0 });
  let loading = $state(true);
  let saving = $state(false);
  let dirty = $state(false);
  let savedEnforcement = $state("");

  const policyDescriptions: Record<string, string> = {
    disabled: "MFA is turned off. Users authenticate with password only — no OTP step.",
    optional: "Users can opt in to MFA from their profile. OTP is only required for users who have enabled it.",
    required_admins: "Admin users must complete OTP on every login. Regular members can opt in.",
    required_all: "All users must complete OTP verification on every login. This is the most secure setting.",
  };

  const policyIcons: Record<string, string> = {
    disabled: "M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636",
    optional: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
    required_admins: "M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z",
    required_all: "M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z",
  };

  async function fetchSettings() {
    loading = true;
    try {
      const res = await api.get<MFASettingsResponse>("/iam/mfa-settings/");
      enforcement = res.mfa_enforcement;
      savedEnforcement = res.mfa_enforcement;
      enforcementDisplay = res.mfa_enforcement_display;
      choices = res.enforcement_choices;
      stats = res.stats;
    } catch {
      // error state
    } finally {
      loading = false;
    }
  }

  function handlePolicyChange(value: string) {
    enforcement = value;
    dirty = enforcement !== savedEnforcement;
  }

  async function handleSave() {
    saving = true;
    try {
      const res = await api.patch<MFASettingsResponse>("/iam/mfa-settings/", {
        mfa_enforcement: enforcement,
      });
      enforcement = res.mfa_enforcement;
      savedEnforcement = res.mfa_enforcement;
      enforcementDisplay = res.mfa_enforcement_display;
      stats = res.stats;
      dirty = false;
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    fetchSettings();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Multi-Factor Authentication</h1>
    <p class="mt-1 text-sm text-neutral-500">Configure MFA enforcement policy and monitor adoption across your organization.</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else}
    <!-- Adoption Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Users</p>
        <p class="mt-2 text-2xl font-bold text-neutral-900">{stats.total_users}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">MFA Enabled</p>
        <p class="mt-2 text-2xl font-bold text-emerald-700">{stats.mfa_enabled}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">MFA Disabled</p>
        <p class="mt-2 text-2xl font-bold text-neutral-400">{stats.mfa_disabled}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Adoption</p>
        <div class="mt-2 flex items-end gap-1.5">
          <p class="text-2xl font-bold text-neutral-900">{stats.adoption_pct}%</p>
        </div>
        <div class="mt-2 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
          <div
            class="h-full rounded-full bg-neutral-900 transition-all duration-500"
            style="width: {stats.adoption_pct}%"
          ></div>
        </div>
      </div>
    </div>

    <!-- Enforcement Policy -->
    <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
      <div class="px-6 py-5">
        <h2 class="text-sm font-semibold text-neutral-900">Enforcement Policy</h2>
        <p class="mt-0.5 text-xs text-neutral-400">Controls whether OTP verification is required during login.</p>
      </div>

      <div class="px-6 py-5">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {#each choices as choice}
            <button
              onclick={() => handlePolicyChange(choice.value)}
              class="relative flex items-start gap-4 rounded-xl border-2 px-5 py-4 text-left transition-all
                     {enforcement === choice.value
                       ? 'border-neutral-900 bg-neutral-50'
                       : 'border-neutral-200 hover:border-neutral-300'}"
            >
              <div class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg
                          {enforcement === choice.value ? 'bg-neutral-900' : 'bg-neutral-100'}">
                <svg class="w-4.5 h-4.5 {enforcement === choice.value ? 'text-white' : 'text-neutral-500'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d={policyIcons[choice.value] ?? ""} />
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-neutral-900">{choice.label}</p>
                <p class="mt-0.5 text-xs text-neutral-400 leading-relaxed">{policyDescriptions[choice.value] ?? ""}</p>
              </div>
              {#if enforcement === choice.value}
                <div class="absolute top-3 right-3">
                  <svg class="w-5 h-5 text-neutral-900" fill="currentColor" viewBox="0 0 24 24">
                    <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z" clip-rule="evenodd" />
                  </svg>
                </div>
              {/if}
            </button>
          {/each}
        </div>
      </div>

      <!-- Save bar -->
      <div class="px-6 py-4 bg-neutral-50/50 rounded-b-xl">
        <div class="flex items-center justify-between">
          <p class="text-xs text-neutral-400">
            {#if dirty}
              You have unsaved changes.
            {:else}
              Current policy: <span class="font-medium text-neutral-600">{enforcementDisplay}</span>
            {/if}
          </p>
          <button
            onclick={handleSave}
            disabled={!dirty || saving}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>

    <!-- How it works -->
    <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
      <div class="px-6 py-5">
        <h2 class="text-sm font-semibold text-neutral-900">How MFA Works</h2>
        <p class="mt-0.5 text-xs text-neutral-400">The authentication flow adapts based on the enforcement policy.</p>
      </div>

      <div class="px-6 py-5">
        <div class="flex gap-4">
          <div class="flex flex-col items-center">
            <div class="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white text-xs font-bold">1</div>
            <div class="w-px flex-1 bg-neutral-200 my-2"></div>
          </div>
          <div class="pb-6">
            <p class="text-sm font-medium text-neutral-900">User enters credentials</p>
            <p class="mt-0.5 text-xs text-neutral-400">Email and password are validated against the database.</p>
          </div>
        </div>

        <div class="flex gap-4">
          <div class="flex flex-col items-center">
            <div class="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white text-xs font-bold">2</div>
            <div class="w-px flex-1 bg-neutral-200 my-2"></div>
          </div>
          <div class="pb-6">
            <p class="text-sm font-medium text-neutral-900">MFA policy is evaluated</p>
            <p class="mt-0.5 text-xs text-neutral-400">The system checks the org enforcement policy and the user's MFA status.</p>
          </div>
        </div>

        <div class="flex gap-4">
          <div class="flex flex-col items-center">
            <div class="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white text-xs font-bold">3</div>
          </div>
          <div>
            <p class="text-sm font-medium text-neutral-900">OTP or direct access</p>
            <p class="mt-0.5 text-xs text-neutral-400">If MFA is required, a 6-digit code is sent via email. Otherwise, tokens are issued directly.</p>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>
