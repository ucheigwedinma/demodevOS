<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type AuthSession = {
    sid: string;
    auth_provider: string;
    auth_provider_display: string;
    ip_address: string | null;
    user_agent: string;
    device_label: string;
    created_at: string;
    last_seen_at: string;
    revoked_at: string | null;
    revoke_reason: string;
    is_current: boolean;
  };
  type SessionsResponse = {
    count: number;
    results: AuthSession[];
    current_sid: string;
  };

  let sessions = $state<AuthSession[]>([]);
  let loading = $state(true);
  let revoking = $state<string | null>(null);
  let revokingAll = $state(false);
  let confirmRevokeAll = $state(false);

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  function relativeTime(d: string | null): string {
    if (!d) return "Never";
    const diff = Date.now() - new Date(d).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return "Just now";
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    const day = Math.floor(hr / 24);
    if (day < 7) return `${day}d ago`;
    return formatDate(d);
  }

  function shortenUA(ua: string): string {
    if (!ua) return "Unknown device";
    // Quick heuristics — not a full UA parser
    if (/iPhone/i.test(ua)) return "iPhone";
    if (/iPad/i.test(ua)) return "iPad";
    if (/Android/i.test(ua)) return "Android";
    if (/Macintosh/i.test(ua)) return "macOS";
    if (/Windows/i.test(ua)) return "Windows";
    if (/Linux/i.test(ua)) return "Linux";
    return ua.slice(0, 60) + (ua.length > 60 ? "…" : "");
  }

  function browserOf(ua: string): string {
    if (!ua) return "";
    if (/Edg\//.test(ua)) return "Edge";
    if (/Chrome\//.test(ua) && !/Edg\//.test(ua)) return "Chrome";
    if (/Firefox\//.test(ua)) return "Firefox";
    if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) return "Safari";
    return "Browser";
  }

  async function fetchSessions() {
    loading = true;
    try {
      const res = await api.get<SessionsResponse>("/iam/auth/sessions/");
      sessions = res.results;
    } catch {
      sessions = [];
    } finally {
      loading = false;
    }
  }

  async function revokeOne(sid: string) {
    revoking = sid;
    try {
      await api.post(`/iam/auth/sessions/${sid}/revoke/`, {});
      toast.success("Revoked", "Session ended.");
      await fetchSessions();
    } catch {
      toast.error("Action failed", "Could not revoke session.");
    } finally {
      revoking = null;
    }
  }

  async function revokeAllOthers() {
    revokingAll = true;
    try {
      await api.post("/auth/sessions/logout-others/", {});
      toast.success("Done", "All other sessions ended.");
      confirmRevokeAll = false;
      await fetchSessions();
    } catch {
      toast.error("Action failed", "Could not end other sessions.");
    } finally {
      revokingAll = false;
    }
  }

  $effect(() => { fetchSessions(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Active Sessions</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Devices and browsers currently signed in to your account. Revoke any that look unfamiliar.
      </p>
    </div>
    {#if sessions.filter((s) => !s.is_current).length > 0}
      <button onclick={() => (confirmRevokeAll = true)}
        class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
        Sign out of all other sessions
      </button>
    {/if}
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if sessions.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No active sessions</h3>
        <p class="mt-1.5 text-sm text-neutral-500">This is unexpected — you should at least see the current session.</p>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each sessions as s}
          <li class="p-5 flex items-start gap-4 hover:bg-neutral-50 transition-colors">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <p class="font-semibold text-neutral-900">
                  {s.device_label || shortenUA(s.user_agent)}
                </p>
                {#if s.is_current}
                  <span class="inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">
                    This session
                  </span>
                {/if}
                <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                  {s.auth_provider_display}
                </span>
              </div>
              <p class="mt-1 text-xs text-neutral-500">
                {browserOf(s.user_agent)} · {s.ip_address || "Unknown IP"}
              </p>
              <p class="mt-1 text-xs text-neutral-400">
                Active {relativeTime(s.last_seen_at)} · started {formatDate(s.created_at)}
              </p>
            </div>
            <div class="shrink-0">
              {#if !s.is_current}
                <button onclick={() => revokeOne(s.sid)} disabled={revoking === s.sid}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50">
                  {revoking === s.sid ? "..." : "Revoke"}
                </button>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

{#if confirmRevokeAll}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (confirmRevokeAll = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">End all other sessions?</h3>
      <p class="mt-2 text-sm text-neutral-600">
        Every device signed into your account other than this browser will be signed out immediately.
      </p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (confirmRevokeAll = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={revokeAllOthers} disabled={revokingAll}
          class="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">
          {revokingAll ? "..." : "Sign out others"}
        </button>
      </div>
    </div>
  </div>
{/if}
