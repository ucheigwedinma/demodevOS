<script lang="ts">
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages } from "$lib/contracts";
  import type { DocumentExpiryRecord } from "$lib/types";

  let loading = $state(true);
  let rows = $state<DocumentExpiryRecord[]>([]);

  function fmtDate(value: string): string {
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

  async function load() {
    loading = true;
    try {
      rows = await fetchAllPages<DocumentExpiryRecord>("/documents/control/expiries/", {
        ordering: "expiry_date",
        page_size: "200",
      });
    } catch {
      toast.error("Load failed", "Could not load retention and expiry tracking.");
      rows = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    load();
  });

  const expiring30 = $derived.by(() => rows.filter((row) => {
    const d = daysTo(row.expiry_date);
    return d >= 0 && d <= 30;
  }).length);
  const expiring60 = $derived.by(() => rows.filter((row) => {
    const d = daysTo(row.expiry_date);
    return d >= 31 && d <= 60;
  }).length);
  const expiring90 = $derived.by(() => rows.filter((row) => {
    const d = daysTo(row.expiry_date);
    return d >= 61 && d <= 90;
  }).length);
  const expired = $derived.by(() => rows.filter((row) => daysTo(row.expiry_date) < 0).length);

  const categoryCounts = $derived.by(() => {
    const map = new Map<string, number>();
    for (const row of rows) {
      map.set(row.trigger_category, (map.get(row.trigger_category) ?? 0) + 1);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Retention Tracking</h1>
    <p class="mt-1 text-sm text-neutral-500">Contract-linked expiry and alert lifecycle for compliance control.</p>
  </div>

  {#if loading}
    <div class="py-20 text-center">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiring 30d</p>
        <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">{expiring30}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiring 60d</p>
        <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">{expiring60}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiring 90d</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{expiring90}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expired</p>
        <p class="mt-1 text-xl font-bold text-red-700 tabular-nums">{expired}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Tracked Records</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{rows.length}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Expiry Register</h2>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Document</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Category</th>
              <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Expiry</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows.slice(0, 14) as row}
              <tr>
                <td class="px-5 py-3 font-medium text-neutral-900">{row.document_number}</td>
                <td class="px-5 py-3 text-neutral-600">{row.trigger_category}</td>
                <td class="px-5 py-3 text-right text-neutral-700">{fmtDate(row.expiry_date)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Trigger Categories</h2>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Category</th>
              <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Count</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each categoryCounts as [key, count]}
              <tr>
                <td class="px-5 py-3 text-neutral-700">{key}</td>
                <td class="px-5 py-3 text-right font-medium tabular-nums text-neutral-900">{count}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
