<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type Passkey = {
    id: number;
    name: string;
    aaguid: string;
    created_at: string;
    last_used_at: string | null;
  };

  let passkeys = $state<Passkey[]>([]);
  let loading = $state(true);
  let deleting = $state<number | null>(null);

  function formatDate(d: string | null): string {
    if (!d) return "Never";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  async function fetchPasskeys() {
    loading = true;
    try {
      const data = await api.get<Passkey[] | { results: Passkey[] }>("/auth/mfa/passkeys/");
      passkeys = Array.isArray(data) ? data : (data.results ?? []);
    } catch {
      passkeys = [];
    } finally {
      loading = false;
    }
  }

  async function deletePasskey(id: number) {
    deleting = id;
    try {
      await api.delete(`/auth/mfa/passkeys/${id}/`);
      toast.success("Removed", "Passkey deleted.");
      await fetchPasskeys();
    } catch {
      toast.error("Delete failed", "Could not remove passkey.");
    } finally {
      deleting = null;
    }
  }

  $effect(() => { fetchPasskeys(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Biometric Authentication</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Manage your registered passkeys (FIDO2 / WebAuthn) — fingerprint, face,
        or hardware key. New enrolment happens during MFA setup.
      </p>
    </div>
    <a href="/iam/auth/mfa"
      class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      Add passkey →
    </a>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if passkeys.length === 0}
      <div class="p-16 text-center">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
          <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.864 4.243A7.5 7.5 0 0 1 19.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 0 0 4.5 10.5a7.464 7.464 0 0 1-1.15 3.993m1.989 3.559A11.209 11.209 0 0 0 8.25 10.5a3.75 3.75 0 1 1 7.5 0c0 .527-.021 1.049-.064 1.565M12 10.5a14.94 14.94 0 0 1-3.6 9.75m6.633-4.596a18.666 18.666 0 0 1-2.485 5.33" />
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-neutral-800">No passkeys yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500 max-w-sm mx-auto">
          Add a passkey from MFA setup to enable fingerprint, face, or hardware-key sign-in.
        </p>
        <a href="/iam/auth/mfa" class="mt-5 inline-block rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
          Set up MFA
        </a>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each passkeys as pk}
          <li class="p-5 flex items-center gap-4 hover:bg-neutral-50 transition-colors">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-neutral-900 truncate">{pk.name || "Passkey"}</p>
              <p class="mt-1 text-xs text-neutral-500">
                Added {formatDate(pk.created_at)} · last used {formatDate(pk.last_used_at)}
              </p>
              {#if pk.aaguid}
                <p class="mt-0.5 text-[10px] text-neutral-400 font-mono">AAGUID: {pk.aaguid}</p>
              {/if}
            </div>
            <button onclick={() => deletePasskey(pk.id)} disabled={deleting === pk.id}
              class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50">
              {deleting === pk.id ? "..." : "Remove"}
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
    <p class="font-medium text-neutral-700 mb-1">About passkeys</p>
    <p>
      Passkeys are phishing-resistant credentials stored on your device's secure enclave.
      They replace passwords for sign-in. Removing a passkey here only de-registers it from this account —
      the credential on your device may still appear in the system passkey manager until you delete it there.
    </p>
  </div>
</div>
