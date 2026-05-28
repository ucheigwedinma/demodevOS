<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { HeadcountSnapshotListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<HeadcountSnapshotListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    snapshot_date: "",
    department: "",
    team: "",
    active_count: "0",
    inactive_count: "0",
    new_hires: "0",
    departures: "0",
    contractors: "0",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<HeadcountSnapshotListItem>>("/hr/headcount-snapshots/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { snapshot_date: "", department: "", team: "", active_count: "0", inactive_count: "0", new_hires: "0", departures: "0", contractors: "0", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: HeadcountSnapshotListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/headcount-snapshots/${item.id}/`);
      form.snapshot_date = d.snapshot_date ?? "";
      form.department = d.department ?? "";
      form.team = d.team ?? "";
      form.active_count = String(d.active_count ?? 0);
      form.inactive_count = String(d.inactive_count ?? 0);
      form.new_hires = String(d.new_hires ?? 0);
      form.departures = String(d.departures ?? 0);
      form.contractors = String(d.contractors ?? 0);
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        snapshot_date: form.snapshot_date,
        active_count: Number(form.active_count),
        inactive_count: Number(form.inactive_count),
        new_hires: Number(form.new_hires),
        departures: Number(form.departures),
        contractors: Number(form.contractors),
      };
      if (form.department) payload.department = form.department;
      if (form.team) payload.team = form.team;
      if (form.notes) payload.notes = form.notes;
      if (isEditing) { await api.patch(`/hr/headcount-snapshots/${editingId}/`, payload); toast.success("Snapshot updated"); }
      else { await api.post("/hr/headcount-snapshots/", payload); toast.success("Snapshot created"); }
      showSlideOver = false; resetForm(); fetchItems();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const message = err.fieldErrors.non_field_errors?.[0] ?? Object.values(err.fieldErrors)[0]?.[0] ?? "Please fix the highlighted fields and try again.";
        toast.error("Validation error", message);
      }
      else toast.error("Failed to save");
    } finally { saving = false; }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(v: string) { searchQuery = v; clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300); }
  function goToPage(p: number) { if (p >= 1 && p <= totalPages) { currentPage = p; fetchItems(); } }
  function fieldError(f: string): string { return fieldErrors[f]?.[0] ?? ""; }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Headcount Analytics</h1>
      <p class="mt-1 text-sm text-neutral-500">Track headcount snapshots across departments and teams</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Snapshot
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search by department or team..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery ? "No snapshots match your search" : "No headcount snapshots yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Team</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Active</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Total</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">New Hires</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Departures</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Contractors</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.snapshot_date}</td>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.department || "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.team || "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{item.active_count}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right tabular-nums">{item.total_headcount}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right tabular-nums">{item.new_hires}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right tabular-nums">{item.departures}</td>
              <td class="px-5 py-3.5 text-neutral-500 text-right tabular-nums">{item.contractors}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} snapshot{totalCount !== 1 ? "s" : ""}</span>
        <div class="flex items-center gap-1">
          <button onclick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&laquo;</button>
          {#each Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1) as p}
            <button onclick={() => goToPage(p)} class="px-2.5 py-1 rounded text-sm {p === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}">{p}</button>
          {/each}
          <button onclick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&raquo;</button>
        </div>
      </div>
    {/if}
  {/if}
</div>

{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Snapshot" : "New Headcount Snapshot"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="hc-date" class="block text-sm font-medium text-neutral-700 mb-1">Snapshot Date <span class="text-red-500">*</span></label>
          <DateInput id="hc-date" bind:value={form.snapshot_date} />
          {#if fieldError("snapshot_date")}<p class="text-xs text-red-500 mt-1">{fieldError("snapshot_date")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hc-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department</label>
            <input id="hc-dept" type="text" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="hc-team" class="block text-sm font-medium text-neutral-700 mb-1">Team</label>
            <input id="hc-team" type="text" bind:value={form.team} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hc-active" class="block text-sm font-medium text-neutral-700 mb-1">Active Count</label>
            <input id="hc-active" type="number" bind:value={form.active_count} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hc-inactive" class="block text-sm font-medium text-neutral-700 mb-1">Inactive Count</label>
            <input id="hc-inactive" type="number" bind:value={form.inactive_count} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="hc-hires" class="block text-sm font-medium text-neutral-700 mb-1">New Hires</label>
            <input id="hc-hires" type="number" bind:value={form.new_hires} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hc-dep" class="block text-sm font-medium text-neutral-700 mb-1">Departures</label>
            <input id="hc-dep" type="number" bind:value={form.departures} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hc-con" class="block text-sm font-medium text-neutral-700 mb-1">Contractors</label>
            <input id="hc-con" type="number" bind:value={form.contractors} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="hc-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="hc-notes" bind:value={form.notes} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>
