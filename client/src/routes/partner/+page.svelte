<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalContextResponse,
    PartnerPortalDashboardResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let dashboard = $state<PartnerPortalDashboardResponse | null>(null);

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  function summaryEntries(summary: Record<string, unknown>): Array<{ key: string; value: string }> {
    return Object.entries(summary).map(([key, value]) => ({
      key: titleCase(key),
      value: typeof value === "number" || typeof value === "string" ? String(value) : "--",
    }));
  }

  async function loadPortalDashboard() {
    loading = true;
    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;
      if (!ctx.is_partner_user && !ctx.is_preview_mode) {
        dashboard = null;
        return;
      }
      const dash = await api.get<PartnerPortalDashboardResponse>("/partners/portal/dashboard/");
      dashboard = dash;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load partner portal dashboard."));
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadPortalDashboard();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">Partner portal access is not active</h1>
    <p class="mt-1 text-sm text-amber-800">
      This user does not have any active portal entitlement yet. Complete onboarding approval and grant access from
      `Settings > Partner Gateway`.
    </p>
  </div>
{:else if context && dashboard}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Dashboard</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Defined visibility across documentation, approvals, financials, and compliance.
        </p>
      </div>
      <div class="flex items-center gap-2">
        {#if context.is_preview_mode}
          <span class="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
            Preview Mode
          </span>
        {/if}
        {#if dashboard.primary_role}
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-semibold text-neutral-700">
            {titleCase(dashboard.primary_role)}
          </span>
        {/if}
        <button
          onclick={() => loadPortalDashboard()}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          Refresh
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
      {#each dashboard.kpis as kpi, idx (kpi.key)}
        <div
          class="rounded-xl border border-neutral-200 border-t-4 bg-white p-4"
          style={`border-top-color: ${[
            "#10b981",
            "#2563eb",
            "#f59e0b",
            "#7c3aed",
            "#ef4444",
            "#0f172a",
          ][idx % 6]}`}
        >
          <p class="text-[10px] uppercase tracking-wider text-neutral-400">{kpi.label}</p>
          <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{kpi.value}</p>
        </div>
      {/each}
    </div>

    {#if Object.keys(dashboard.role_summary).length > 0}
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Role Summary</h2>
        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {#each summaryEntries(dashboard.role_summary) as row (row.key)}
            <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3">
              <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">{row.key}</p>
              <p class="mt-1 text-base font-semibold text-neutral-900">{row.value}</p>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div class="rounded-xl border border-neutral-200 bg-white xl:col-span-2">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Recently Accessible Documents</h3>
        </div>
        {#if dashboard.recent_documents.length === 0}
          <div class="px-5 py-10 text-center text-sm text-neutral-500">No documents available for this portal scope.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-100 text-sm">
              <thead class="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Document</th>
                  <th class="px-4 py-3 text-left">Status</th>
                  <th class="px-4 py-3 text-left">Confidentiality</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each dashboard.recent_documents as doc (doc.id)}
                  <tr>
                    <td class="px-4 py-3">
                      <p class="font-medium text-neutral-900">{doc.document_number}</p>
                      <p class="text-xs text-neutral-500">{doc.title}</p>
                    </td>
                    <td class="px-4 py-3 text-neutral-700">{titleCase(doc.status)}</td>
                    <td class="px-4 py-3 text-neutral-700">{titleCase(doc.confidentiality_level)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <div class="space-y-6">
        <div class="rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Upcoming Expiry</h3>
          </div>
          {#if dashboard.upcoming_expiries.length === 0}
            <div class="px-5 py-6 text-sm text-neutral-500">No upcoming expiries in the next 90 days.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each dashboard.upcoming_expiries as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{row.document_number}</p>
                  <p class="text-xs text-neutral-600">{titleCase(row.trigger_category)} • {row.expiry_date}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Pending Sign-offs</h3>
          </div>
          {#if dashboard.pending_signoffs.length === 0}
            <div class="px-5 py-6 text-sm text-neutral-500">No pending sign-offs.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each dashboard.pending_signoffs as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{row.document_number}</p>
                  <p class="text-xs text-neutral-600">v{row.version_major}.{row.version_minor} • {titleCase(row.approval_status)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
