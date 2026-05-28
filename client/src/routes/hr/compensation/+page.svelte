<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { CompensationRecord, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // ---------------------------------------------------------------------------
  // List state
  // ---------------------------------------------------------------------------
  let records = $state<CompensationRecord[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // Filters
  let search = $state("");
  let statusFilter = $state("");

  // ---------------------------------------------------------------------------
  // Slide-over state
  // ---------------------------------------------------------------------------
  let showSlideOver = $state(false);
  let saving = $state(false);
  let approving = $state(false);
  let editingId = $state<number | null>(null);
  let fieldErrors = $state<Record<string, string[]>>({});

  let form = $state({
    user: "",
    effective_date: "",
    end_date: "",
    base_salary: "",
    pay_frequency: "monthly",
    allowances: "0",
    bonus: "0",
    total_package: "0",
    status: "draft",
    notes: "",
  });

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);
  let panelTitle = $derived(isEditing ? "Edit Compensation Record" : "New Compensation Record");

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function formatCurrency(value: string): string {
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    return currency.format(num);
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function resetForm() {
    form = {
      user: "",
      effective_date: "",
      end_date: "",
      base_salary: "",
      pay_frequency: "monthly",
      allowances: "0",
      bonus: "0",
      total_package: "0",
      status: "draft",
      notes: "",
    };
    fieldErrors = {};
  }

  function populateForm(record: CompensationRecord) {
    form = {
      user: String(record.user),
      effective_date: record.effective_date ?? "",
      end_date: record.end_date ?? "",
      base_salary: record.base_salary ?? "",
      pay_frequency: record.pay_frequency ?? "monthly",
      allowances: record.allowances ?? "0",
      bonus: record.bonus ?? "0",
      total_package: record.total_package ?? "0",
      status: record.status ?? "draft",
      notes: record.notes ?? "",
    };
  }

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  let debounceTimer: ReturnType<typeof setTimeout>;

  async function fetchRecords() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;

      const res = await api.get<PaginatedResponse<CompensationRecord>>(
        "/hr/compensation-records/",
        params,
      );
      records = res.results;
      totalCount = res.count;
    } catch {
      records = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------
  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchRecords();
    }, 300);
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchRecords();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchRecords();
  }

  // ---------------------------------------------------------------------------
  // Slide-over actions
  // ---------------------------------------------------------------------------
  function openCreate() {
    resetForm();
    editingId = null;
    showSlideOver = true;
  }

  function openEdit(record: CompensationRecord) {
    editingId = record.id;
    populateForm(record);
    fieldErrors = {};
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    editingId = null;
    resetForm();
  }

  async function handleSave(e: Event) {
    e.preventDefault();
    saving = true;
    fieldErrors = {};

    const payload: Record<string, unknown> = {
      user: form.user ? Number(form.user) : null,
      effective_date: form.effective_date || null,
      end_date: form.end_date || null,
      base_salary: form.base_salary || null,
      currency: currency.config.code,
      pay_frequency: form.pay_frequency,
      allowances: form.allowances || "0",
      bonus: form.bonus || "0",
      total_package: form.total_package || "0",
      status: form.status,
      notes: form.notes || "",
    };

    try {
      if (isEditing && editingId) {
        await api.patch<CompensationRecord>(`/hr/compensation-records/${editingId}/`, payload);
        toast.success("Record updated", "Compensation record has been updated successfully.");
      } else {
        await api.post<CompensationRecord>("/hr/compensation-records/", payload);
        toast.success("Record created", "Compensation record has been created successfully.");
      }
      closeSlideOver();
      await fetchRecords();
    } catch (err) {
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields.");
      } else {
        toast.error("Something went wrong", "Could not save the compensation record.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleApprove() {
    if (!editingId) return;
    approving = true;
    try {
      await api.post(`/hr/compensation-records/${editingId}/approve/`, {});
      toast.success("Record approved", "Compensation record has been approved.");
      closeSlideOver();
      await fetchRecords();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Approval failed", err.message);
      } else {
        toast.error("Something went wrong", "Could not approve the record.");
      }
    } finally {
      approving = false;
    }
  }

  async function handleDelete() {
    if (!editingId) return;
    try {
      await api.delete(`/hr/compensation-records/${editingId}/`);
      toast.success("Record deleted", "Compensation record has been removed.");
      closeSlideOver();
      await fetchRecords();
    } catch {
      toast.error("Something went wrong", "Could not delete the record.");
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  $effect(() => {
    fetchRecords();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Compensation Records</h1>
      <p class="mt-1 text-sm text-neutral-500">Employee compensation packages and salary history</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Record
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Employee name..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="superseded">Superseded</option>
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if records.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No compensation records found</p>
        <button
          onclick={openCreate}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first record
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Employee</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Effective Date</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Base Salary</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total Package</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each records as record (record.id)}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openEdit(record)}
              >
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{record.user_name}</div>
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {formatDate(record.effective_date)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-900 text-right tabular-nums">
                  {formatCurrency(record.base_salary)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-900 font-medium text-right tabular-nums">
                  {formatCurrency(record.total_package)}
                </td>
                <td class="px-5 py-4">
                  <StatusBadge status={record.status} />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<!-- ======================================================================= -->
<!-- SLIDE-OVER: Create / Edit Compensation Record                            -->
<!-- ======================================================================= -->
{#if showSlideOver}
  <!-- Backdrop -->
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeSlideOver}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <!-- Panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg flex flex-col bg-white shadow-2xl animate-slide-in-right">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-900">{panelTitle}</h2>
      <button
        onclick={closeSlideOver}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="compensation-form" onsubmit={handleSave} class="space-y-5">
        <!-- Employee -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Employee (User ID)</span>
          <input
            type="number"
            bind:value={form.user}
            required
            placeholder="User ID"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
          />
          {#if fieldError("user")}<p class="mt-1 text-xs text-red-500">{fieldError("user")}</p>{/if}
        </label>

        <!-- Effective Date & End Date -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Effective Date</span>
            <DateInput bind:value={form.effective_date} required />
            {#if fieldError("effective_date")}<p class="mt-1 text-xs text-red-500">{fieldError("effective_date")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">End Date <span class="text-neutral-400 font-normal">(optional)</span></span>
            <DateInput bind:value={form.end_date} />
            {#if fieldError("end_date")}<p class="mt-1 text-xs text-red-500">{fieldError("end_date")}</p>{/if}
          </label>
        </div>

        <!-- Base Salary & Currency -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Base Salary</span>
            <input
              type="text"
              bind:value={form.base_salary}
              required
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("base_salary")}<p class="mt-1 text-xs text-red-500">{fieldError("base_salary")}</p>{/if}
          </label>
          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Currency</span>
            <p class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-neutral-50 text-neutral-700">
              {currency.config.code}
            </p>
          </div>
        </div>

        <!-- Pay Frequency -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Pay Frequency</span>
          <select
            bind:value={form.pay_frequency}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="weekly">Weekly</option>
            <option value="biweekly">Bi-weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="annual">Annual</option>
          </select>
          {#if fieldError("pay_frequency")}<p class="mt-1 text-xs text-red-500">{fieldError("pay_frequency")}</p>{/if}
        </label>

        <!-- Allowances & Bonus -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Allowances</span>
            <input
              type="text"
              bind:value={form.allowances}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("allowances")}<p class="mt-1 text-xs text-red-500">{fieldError("allowances")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Bonus</span>
            <input
              type="text"
              bind:value={form.bonus}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("bonus")}<p class="mt-1 text-xs text-red-500">{fieldError("bonus")}</p>{/if}
          </label>
        </div>

        <!-- Total Package -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Total Package</span>
          <input
            type="text"
            bind:value={form.total_package}
            placeholder="0.00"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
          />
          {#if fieldError("total_package")}<p class="mt-1 text-xs text-red-500">{fieldError("total_package")}</p>{/if}
        </label>

        <!-- Status -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
          <select
            bind:value={form.status}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="superseded">Superseded</option>
          </select>
          {#if fieldError("status")}<p class="mt-1 text-xs text-red-500">{fieldError("status")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.notes}
            rows="3"
            placeholder="Additional notes..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between px-6 py-4 border-t border-neutral-100 shrink-0">
      <div>
        {#if isEditing}
          <button
            type="button"
            onclick={handleDelete}
            class="text-sm text-red-500 hover:text-red-700 font-medium transition-colors"
          >
            Delete
          </button>
        {/if}
      </div>
      <div class="flex items-center gap-3">
        {#if isEditing && form.status === "draft"}
          <button
            type="button"
            onclick={handleApprove}
            disabled={approving}
            class="px-4 py-2.5 bg-neutral-700 text-white rounded-lg text-sm font-medium hover:bg-neutral-600 disabled:opacity-50 transition-colors"
          >
            {approving ? "Approving..." : "Approve"}
          </button>
        {/if}
        <button
          type="button"
          onclick={closeSlideOver}
          class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="compensation-form"
          disabled={saving}
          class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : isEditing ? "Update Record" : "Create Record"}
        </button>
      </div>
    </div>
  </div>
{/if}

<svelte:window onkeydown={(e) => { if (e.key === "Escape" && showSlideOver) closeSlideOver(); }} />

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
