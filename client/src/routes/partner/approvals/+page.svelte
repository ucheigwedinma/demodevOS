<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalApprovalsResponse,
    PartnerPortalContextResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let data = $state<PartnerPortalApprovalsResponse | null>(null);

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function loadApprovals() {
    loading = true;
    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;
      if (!ctx.is_partner_user && !ctx.is_preview_mode) {
        data = null;
        return;
      }
      const result = await api.get<PartnerPortalApprovalsResponse>("/partners/portal/approvals/");
      data = result;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal approvals."));
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadApprovals();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No approvals access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Approval queue access is granted through active portal entitlements.</p>
  </div>
{:else if data}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Approvals & Signoffs</h1>
        <p class="mt-1 text-sm text-neutral-500">Pending document reviews and recent approval decisions within scope.</p>
      </div>
      <button
        onclick={() => loadApprovals()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Pending Signoffs</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900">{data.pending_count}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-emerald-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Can Approve</p>
        <p class="mt-1 text-2xl font-bold {data.can_approve ? 'text-emerald-600' : 'text-neutral-900'}">{data.can_approve ? "Yes" : "No"}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-indigo-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Recent Decisions</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900">{data.recent_document_decisions.length + data.onboarding_decisions.length}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Pending Document Versions</h2>
        </div>
        {#if data.pending_versions.length === 0}
          <div class="px-5 py-12 text-center text-sm text-neutral-500">No pending versions in scope.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-100 text-sm">
              <thead class="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Document</th>
                  <th class="px-4 py-3 text-left">Version</th>
                  <th class="px-4 py-3 text-left">Uploaded</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each data.pending_versions as row (row.id)}
                  <tr>
                    <td class="px-4 py-3 text-neutral-900">{row.document_number}</td>
                    <td class="px-4 py-3 text-neutral-700">v{row.version_major}.{row.version_minor}</td>
                    <td class="px-4 py-3 text-neutral-700">{fmtDate(row.uploaded_at)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <div class="space-y-6">
        <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Recent Document Decisions</h2>
          </div>
          {#if data.recent_document_decisions.length === 0}
            <div class="px-5 py-8 text-sm text-neutral-500">No document decisions recorded.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each data.recent_document_decisions.slice(0, 8) as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{row.document_version_label}</p>
                  <p class="text-xs text-neutral-600">{titleCase(row.decision)} by {row.user_name} • {fmtDate(row.timestamp)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Onboarding Decisions</h2>
          </div>
          {#if data.onboarding_decisions.length === 0}
            <div class="px-5 py-8 text-sm text-neutral-500">No onboarding decisions recorded.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each data.onboarding_decisions.slice(0, 8) as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">Case #{row.case_id} • {titleCase(row.decision)}</p>
                  <p class="text-xs text-neutral-600">{row.approver_role_label || "Approver"} • {fmtDate(row.decided_at)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
