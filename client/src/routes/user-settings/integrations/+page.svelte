<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserIntegrationConnection,
    UserIntegrationProvider,
    UserIntegrationsSettings,
  } from "$lib/types";

  type IntegrationAction = "connect" | "revoke" | "refresh_token";
  type IntegrationDraft = {
    account_label: string;
    webhook_url: string;
    token_expires_in_minutes: number;
  };

  const DEFAULT_TOKEN_EXPIRY_MINUTES = 129600; // 90 days

  let loading = $state(true);
  let activeActionKey = $state("");
  let settings = $state<UserIntegrationsSettings | null>(null);
  let drafts = $state<Record<string, IntegrationDraft>>({});

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function fmtDate(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function statusClass(status: string): string {
    if (status === "connected") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (status === "revoked") return "bg-amber-50 text-amber-700 border-amber-200";
    if (status === "error") return "bg-red-50 text-red-700 border-red-200";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function draftFor(provider: UserIntegrationProvider): IntegrationDraft {
    return (
      drafts[provider] ?? {
        account_label: "",
        webhook_url: "",
        token_expires_in_minutes: DEFAULT_TOKEN_EXPIRY_MINUTES,
      }
    );
  }

  function setDraft(
    provider: UserIntegrationProvider,
    field: keyof IntegrationDraft,
    value: string | number
  ) {
    const current = draftFor(provider);
    drafts = {
      ...drafts,
      [provider]: {
        ...current,
        [field]: value,
      },
    };
  }

  function syncDrafts(data: UserIntegrationsSettings) {
    const next: Record<string, IntegrationDraft> = {};
    for (const row of data.integrations) {
      let tokenMinutes = DEFAULT_TOKEN_EXPIRY_MINUTES;
      if (row.token_expires_at && row.last_token_refresh_at) {
        const expires = new Date(row.token_expires_at).getTime();
        const refreshed = new Date(row.last_token_refresh_at).getTime();
        if (Number.isFinite(expires) && Number.isFinite(refreshed) && expires > refreshed) {
          tokenMinutes = Math.max(5, Math.round((expires - refreshed) / 60000));
        }
      }
      next[row.provider] = {
        account_label: row.account_label || "",
        webhook_url: row.webhook_url || "",
        token_expires_in_minutes: tokenMinutes,
      };
    }
    drafts = next;
  }

  function isActing(provider: UserIntegrationProvider, action: IntegrationAction): boolean {
    return activeActionKey === `${provider}:${action}`;
  }

  async function loadIntegrations() {
    loading = true;
    try {
      const payload = await api.get<UserIntegrationsSettings>("/auth/integrations/");
      settings = payload;
      syncDrafts(payload);
    } catch (error) {
      settings = null;
      drafts = {};
      toast.error("Load failed", parseError(error, "Could not load integration settings."));
    } finally {
      loading = false;
    }
  }

  async function runAction(row: UserIntegrationConnection, action: IntegrationAction) {
    const provider = row.provider;
    const draft = draftFor(provider);
    const payload: Record<string, unknown> = {
      provider,
      action,
      account_label: draft.account_label.trim(),
    };
    if (row.supports_webhook_url || draft.webhook_url.trim()) {
      payload.webhook_url = draft.webhook_url.trim();
    }
    if (row.supports_token_refresh) {
      payload.token_expires_in_minutes = Number(draft.token_expires_in_minutes) || DEFAULT_TOKEN_EXPIRY_MINUTES;
    }

    activeActionKey = `${provider}:${action}`;
    try {
      const updated = await api.post<UserIntegrationsSettings>("/auth/integrations/", payload);
      settings = updated;
      syncDrafts(updated);
      toast.success("Updated", updated.detail || `${row.provider_display} updated.`);
    } catch (error) {
      toast.error("Action failed", parseError(error, `Could not ${action.replace("_", " ")} for ${row.provider_display}.`));
    } finally {
      activeActionKey = "";
    }
  }

  $effect(() => {
    loadIntegrations();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !settings}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Integrations unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your integration settings.</p>
    <button
      onclick={() => loadIntegrations()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Integrations</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Manage personal external connections and control connect, revoke, and token refresh actions.
      </p>
    </div>

    <section class="space-y-4">
      {#each settings.integrations as row}
        <article class="rounded-xl border border-neutral-200 bg-white p-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-semibold text-neutral-900">{row.provider_display}</h2>
                <span class={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${statusClass(row.status)}`}>
                  {row.status_display}
                </span>
              </div>
              <p class="mt-1 text-xs text-neutral-500">
                Connected: {fmtDate(row.connected_at)} | Last token refresh: {fmtDate(row.last_token_refresh_at)}
              </p>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => runAction(row, "connect")}
                disabled={activeActionKey.length > 0}
                class="rounded-lg border border-neutral-900 bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isActing(row.provider, "connect") ? "Connecting..." : row.is_connected ? "Reconnect" : "Connect"}
              </button>

              <button
                type="button"
                onclick={() => runAction(row, "revoke")}
                disabled={!row.is_connected || activeActionKey.length > 0}
                class="rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isActing(row.provider, "revoke") ? "Revoking..." : "Revoke"}
              </button>

              {#if row.supports_token_refresh}
                <button
                  type="button"
                  onclick={() => runAction(row, "refresh_token")}
                  disabled={!row.is_connected || activeActionKey.length > 0}
                  class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isActing(row.provider, "refresh_token") ? "Refreshing..." : "Token Refresh"}
                </button>
              {/if}
            </div>
          </div>

          <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label for={`account-label-${row.provider}`} class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-neutral-500">
                Account Label
              </label>
              <input
                id={`account-label-${row.provider}`}
                type="text"
                value={draftFor(row.provider).account_label}
                oninput={(event) =>
                  setDraft(
                    row.provider,
                    "account_label",
                    (event.currentTarget as HTMLInputElement).value
                  )}
                placeholder={`e.g. ${row.provider_display} workspace`}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </div>

            {#if row.supports_token_refresh}
              <div>
                <label for={`token-expiry-${row.provider}`} class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-neutral-500">
                  Token Lifetime (Minutes)
                </label>
                <input
                  id={`token-expiry-${row.provider}`}
                  type="number"
                  min="5"
                  max="525600"
                  value={draftFor(row.provider).token_expires_in_minutes}
                  oninput={(event) =>
                    setDraft(
                      row.provider,
                      "token_expires_in_minutes",
                      Number((event.currentTarget as HTMLInputElement).value) || DEFAULT_TOKEN_EXPIRY_MINUTES
                    )}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
              </div>
            {/if}

            {#if row.supports_webhook_url}
              <div class="md:col-span-2">
                <label for={`webhook-url-${row.provider}`} class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-neutral-500">
                  Webhook URL
                </label>
                <input
                  id={`webhook-url-${row.provider}`}
                  type="url"
                  value={draftFor(row.provider).webhook_url}
                  oninput={(event) =>
                    setDraft(
                      row.provider,
                      "webhook_url",
                      (event.currentTarget as HTMLInputElement).value
                    )}
                  placeholder="https://example.com/hooks/events"
                  class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
              </div>
            {/if}
          </div>

          <div class="mt-3 text-xs text-neutral-500">
            {#if row.supports_webhook_url}
              Webhooks require a valid endpoint URL during connect.
            {:else}
              Token expiry: {fmtDate(row.token_expires_at)}.
            {/if}
          </div>
        </article>
      {/each}
    </section>
  </div>
{/if}
