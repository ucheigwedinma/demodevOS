<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { JobOfferListItem, JobOffer, OfferStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<JobOfferListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    candidate: "" as string,
    requisition: "" as string,
    position: "" as string,
    offered_salary: "",
    start_date: "",
    expiry_date: "",
    terms: "",
    notes: "",
  });
  let candidateOptions = $state<{ id: number; full_name: string }[]>([]);
  let requisitionOptions = $state<{ id: number; title: string }[]>([]);
  let positionOptions = $state<{ id: number; title: string }[]>([]);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<OfferStatus, string> = {
    draft: "Draft",
    pending_approval: "Pending Approval",
    approved: "Approved",
    extended: "Extended",
    accepted: "Accepted",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
    expired: "Expired",
  };

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<JobOfferListItem>>("/hr/job-offers/", params);
      items = res.results;
      totalCount = res.count;
    } catch {
      items = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = { candidate: "", requisition: "", position: "", offered_salary: "", start_date: "", expiry_date: "", terms: "", notes: "" };
    fieldErrors = {};
    editingId = null;
  }

  async function loadOptions() {
    try {
      const [candRes, reqRes, posRes] = await Promise.all([
        api.get<{ results: { id: number; full_name: string }[] }>("/hr/candidates/", { page_size: "200" }),
        api.get<{ results: { id: number; title: string }[] }>("/hr/requisitions/", { page_size: "200" }),
        api.get<{ results: { id: number; title: string }[] }>("/hr/positions/", { page_size: "200" }),
      ]);
      candidateOptions = candRes.results;
      requisitionOptions = reqRes.results;
      positionOptions = posRes.results;
    } catch { /* ignore */ }
  }

  async function openCreate() {
    resetForm();
    await loadOptions();
    showSlideOver = true;
  }

  async function openEdit(item: JobOfferListItem) {
    resetForm();
    editingId = item.id;
    form.candidate = item.candidate ? String(item.candidate) : "";
    form.requisition = item.requisition ? String(item.requisition) : "";
    form.position = item.position ? String(item.position) : "";
    form.offered_salary = item.offered_salary ?? "";
    form.start_date = item.start_date ?? "";
    form.expiry_date = item.expiry_date ?? "";
    await loadOptions();
    try {
      const detail = await api.get<JobOffer>(`/hr/job-offers/${item.id}/`);
      form.terms = detail.terms ?? "";
      form.notes = detail.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        offered_salary: form.offered_salary,
        currency: currency.config.code,
        terms: form.terms,
        notes: form.notes,
      };
      if (form.candidate) payload.candidate = Number(form.candidate);
      if (form.requisition) payload.requisition = Number(form.requisition);
      if (form.position) payload.position = Number(form.position);
      if (form.start_date) payload.start_date = form.start_date;
      if (form.expiry_date) payload.expiry_date = form.expiry_date;

      if (isEditing) {
        await api.patch(`/hr/job-offers/${editingId}/`, payload);
        toast.success("Offer updated");
      } else {
        await api.post("/hr/job-offers/", payload);
        toast.success("Offer created");
      }
      showSlideOver = false;
      resetForm();
      fetchItems();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const message = err.fieldErrors.non_field_errors?.[0] ?? Object.values(err.fieldErrors)[0]?.[0] ?? "Please fix the highlighted fields and try again.";
        toast.error("Validation error", message);
      }
      else toast.error("Failed to save offer");
    } finally {
      saving = false;
    }
  }

  async function submitForApproval(id: number) {
    try {
      await api.post(`/hr/job-offers/${id}/submit_for_approval/`, {});
      toast.success("Offer submitted for approval");
      fetchItems();
    } catch {
      toast.error("Failed to submit for approval");
    }
  }

  async function extendOffer(id: number) {
    try {
      await api.post(`/hr/job-offers/${id}/extend/`, {});
      toast.success("Offer extended to candidate");
      fetchItems();
    } catch {
      toast.error("Failed to extend offer");
    }
  }

  async function acceptOffer(id: number) {
    try {
      await api.post(`/hr/job-offers/${id}/accept/`, {});
      toast.success("Offer accepted");
      fetchItems();
    } catch {
      toast.error("Failed to accept offer");
    }
  }

  async function rejectOffer(id: number) {
    try {
      await api.post(`/hr/job-offers/${id}/reject/`, {});
      toast.success("Offer rejected");
      fetchItems();
    } catch {
      toast.error("Failed to reject offer");
    }
  }

  async function withdrawOffer(id: number) {
    try {
      await api.post(`/hr/job-offers/${id}/withdraw/`, {});
      toast.success("Offer withdrawn");
      fetchItems();
    } catch {
      toast.error("Failed to withdraw offer");
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchItems();
  }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Offer Management</h1>
      <p class="mt-1 text-sm text-neutral-500">Extend, track, and manage job offers</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Create Offer
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search offers..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No offers match your filters" : "No offers yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/50">
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Candidate</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position</th>
              <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Salary</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Start Date</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Expiry Date</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each items as item}
              <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
                <td class="px-5 py-3.5 font-medium text-neutral-900">{item.candidate_name}</td>
                <td class="px-5 py-3.5 text-neutral-600">{item.position_title ?? "\u2014"}</td>
                <td class="px-5 py-3.5 text-right text-neutral-600 tabular-nums">{item.offered_salary ? currency.format(item.offered_salary) : "\u2014"}</td>
                <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(item.start_date)}</td>
                <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(item.expiry_date)}</td>
                <td class="px-5 py-3.5 text-center">
                  <StatusBadge status={item.status} />
                </td>
                <td class="px-5 py-3.5 text-center">
                  <div class="inline-flex items-center gap-2">
                    {#if item.status === "draft"}
                      <button onclick={(e) => { e.stopPropagation(); submitForApproval(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Submit</button>
                    {/if}
                    {#if item.status === "approved" || item.status === "extended"}
                      <button onclick={(e) => { e.stopPropagation(); extendOffer(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Extend</button>
                      <button onclick={(e) => { e.stopPropagation(); acceptOffer(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Accept</button>
                      <button onclick={(e) => { e.stopPropagation(); rejectOffer(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Reject</button>
                    {/if}
                    {#if item.status === "pending_approval"}
                      <button onclick={(e) => { e.stopPropagation(); withdrawOffer(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Withdraw</button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} offer{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Offer" : "New Offer"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="offer-candidate" class="block text-sm font-medium text-neutral-700 mb-1">Candidate <span class="text-red-500">*</span></label>
          <select id="offer-candidate" bind:value={form.candidate} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('candidate') ? 'border-red-400' : ''}">
            <option value="">Select candidate</option>
            {#each candidateOptions as cand}<option value={String(cand.id)}>{cand.full_name}</option>{/each}
          </select>
          {#if fieldError("candidate")}<p class="text-xs text-red-500 mt-1">{fieldError("candidate")}</p>{/if}
        </div>
        <div>
          <label for="offer-requisition" class="block text-sm font-medium text-neutral-700 mb-1">Requisition</label>
          <select id="offer-requisition" bind:value={form.requisition} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">None</option>
            {#each requisitionOptions as req}<option value={String(req.id)}>{req.title}</option>{/each}
          </select>
        </div>
        <div>
          <label for="offer-position" class="block text-sm font-medium text-neutral-700 mb-1">Position</label>
          <select id="offer-position" bind:value={form.position} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">None</option>
            {#each positionOptions as pos}<option value={String(pos.id)}>{pos.title}</option>{/each}
          </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="offer-salary" class="block text-sm font-medium text-neutral-700 mb-1">Offered Salary <span class="text-red-500">*</span></label>
            <input id="offer-salary" type="text" bind:value={form.offered_salary} placeholder="0.00" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('offered_salary') ? 'border-red-400' : ''}" />
            {#if fieldError("offered_salary")}<p class="text-xs text-red-500 mt-1">{fieldError("offered_salary")}</p>{/if}
          </div>
          <div>
            <p class="block text-sm font-medium text-neutral-700 mb-1">Currency</p>
            <p class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-neutral-50 text-neutral-700">{currency.config.code}</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="offer-start" class="block text-sm font-medium text-neutral-700 mb-1">Start Date</label>
            <DateInput id="offer-start" bind:value={form.start_date} />
            {#if fieldError("start_date")}<p class="text-xs text-red-500 mt-1">{fieldError("start_date")}</p>{/if}
          </div>
          <div>
            <label for="offer-expiry" class="block text-sm font-medium text-neutral-700 mb-1">Expiry Date</label>
            <DateInput id="offer-expiry" bind:value={form.expiry_date} />
            {#if fieldError("expiry_date")}<p class="text-xs text-red-500 mt-1">{fieldError("expiry_date")}</p>{/if}
          </div>
        </div>
        <div>
          <label for="offer-terms" class="block text-sm font-medium text-neutral-700 mb-1">Terms</label>
          <textarea id="offer-terms" bind:value={form.terms} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
          {#if fieldError("terms")}<p class="text-xs text-red-500 mt-1">{fieldError("terms")}</p>{/if}
        </div>
        <div>
          <label for="offer-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="offer-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
