<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface BomVersion {
    id: number; bom_number: string; name: string; description: string;
    project: number | null; project_name: string | null;
    status: string; version: number; parent_version: number | null;
    confidence_pct: number; margin_pct: string; vat_pct: string;
    total_estimated_cost: string; grand_total: string;
    revision_reason: string; is_baseline: boolean;
    item_count: number; created_by_name: string; created_at: string; updated_at: string;
  }
  interface BomItem {
    id: number; material_name: string; category: string; section: string;
    quantity: string; unit_of_measure: string; unit_cost: string; line_total: string;
  }
  interface BomDetail extends BomVersion { items: BomItem[]; }
  interface DiffRow {
    material_name: string; section: string; unit: string;
    baseQty: number; baseRate: number; baseTotal: number;
    currQty: number; currRate: number; currTotal: number;
    status: "added" | "removed" | "changed" | "unchanged";
    qtyChanged: boolean; rateChanged: boolean;
  }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-200 text-neutral-600", in_review: "bg-blue-100 text-blue-700",
    pending_approval: "bg-blue-100 text-blue-700", approved: "bg-emerald-100 text-emerald-700",
    archived: "bg-neutral-200 text-neutral-400",
  };

  let loading = $state(true);
  let allVersions = $state<BomVersion[]>([]);
  let projectFilter = $state("");

  // Compare
  let baseVersionId = $state<number | null>(null);
  let currVersionId = $state<number | null>(null);
  let baseDetail = $state<BomDetail | null>(null);
  let currDetail = $state<BomDetail | null>(null);
  let comparing = $state(false);

  // Create revision
  let showCreateModal = $state(false);
  let createSourceId = $state<number | null>(null);
  let createReason = $state("");
  let creating = $state(false);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // Group versions by project/parent chain
  const versionGroups = $derived.by(() => {
    const map = new Map<string, BomVersion[]>();
    for (const v of allVersions) {
      const key = v.project_name || v.name.split(" — ")[0] || "Ungrouped";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(v);
    }
    // Sort each group by version desc
    for (const [, arr] of map) arr.sort((a, b) => b.version - a.version);
    return map;
  });

  const filtered = $derived.by(() => {
    if (!projectFilter) return versionGroups;
    const map = new Map<string, BomVersion[]>();
    for (const [key, arr] of versionGroups) {
      if (key.toLowerCase().includes(projectFilter.toLowerCase())) map.set(key, arr);
    }
    return map;
  });

  // Diff engine
  const diffRows = $derived.by((): DiffRow[] => {
    if (!baseDetail || !currDetail) return [];
    const baseMap = new Map(baseDetail.items.map(i => [i.material_name + "|" + i.section, i]));
    const currMap = new Map(currDetail.items.map(i => [i.material_name + "|" + i.section, i]));
    const rows: DiffRow[] = [];
    const allKeys = new Set([...baseMap.keys(), ...currMap.keys()]);

    for (const key of allKeys) {
      const b = baseMap.get(key);
      const c = currMap.get(key);
      if (b && !c) {
        rows.push({ material_name: b.material_name, section: b.section, unit: b.unit_of_measure, baseQty: Number(b.quantity), baseRate: Number(b.unit_cost), baseTotal: Number(b.line_total), currQty: 0, currRate: 0, currTotal: 0, status: "removed", qtyChanged: true, rateChanged: true });
      } else if (!b && c) {
        rows.push({ material_name: c.material_name, section: c.section, unit: c.unit_of_measure, baseQty: 0, baseRate: 0, baseTotal: 0, currQty: Number(c.quantity), currRate: Number(c.unit_cost), currTotal: Number(c.line_total), status: "added", qtyChanged: true, rateChanged: true });
      } else if (b && c) {
        const bq = Number(b.quantity), br = Number(b.unit_cost), bt = Number(b.line_total);
        const cq = Number(c.quantity), cr = Number(c.unit_cost), ct = Number(c.line_total);
        const qtyChanged = Math.abs(bq - cq) > 0.01;
        const rateChanged = Math.abs(br - cr) > 0.01;
        rows.push({ material_name: c.material_name, section: c.section, unit: c.unit_of_measure, baseQty: bq, baseRate: br, baseTotal: bt, currQty: cq, currRate: cr, currTotal: ct, status: qtyChanged || rateChanged ? "changed" : "unchanged", qtyChanged, rateChanged });
      }
    }
    return rows.sort((a, b) => {
      const order = { removed: 0, added: 1, changed: 2, unchanged: 3 };
      return order[a.status] - order[b.status];
    });
  });

  const totalBaseValue = $derived(diffRows.reduce((s, r) => s + r.baseTotal, 0));
  const totalCurrValue = $derived(diffRows.reduce((s, r) => s + r.currTotal, 0));
  const totalDelta = $derived(totalCurrValue - totalBaseValue);
  const changedCount = $derived(diffRows.filter(r => r.status !== "unchanged").length);
  const addedCount = $derived(diffRows.filter(r => r.status === "added").length);
  const removedCount = $derived(diffRows.filter(r => r.status === "removed").length);

  function fmt(n: number): string { return `\u20A6${Math.round(n).toLocaleString()}`; }
  function timeAgo(d: string): string {
    const diff = Date.now() - new Date(d).getTime();
    const hrs = Math.floor(diff / 3600000);
    if (hrs < 1) return `${Math.floor(diff / 60000)}m ago`;
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  async function loadVersions() {
    loading = true;
    try {
      const res = await api.get<{ results: BomVersion[] }>("/bom/", { page_size: "500" });
      allVersions = res.results;
    } catch { toast.error("Load failed", "Could not load versions."); }
    finally { loading = false; }
  }

  async function runCompare() {
    if (!baseVersionId || !currVersionId) return;
    comparing = true;
    try {
      const [b, c] = await Promise.all([
        api.get<BomDetail>(`/bom/${baseVersionId}/`),
        api.get<BomDetail>(`/bom/${currVersionId}/`),
      ]);
      baseDetail = b;
      currDetail = c;
    } catch { toast.error("Failed", "Could not load versions for comparison."); }
    finally { comparing = false; }
  }

  async function createRevision() {
    if (!createSourceId || !createReason.trim()) { toast.error("Required", "Reason is mandatory."); return; }
    creating = true;
    try {
      const cloned = await api.post<BomDetail>(`/bom/${createSourceId}/clone/`, {});
      await api.patch(`/bom/${cloned.id}/`, { revision_reason: createReason });
      toast.success("Revision Created", `v${cloned.version} created from source.`);
      showCreateModal = false;
      createReason = "";
      await loadVersions();
    } catch { toast.error("Failed", "Could not create revision."); }
    finally { creating = false; }
  }

  async function setBaseline(bomId: number) {
    try {
      await api.patch(`/bom/${bomId}/`, { is_baseline: true });
      toast.success("Baseline Set", "This version is now the baseline reference.");
      await loadVersions();
    } catch { toast.error("Failed", "Could not set baseline."); }
  }

  async function promoteToMaster(bomId: number) {
    try {
      await api.patch(`/bom/${bomId}/`, { status: "approved" });
      toast.success("Promoted", "Revision promoted to approved Master BoQ.");
      await loadVersions();
    } catch { toast.error("Failed", "Could not promote."); }
  }

  async function restoreVersion(bomId: number) {
    if (!confirm("Restore this version as the current Master? This will clone it as a new version.")) return;
    try {
      const cloned = await api.post<BomDetail>(`/bom/${bomId}/clone/`, {});
      await api.patch(`/bom/${cloned.id}/`, { status: "approved", revision_reason: `Restored from v${allVersions.find(v => v.id === bomId)?.version || "?"}` });
      toast.success("Restored", `Version restored as v${cloned.version}.`);
      await loadVersions();
    } catch { toast.error("Failed", "Could not restore version."); }
  }

  onMount(() => { loadVersions(); });
</script>

<svelte:head><title>Revisions | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Revisions</h1>
      <p class="mt-1 text-sm text-neutral-500">Audit trail for budget changes. Every revision documented, authorized, and reversible.</p>
    </div>
  </div>

  <!-- Compare Controls -->
  <div class="rounded-xl border border-neutral-200 bg-white/80 p-5" style="backdrop-filter: blur(10px)">
    <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Compare Engine</h3>
    <div class="flex flex-wrap items-end gap-3">
      <div class="w-64">
        <label class="block text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1">Base Version</label>
        <select bind:value={baseVersionId} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value={null}>Select base...</option>
          {#each allVersions as v}<option value={v.id}>{v.bom_number} v{v.version} — {v.name}</option>{/each}
        </select>
      </div>
      <span class="text-neutral-300 text-lg pb-1">&rarr;</span>
      <div class="w-64">
        <label class="block text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1">Current Version</label>
        <select bind:value={currVersionId} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value={null}>Select current...</option>
          {#each allVersions as v}<option value={v.id}>{v.bom_number} v{v.version} — {v.name}</option>{/each}
        </select>
      </div>
      <button onclick={runCompare} disabled={!baseVersionId || !currVersionId || comparing} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{comparing ? "Loading..." : "Compare"}</button>
    </div>
  </div>

  <!-- 2. Diff View -->
  {#if baseDetail && currDetail}
    <!-- Variance summary -->
    <div class="flex gap-3 flex-wrap">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {totalDelta > 0 ? 'text-amber-700' : totalDelta < 0 ? 'text-emerald-700' : 'text-neutral-900'}">{totalDelta > 0 ? "+" : ""}{fmt(totalDelta)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Net Change</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{changedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Changed</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-600 tabular-nums">{addedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Added</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{removedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Removed</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmt(totalBaseValue)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Base Total</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-700 tabular-nums">{fmt(totalCurrValue)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase">Current Total</p>
      </div>
    </div>

    <!-- Diff table -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-200 bg-neutral-800 px-5 py-3 flex items-center justify-between">
        <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">Side-by-Side Diff — v{baseDetail.version} vs v{currDetail.version}</h3>
        <span class="text-[10px] text-neutral-400">{diffRows.length} rows</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-700">
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Item</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200">Section</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-300" colspan="3">Base (v{baseDetail.version})</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-300" colspan="3">Current (v{currDetail.version})</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-200">Delta</th>
            </tr>
            <tr class="border-b border-neutral-600 bg-neutral-700">
              <th class="px-4 py-1"></th><th class="px-3 py-1"></th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Qty</th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Rate</th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Total</th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Qty</th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Rate</th>
              <th class="px-3 py-1 text-right text-[9px] text-neutral-400">Total</th>
              <th class="px-3 py-1"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each diffRows as row}
              {@const delta = row.currTotal - row.baseTotal}
              <tr class="{row.status === 'added' ? 'bg-emerald-50/40' : row.status === 'removed' ? 'bg-amber-50/40' : row.status === 'changed' ? 'bg-blue-50/20' : ''}">
                <td class="px-4 py-2 font-medium {row.status === 'removed' ? 'line-through text-neutral-400' : 'text-neutral-900'}">{row.material_name}</td>
                <td class="px-3 py-2 text-neutral-500">{row.section}</td>
                <td class="px-3 py-2 text-right tabular-nums {row.qtyChanged ? 'font-bold' : 'text-neutral-500'}">{row.baseQty || "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums {row.rateChanged ? 'font-bold' : 'text-neutral-500'}">{row.baseRate ? fmt(row.baseRate) : "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{row.baseTotal ? fmt(row.baseTotal) : "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums {row.qtyChanged ? 'font-bold text-blue-700' : 'text-neutral-500'}">{row.currQty || "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums {row.rateChanged ? 'font-bold text-blue-700' : 'text-neutral-500'}">{row.currRate ? fmt(row.currRate) : "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums font-semibold text-neutral-900">{row.currTotal ? fmt(row.currTotal) : "—"}</td>
                <td class="px-3 py-2 text-right tabular-nums font-bold {delta > 0 ? 'text-amber-700' : delta < 0 ? 'text-emerald-700' : 'text-neutral-400'}">{delta !== 0 ? `${delta > 0 ? "+" : ""}${fmt(delta)}` : "—"}</td>
              </tr>
            {/each}
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-neutral-200 bg-neutral-50">
              <td colspan="4" class="px-4 py-3 font-bold text-neutral-800">Variance</td>
              <td class="px-3 py-3 text-right tabular-nums font-bold text-neutral-800">{fmt(totalBaseValue)}</td>
              <td colspan="2"></td>
              <td class="px-3 py-3 text-right tabular-nums font-bold text-emerald-700">{fmt(totalCurrValue)}</td>
              <td class="px-3 py-3 text-right tabular-nums font-bold {totalDelta > 0 ? 'text-amber-700' : 'text-emerald-700'}">{totalDelta > 0 ? "+" : ""}{fmt(totalDelta)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  {/if}

  <!-- 1. Revision History Timeline -->
  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else}
    <div class="flex items-center gap-3 mb-2">
      <input bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Filter by project..." />
    </div>

    {#each [...filtered.entries()] as [groupName, versions]}
      <div class="rounded-xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(10px)">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-xs font-bold text-neutral-800 uppercase tracking-wider">{groupName}</h3>
        </div>
        <div class="divide-y divide-neutral-50">
          {#each versions as v (v.id)}
            <div class="group px-5 py-4 hover:bg-neutral-50/50 transition-colors relative">
              <!-- Timeline dot -->
              <div class="absolute left-2 top-6 w-2 h-2 rounded-full {v.is_baseline ? 'bg-indigo-500 ring-2 ring-indigo-200' : v.status === 'approved' ? 'bg-emerald-500' : 'bg-neutral-300'}"></div>
              {#if versions.indexOf(v) < versions.length - 1}
                <div class="absolute left-[11px] top-8 bottom-0 w-px bg-neutral-200"></div>
              {/if}

              <div class="flex items-start gap-4 pl-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-neutral-900">v{v.version}</span>
                    <span class="text-xs text-neutral-500">{v.bom_number}</span>
                    <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[v.status] || STATUS_COLORS.draft}">{v.status.replace("_", " ")}</span>
                    {#if v.is_baseline}<span class="rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 text-[9px] font-bold">BASELINE</span>{/if}
                  </div>
                  <p class="text-xs text-neutral-700 mt-0.5">{v.name}</p>
                  {#if v.revision_reason}<p class="text-[10px] text-neutral-500 mt-1 italic">"{v.revision_reason}"</p>{/if}
                  <p class="text-[10px] text-neutral-400 mt-1">{v.created_by_name} &middot; {timeAgo(v.created_at)} &middot; {v.item_count} items</p>
                </div>

                <!-- Impact -->
                <div class="text-right shrink-0">
                  <p class="text-sm font-bold text-emerald-700 tabular-nums">{fmt(Number(v.grand_total || v.total_estimated_cost || 0))}</p>
                  {#if v.parent_version}
                    {@const parent = allVersions.find(p => p.id === v.parent_version)}
                    {#if parent}
                      {@const delta = Number(v.grand_total || v.total_estimated_cost || 0) - Number(parent.grand_total || parent.total_estimated_cost || 0)}
                      <p class="text-[10px] font-bold tabular-nums {delta > 0 ? 'text-amber-700' : delta < 0 ? 'text-emerald-600' : 'text-neutral-400'}">{delta > 0 ? "+" : ""}{fmt(delta)}</p>
                    {/if}
                  {/if}
                </div>

                <!-- Actions -->
                <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button onclick={() => { baseVersionId = v.parent_version; currVersionId = v.id; runCompare(); }} class="rounded border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-500 hover:bg-neutral-50" title="Compare with parent">Diff</button>
                  <button onclick={() => { createSourceId = v.id; showCreateModal = true; }} class="rounded border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-500 hover:bg-neutral-50" title="Create new revision">Revise</button>
                  {#if !v.is_baseline}
                    <button onclick={() => setBaseline(v.id)} class="rounded border border-indigo-200 px-2 py-1 text-[10px] font-medium text-indigo-600 hover:bg-indigo-50" title="Set as baseline">Baseline</button>
                  {/if}
                  {#if v.status !== "approved"}
                    <button onclick={() => promoteToMaster(v.id)} class="rounded bg-emerald-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-emerald-700" title="Promote to Master">Promote</button>
                  {:else}
                    <button onclick={() => restoreVersion(v.id)} class="rounded border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-500 hover:bg-neutral-50" title="Restore this version">Restore</button>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

<!-- Create Revision Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-lg font-semibold text-neutral-900 mb-1">Create Revision</h2>
      <p class="text-sm text-neutral-500 mb-4">Clone this version and document the reason for the change.</p>
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Reason for Revision *</span>
        <textarea bind:value={createReason} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="e.g. Switching from imported to local marble due to FX rates"></textarea>
      </label>
      <div class="mt-5 flex justify-end gap-3">
        <button onclick={() => { showCreateModal = false; createReason = ""; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createRevision} disabled={creating} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{creating ? "Creating..." : "Create Revision"}</button>
      </div>
    </div>
  </div>
{/if}
