<script lang="ts">
  import { goto } from "$app/navigation";
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, isClaimIssue, isDisputeIssue, isMainContractDocument, isSubcontractDocument, toAmount } from "$lib/contracts";
  import { currency } from "$lib/stores/currency.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    DocumentExpiryRecord,
    DocumentRecord,
    ProjectFieldEscalation,
    ProjectVariationOrder,
  } from "$lib/types";

  let loading = $state(true);
  let contracts = $state<DocumentRecord[]>([]);
  let variations = $state<ProjectVariationOrder[]>([]);
  let issues = $state<ProjectFieldEscalation[]>([]);
  let expiries = $state<DocumentExpiryRecord[]>([]);

  function fmtCurrency(value: number): string {
    return currency.format(value);
  }

  function fmtDate(value: string | null): string {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function daysTo(date: string): number {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const target = new Date(`${date}T00:00:00`);
    return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  }

  async function loadAll() {
    loading = true;
    try {
      const [contractRows, variationRows, issueRows, expiryRows] = await Promise.all([
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "CON",
          ordering: "-created_at",
          page_size: "200",
        }),
        fetchAllPages<ProjectVariationOrder>("/projects/variations/", {
          ordering: "-created_at",
          page_size: "200",
        }),
        fetchAllPages<ProjectFieldEscalation>("/projects/issues/", {
          ordering: "-issue_date",
          page_size: "200",
        }),
        fetchAllPages<DocumentExpiryRecord>("/documents/control/expiries/", {
          ordering: "expiry_date",
          page_size: "200",
        }),
      ]);
      contracts = contractRows;
      variations = variationRows;
      issues = issueRows;
      expiries = expiryRows;
    } catch {
      toast.error("Load failed", "Could not load contracts overview.");
      contracts = [];
      variations = [];
      issues = [];
      expiries = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadAll();
  });

  const live = useLiveKpis(
    ["Contract", "VariationOrder", "Document"],
    loadAll,
    { debounceMs: 3000 },
  );

  const mainContracts = $derived.by(() => contracts.filter(isMainContractDocument));
  const subcontracts = $derived.by(() => contracts.filter(isSubcontractDocument));
  const activeExposure = $derived.by(() =>
    mainContracts
      .filter((doc) => doc.status !== "archived" && doc.status !== "superseded")
      .reduce((sum, doc) => sum + toAmount(doc.contract_value), 0)
  );
  const approvedVariationValue = $derived.by(() =>
    variations
      .filter((row) => row.status === "approved")
      .reduce((sum, row) => sum + toAmount(row.contract_value), 0)
  );
  const claimsOpen = $derived.by(() =>
    issues.filter((row) => isClaimIssue(row) && row.status !== "resolved" && row.status !== "closed").length
  );
  const disputesOpen = $derived.by(() =>
    issues.filter((row) => isDisputeIssue(row) && row.status !== "resolved" && row.status !== "closed").length
  );
  const expiring30 = $derived.by(() =>
    expiries.filter((row) => {
      const days = daysTo(row.expiry_date);
      return days >= 0 && days <= 30;
    }).length
  );
  const expiring60 = $derived.by(() =>
    expiries.filter((row) => {
      const days = daysTo(row.expiry_date);
      return days >= 31 && days <= 60;
    }).length
  );
  const expiring90 = $derived.by(() =>
    expiries.filter((row) => {
      const days = daysTo(row.expiry_date);
      return days >= 61 && days <= 90;
    }).length
  );
  const exposureRows = $derived.by(() =>
    [...mainContracts]
      .sort((a, b) => toAmount(b.contract_value) - toAmount(a.contract_value))
      .slice(0, 8)
  );
  const expiryRows = $derived.by(() =>
    [...expiries]
      .sort((a, b) => a.expiry_date.localeCompare(b.expiry_date))
      .slice(0, 8)
  );
</script>

<div class="space-y-6">
  <div>
    <div class="flex items-center gap-2">
      <h1 class="text-2xl font-bold text-neutral-900">Contracts</h1>
      <LiveBadge refreshing={live.refreshing} />
    </div>
    <p class="mt-1 text-sm text-neutral-500">
      Legal and commercial execution overview across contracts, variations, claims, disputes, and expiry risk.
    </p>
  </div>

  {#if loading}
    <div class="py-20 text-center">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-7">
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Main Contracts</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{mainContracts.length}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Subcontracts</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{subcontracts.length}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Exposure</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(activeExposure)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Executed Value</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(approvedVariationValue)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Open Claims</p>
        <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">{claimsOpen}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Open Disputes</p>
        <p class="mt-1 text-xl font-bold text-red-700 tabular-nums">{disputesOpen}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiry 30/60/90</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{expiring30}/{expiring60}/{expiring90}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Exposure Analysis</h2>
          <button class="text-xs font-medium text-neutral-600 hover:text-neutral-900" onclick={() => goto("/contracts/main-contracts")}>
            View all
          </button>
        </div>
        {#if exposureRows.length === 0}
          <div class="px-5 py-10 text-sm text-neutral-500">No contract exposure records yet.</div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Contract</th>
                <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-5 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Value</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each exposureRows as row}
                <tr>
                  <td class="px-5 py-3">
                    <p class="font-medium text-neutral-900">{row.document_number}</p>
                    <p class="truncate text-xs text-neutral-500 max-w-[280px]">{row.title}</p>
                  </td>
                  <td class="px-5 py-3 text-neutral-600">{row.project_name || "—"}</td>
                  <td class="px-5 py-3 text-right font-medium tabular-nums text-neutral-900">
                    {fmtCurrency(toAmount(row.contract_value))}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Expiry Alerts</h2>
          <button class="text-xs font-medium text-neutral-600 hover:text-neutral-900" onclick={() => goto("/contracts/retention-tracking")}>
            View all
          </button>
        </div>
        {#if expiryRows.length === 0}
          <div class="px-5 py-10 text-sm text-neutral-500">No expiry records available.</div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Document</th>
                <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Category</th>
                <th class="px-5 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Expiry</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each expiryRows as row}
                <tr>
                  <td class="px-5 py-3 font-medium text-neutral-900">{row.document_number}</td>
                  <td class="px-5 py-3 text-neutral-600">{row.trigger_category}</td>
                  <td class="px-5 py-3 text-right text-neutral-700">{fmtDate(row.expiry_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  {/if}
</div>
