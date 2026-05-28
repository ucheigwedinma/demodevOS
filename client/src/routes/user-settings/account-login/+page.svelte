<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { UserAccountSecurity } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let changingPassword = $state(false);
  let revokingSessions = $state(false);

  let security = $state<UserAccountSecurity | null>(null);
  let username = $state("");
  let mfaEnabled = $state(false);
  let passkeyEnabled = $state(false);

  let currentPassword = $state("");
  let newPassword = $state("");
  let confirmPassword = $state("");

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function fmtDate(value: string | null): string {
    if (!value) return "—";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function loadSecurity() {
    loading = true;
    try {
      const data = await api.get<UserAccountSecurity>("/auth/account-security/");
      security = data;
      username = data.username;
      mfaEnabled = data.mfa_enabled;
      passkeyEnabled = data.passkey_enabled;
    } catch (error) {
      security = null;
      toast.error("Load failed", parseError(error, "Could not load account and login settings."));
    } finally {
      loading = false;
    }
  }

  async function saveAccountSecurity() {
    if (!security) return;
    saving = true;
    try {
      const updated = await api.patch<UserAccountSecurity>("/auth/account-security/", {
        username: username.trim(),
        mfa_enabled: mfaEnabled,
        passkey_enabled: passkeyEnabled,
      });
      security = updated;
      username = updated.username;
      mfaEnabled = updated.mfa_enabled;
      passkeyEnabled = updated.passkey_enabled;
      toast.success("Updated", "Account and login preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not update account and login settings."));
    } finally {
      saving = false;
    }
  }

  async function changePassword() {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error("Missing fields", "Fill current password, new password, and confirmation.");
      return;
    }

    changingPassword = true;
    try {
      const response = await api.post<{ detail: string; revoked_sessions: number }>("/auth/change-password/", {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      currentPassword = "";
      newPassword = "";
      confirmPassword = "";
      toast.success("Password changed", `${response.detail} Revoked sessions: ${response.revoked_sessions}.`);
      await loadSecurity();
    } catch (error) {
      toast.error("Change failed", parseError(error, "Could not change password."));
    } finally {
      changingPassword = false;
    }
  }

  async function logoutOtherSessions() {
    revokingSessions = true;
    try {
      const response = await api.post<{ detail: string; revoked_sessions: number }>("/auth/sessions/logout-others/", {});
      toast.success("Sessions updated", `${response.detail} (${response.revoked_sessions} revoked)`);
      await loadSecurity();
    } catch (error) {
      toast.error("Action failed", parseError(error, "Could not revoke other sessions."));
    } finally {
      revokingSessions = false;
    }
  }

  $effect(() => {
    loadSecurity();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !security}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Account settings unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load account and login settings.</p>
    <button
      onclick={() => loadSecurity()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Account & Login</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Sign-in security controls, active sessions, linked providers, and account security logs.
        </p>
      </div>
      <button
        onclick={saveAccountSecurity}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-5">Sign-in controls</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="username" class="block text-sm font-medium text-neutral-700 mb-1.5">Username</label>
          <input
            id="username"
            type="text"
            bind:value={username}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
          <p class="mt-1 text-xs text-neutral-500">Current account email: {security.email}</p>
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-medium text-neutral-900">2FA</p>
          <p class="mt-1 text-xs text-neutral-500">
            Organization policy: {security.mfa_policy_display}
          </p>
          <label class="mt-3 inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={mfaEnabled} class="rounded border-neutral-300" />
            Enable two-factor authentication for this account
          </label>
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 md:col-span-2">
          <p class="text-sm font-medium text-neutral-900">Passkeys / Biometric login</p>
          <p class="mt-1 text-xs text-neutral-500">
            Platform support is tracked here. Device-native passkey enrollment is still pending full rollout.
          </p>
          <div class="mt-3 flex items-center justify-between gap-3">
            <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" bind:checked={passkeyEnabled} class="rounded border-neutral-300" />
              Mark passkey/biometric login as enabled for this account
            </label>
            <a
              href="/iam/auth/biometric"
              class="text-xs font-semibold text-neutral-700 hover:text-neutral-900"
            >
              Open biometric policy
            </a>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-5">Change password</h2>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div>
          <label for="current_password" class="block text-sm font-medium text-neutral-700 mb-1.5">Current password</label>
          <input
            id="current_password"
            type="password"
            bind:value={currentPassword}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
        <div>
          <label for="new_password" class="block text-sm font-medium text-neutral-700 mb-1.5">New password</label>
          <input
            id="new_password"
            type="password"
            bind:value={newPassword}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
        <div>
          <label for="confirm_password" class="block text-sm font-medium text-neutral-700 mb-1.5">Confirm new password</label>
          <input
            id="confirm_password"
            type="password"
            bind:value={confirmPassword}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>
      </div>
      <div class="mt-4">
        <button
          onclick={changePassword}
          disabled={changingPassword}
          class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {changingPassword ? "Changing..." : "Change Password"}
        </button>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between gap-3 mb-4">
        <h2 class="text-sm font-semibold text-neutral-900">Login sessions</h2>
        <button
          onclick={logoutOtherSessions}
          disabled={revokingSessions}
          class="rounded-lg border border-red-300 bg-red-50 px-3.5 py-2 text-xs font-semibold text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {revokingSessions ? "Revoking..." : "Logout from other devices"}
        </button>
      </div>

      {#if security.active_sessions.length === 0}
        <p class="text-sm text-neutral-500">No tracked active sessions yet.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Device</th>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Provider</th>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">IP</th>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Created</th>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Last Seen</th>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">State</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each security.active_sessions as row}
                <tr>
                  <td class="px-3 py-2 text-sm text-neutral-800">{row.device_label || "Unknown device"}</td>
                  <td class="px-3 py-2 text-sm text-neutral-700">{row.auth_provider_display}</td>
                  <td class="px-3 py-2 text-sm text-neutral-700">{row.ip_address || "—"}</td>
                  <td class="px-3 py-2 text-sm text-neutral-700">{fmtDate(row.created_at)}</td>
                  <td class="px-3 py-2 text-sm text-neutral-700">{fmtDate(row.last_seen_at)}</td>
                  <td class="px-3 py-2">
                    {#if row.is_current}
                      <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">Current</span>
                    {:else}
                      <span class="inline-flex rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-600">Active</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Linked authentication providers</h2>
      {#if security.linked_providers.length === 0}
        <p class="text-sm text-neutral-500">No external providers linked yet.</p>
      {:else}
        <div class="space-y-2">
          {#each security.linked_providers as row}
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-neutral-900">{row.provider_display}</p>
                <p class="text-xs text-neutral-500">Connected {fmtDate(row.connected_at)}</p>
              </div>
              <p class="text-xs text-neutral-600 mt-0.5">{row.email}</p>
              <p class="text-xs text-neutral-500 mt-0.5">Last provider login: {fmtDate(row.last_login_at)}</p>
            </div>
          {/each}
        </div>
      {/if}

      <div class="mt-4 flex flex-wrap gap-2">
        <a href="/login" class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50">Google</a>
        <a href="/login" class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50">Microsoft</a>
        <a href="/iam/auth/oauth-saml" class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50">SSO / SAML</a>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Security logs</h2>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">Login history</h3>
          <div class="space-y-2">
            {#if security.login_history.length === 0}
              <p class="text-sm text-neutral-500">No login history yet.</p>
            {:else}
              {#each security.login_history.slice(0, 10) as row}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <p class="text-xs font-semibold text-neutral-800">{row.event_type_display}</p>
                  <p class="text-xs text-neutral-600 mt-0.5">{row.device_label || "Unknown device"} • {row.ip_address || "No IP"}</p>
                  <p class="text-xs text-neutral-500 mt-0.5">{fmtDate(row.occurred_at)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">Failed login attempts</h3>
          <div class="space-y-2">
            {#if security.failed_login_attempts.length === 0}
              <p class="text-sm text-neutral-500">No failed attempts logged.</p>
            {:else}
              {#each security.failed_login_attempts.slice(0, 10) as row}
                <div class="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                  <p class="text-xs font-semibold text-red-800">{row.event_type_display}</p>
                  <p class="text-xs text-red-700 mt-0.5">{row.detail || "Failed login attempt."}</p>
                  <p class="text-xs text-red-600 mt-0.5">{fmtDate(row.occurred_at)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">Device history</h3>
          <div class="space-y-2">
            {#if security.device_history.length === 0}
              <p class="text-sm text-neutral-500">No device history yet.</p>
            {:else}
              {#each security.device_history.slice(0, 10) as row}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <p class="text-xs font-semibold text-neutral-800">{row.device_label}</p>
                  <p class="text-xs text-neutral-600 mt-0.5">{row.auth_provider_display} • {row.ip_address || "No IP"}</p>
                  <p class="text-xs text-neutral-500 mt-0.5">Last seen {fmtDate(row.last_seen_at)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </section>
  </div>
{/if}
