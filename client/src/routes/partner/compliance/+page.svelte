<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalComplianceResponse,
    PartnerPortalContextResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let data = $state<PartnerPortalComplianceResponse | null>(null);

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  async function loadCompliance() {
    loading = true;
    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;
      if (!ctx.is_partner_user && !ctx.is_preview_mode) {
        data = null;
        return;
      }
      const result = await api.get<PartnerPortalComplianceResponse>("/partners/portal/compliance/");
      data = result;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal compliance data."));
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadCompliance();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No compliance access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Compliance visibility is enabled when scope entitlements are active.</p>
  </div>
{:else if data}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Partners</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Compliance & Governance</h1>
        <p class="mt-1 text-sm text-neutral-500">Risk, issues, and controlled-document expiry posture within entitlement scope.</p>
      </div>
      <button
        onclick={() => loadCompliance()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Expired Documents</p>
        <p class="mt-1 text-2xl font-bold text-rose-600">{data.summary.expired_documents}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Expiring in 30 Days</p>
        <p class="mt-1 text-2xl font-bold text-amber-600">{data.summary.documents_expiring_30_days}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-violet-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Open Risks</p>
        <p class="mt-1 text-2xl font-bold text-violet-600">{data.summary.open_risks}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-indigo-500 bg-white p-4">
        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Open Issues</p>
        <p class="mt-1 text-2xl font-bold text-indigo-600">{data.summary.open_issues}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div class="rounded-xl border border-neutral-200 bg-white xl:col-span-2">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Project Compliance Scoreboard</h2>
        </div>
        {#if data.project_compliance.length === 0}
          <div class="px-5 py-12 text-sm text-neutral-500">No scoped projects found.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-100 text-sm">
              <thead class="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Project</th>
                  <th class="px-4 py-3 text-left">Score</th>
                  <th class="px-4 py-3 text-left">Status</th>
                  <th class="px-4 py-3 text-left">Last Evaluated</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each data.project_compliance as row (row.project_id)}
                  <tr>
                    <td class="px-4 py-3 text-neutral-900">{row.project_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{row.compliance_score}</td>
                    <td class="px-4 py-3 text-neutral-700">{titleCase(row.compliance_status)}</td>
                    <td class="px-4 py-3 text-neutral-700">{row.compliance_last_evaluated_at ? new Date(row.compliance_last_evaluated_at).toLocaleDateString("en-US") : "--"}</td>
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
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Vendor Compliance</h2>
          </div>
          {#if data.vendor_compliance.length === 0}
            <div class="px-5 py-6 text-sm text-neutral-500">No vendor-scoped compliance rows.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each data.vendor_compliance as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{row.name}</p>
                  <p class="text-xs text-neutral-600">{titleCase(row.compliance_status)} • Rating {row.performance_rating}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Expiring Documents</h2>
          </div>
          {#if data.document_expiries.length === 0}
            <div class="px-5 py-6 text-sm text-neutral-500">No document expiries in scope.</div>
          {:else}
            <div class="space-y-3 px-5 py-4">
              {#each data.document_expiries.slice(0, 8) as row (row.id)}
                <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{row.document_number}</p>
                  <p class="text-xs text-neutral-600">{titleCase(row.trigger_category)} • {row.expiry_date}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div class="rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Open Risks</h2>
        </div>
        {#if data.open_risks_list.length === 0}
          <div class="px-5 py-8 text-sm text-neutral-500">No open risks.</div>
        {:else}
          <div class="space-y-3 px-5 py-4">
            {#each data.open_risks_list.slice(0, 10) as row (row.id)}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <p class="text-sm font-medium text-neutral-900">{row.title}</p>
                <p class="text-xs text-neutral-600">{row.project_name} • {titleCase(row.severity)} • Score {row.risk_score}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Open Issues</h2>
        </div>
        {#if data.open_issues_list.length === 0}
          <div class="px-5 py-8 text-sm text-neutral-500">No open issues.</div>
        {:else}
          <div class="space-y-3 px-5 py-4">
            {#each data.open_issues_list.slice(0, 10) as row (row.id)}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <p class="text-sm font-medium text-neutral-900">{row.title}</p>
                <p class="text-xs text-neutral-600">{row.project_name} • {titleCase(row.issue_type)} • {titleCase(row.status)}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
