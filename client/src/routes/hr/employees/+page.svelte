<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { EmployeeDirectoryItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let userOptions = $state<{ id: number; full_name: string; employee_id: string }[]>([]);

  async function fetchUserOptions() {
    try {
      const res = await api.get<{ results: { id: number; full_name: string; employee_id: string }[] }>("/iam/users/", { page_size: "200" });
      userOptions = res.results;
    } catch {
      userOptions = [];
    }
  }

  let employees = $state<EmployeeDirectoryItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let drawerMode = $state<"view" | "edit" | "create">("view");
  let viewingEmployee = $state<EmployeeDirectoryItem | null>(null);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    user: "" as string,
    hire_date: "",
    probation_end_date: "",
    contract_start_date: "",
    contract_end_date: "",
    contract_type: "",
    employment_status: "active",
    termination_date: "",
    termination_reason: "",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchEmployees() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.employment_status = filterStatus;
      const res = await api.get<PaginatedResponse<EmployeeDirectoryItem>>("/hr/employee-records/", params);
      employees = res.results;
      totalCount = res.count;
    } catch {
      employees = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = { user: "", hire_date: "", probation_end_date: "", contract_start_date: "", contract_end_date: "", contract_type: "", employment_status: "active", termination_date: "", termination_reason: "", notes: "" };
    fieldErrors = {};
    editingId = null;
  }

  function openCreate() {
    resetForm();
    drawerMode = "create";
    viewingEmployee = null;
    showSlideOver = true;
  }

  function openView(emp: EmployeeDirectoryItem) {
    viewingEmployee = emp;
    drawerMode = "view";
    showSlideOver = true;
  }

  async function openEdit(emp: EmployeeDirectoryItem) {
    resetForm();
    viewingEmployee = emp;
    editingId = emp.id;
    drawerMode = "edit";
    try {
      const detail = await api.get<{ user: number; hire_date: string | null; probation_end_date: string | null; contract_start_date: string | null; contract_end_date: string | null; contract_type: string; employment_status: string; termination_date: string | null; termination_reason: string; notes: string }>(`/hr/employee-records/${emp.id}/`);
      form.user = String(detail.user);
      form.hire_date = detail.hire_date ?? "";
      form.probation_end_date = detail.probation_end_date ?? "";
      form.contract_start_date = detail.contract_start_date ?? "";
      form.contract_end_date = detail.contract_end_date ?? "";
      form.contract_type = detail.contract_type;
      form.employment_status = detail.employment_status;
      form.termination_date = detail.termination_date ?? "";
      form.termination_reason = detail.termination_reason;
      form.notes = detail.notes;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function deleteEmployee(emp: EmployeeDirectoryItem) {
    if (!confirm(`Delete employee record for ${emp.full_name}?`)) return;
    try {
      await api.delete(`/hr/employee-records/${emp.id}/`);
      toast.success("Deleted", `${emp.full_name} removed.`);
      showSlideOver = false;
      fetchEmployees();
    } catch { toast.error("Failed to delete employee record"); }
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        employment_status: form.employment_status,
        contract_type: form.contract_type || undefined,
        notes: form.notes,
      };
      if (form.user) payload.user = Number(form.user);
      if (form.hire_date) payload.hire_date = form.hire_date;
      if (form.probation_end_date) payload.probation_end_date = form.probation_end_date;
      if (form.contract_start_date) payload.contract_start_date = form.contract_start_date;
      if (form.contract_end_date) payload.contract_end_date = form.contract_end_date;
      if (form.termination_date) payload.termination_date = form.termination_date;
      if (form.termination_reason) payload.termination_reason = form.termination_reason;

      if (isEditing) {
        await api.patch(`/hr/employee-records/${editingId}/`, payload);
        toast.success("Employee record updated");
      } else {
        await api.post("/hr/employee-records/", payload);
        toast.success("Employee record created");
      }
      showSlideOver = false;
      resetForm();
      fetchEmployees();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
      } else {
        toast.error("Failed to save employee record");
      }
    } finally {
      saving = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchEmployees(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchEmployees();
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  const statusLabels: Record<string, string> = {
    active: "Active",
    on_leave: "On Leave",
    probation: "Probation",
    notice_period: "Notice Period",
    terminated: "Terminated",
    resigned: "Resigned",
  };

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const EMPLOYEE_SAMPLES = [
    {
      hire_date: "2023-06-15", probation_end_date: "2023-09-15", contract_start_date: "2023-06-15", contract_end_date: "",
      contract_type: "permanent", employment_status: "active", termination_date: "", termination_reason: "",
      notes: "Joined as Senior Site Engineer. Passed probation with commendation from project director.",
    },
    {
      hire_date: "2024-01-08", probation_end_date: "2024-04-08", contract_start_date: "2024-01-08", contract_end_date: "2025-12-31",
      contract_type: "fixed_term", employment_status: "probation", termination_date: "", termination_reason: "",
      notes: "2-year fixed-term contract for Tower C project. Currently in probation period.",
    },
    {
      hire_date: "2022-03-20", probation_end_date: "2022-06-20", contract_start_date: "2022-03-20", contract_end_date: "",
      contract_type: "permanent", employment_status: "on_leave", termination_date: "", termination_reason: "",
      notes: "On approved annual leave. Expected return in 2 weeks. Handover completed to deputy.",
    },
  ];
  let empDevIdx = 0;
  function devFillEmployee() {
    const s = EMPLOYEE_SAMPLES[empDevIdx % EMPLOYEE_SAMPLES.length];
    empDevIdx++;
    form.user = userOptions.length > 0 ? String(userOptions[empDevIdx % userOptions.length].id) : "";
    form.hire_date = s.hire_date;
    form.probation_end_date = s.probation_end_date;
    form.contract_start_date = s.contract_start_date;
    form.contract_end_date = s.contract_end_date;
    form.contract_type = s.contract_type;
    form.employment_status = s.employment_status;
    form.termination_date = s.termination_date;
    form.termination_reason = s.termination_reason;
    form.notes = s.notes;
  }

  $effect(() => {
    fetchEmployees();
    fetchUserOptions();
  });
</script>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Employee Profiles</h1>
      <p class="mt-1 text-sm text-neutral-500">Master record of every worker in the system</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Record
    </button>
  </div>

  <!-- Filters -->
  <div class="flex items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input
        type="text"
        placeholder="Search employees..."
        value={searchQuery}
        oninput={(e) => handleSearch(e.currentTarget.value)}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>
    <select
      value={filterStatus}
      onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchEmployees(); }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [val, label]}
        <option value={val}>{label}</option>
      {/each}
    </select>
  </div>

  <!-- Table -->
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if employees.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No employees match your filters" : "No employee records yet"}</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">ID</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Hire Date</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="px-3 py-3 w-16"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each employees as emp}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer group" onclick={() => openView(emp)}>
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-3">
                  {#if emp.profile_photo}
                    <img src={emp.profile_photo} alt="" class="h-8 w-8 rounded-full object-cover" />
                  {:else}
                    <div class="h-8 w-8 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-500">
                      {emp.full_name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()}
                    </div>
                  {/if}
                  <div>
                    <p class="font-medium text-neutral-900">{emp.full_name}</p>
                    <p class="text-xs text-neutral-400">{emp.job_title || emp.email}</p>
                  </div>
                </div>
              </td>
              <td class="px-5 py-3.5">
                <span class="font-mono text-xs text-neutral-400">{emp.id}</span>
                {#if emp.employee_id}
                  <span class="block font-mono text-xs text-neutral-500 mt-0.5">{emp.employee_id}</span>
                {/if}
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{emp.department_name ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{emp.position_title ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{emp.hire_date ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {emp.employment_status === 'active' ? 'bg-neutral-900 text-white' : emp.employment_status === 'terminated' || emp.employment_status === 'resigned' ? 'bg-neutral-100 text-neutral-400' : 'bg-neutral-200 text-neutral-600'}">
                  {statusLabels[emp.employment_status] ?? emp.employment_status}
                </span>
              </td>
              <td class="px-3 py-3.5">
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onclick={(e) => { e.stopPropagation(); openEdit(emp); }} class="rounded p-1 text-neutral-300 hover:text-neutral-700 transition-colors" title="Edit" aria-label="Edit">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" /></svg>
                  </button>
                  <button onclick={(e) => { e.stopPropagation(); deleteEmployee(emp); }} class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors" title="Delete" aria-label="Delete">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} employee{totalCount !== 1 ? 's' : ''}</span>
        <div class="flex items-center gap-1">
          <button onclick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&laquo;</button>
          {#each Array.from({ length: totalPages }, (_, i) => i + 1) as p}
            <button onclick={() => goToPage(p)} class="px-2.5 py-1 rounded text-sm {p === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}">{p}</button>
          {/each}
          <button onclick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&raquo;</button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Slide-over -->
{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">

      {#if drawerMode === "view" && viewingEmployee}
        <!-- VIEW MODE -->
        {@const emp = viewingEmployee}
        <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
          <div class="flex items-start justify-between">
            <div>
              <h2 class="text-lg font-semibold text-white">{emp.full_name}</h2>
              <p class="mt-0.5 text-sm text-neutral-400">{emp.job_title || emp.email}</p>
              <div class="mt-2 flex items-center gap-2">
                <span class="inline-flex items-center rounded-full {emp.employment_status === 'active' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-white/10 text-neutral-300'} px-2.5 py-0.5 text-[11px] font-medium">{statusLabels[emp.employment_status] ?? emp.employment_status}</span>
                {#if emp.department_name}<span class="inline-flex items-center rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-medium text-neutral-300">{emp.department_name}</span>{/if}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button onclick={() => openEdit(emp)} class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20">Edit</button>
              <button onclick={() => { showSlideOver = false; resetForm(); }} class="rounded-md p-1.5 text-neutral-400 hover:text-white" aria-label="Close">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <section>
            <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-3">Employee Details</h3>
            <div class="grid grid-cols-2 gap-3 rounded-xl border border-neutral-100 bg-neutral-50/50 p-4">
              <div><p class="text-[11px] text-neutral-500">Employee ID</p><p class="text-sm text-neutral-900">{emp.employee_id || "--"}</p></div>
              <div><p class="text-[11px] text-neutral-500">Position</p><p class="text-sm text-neutral-900">{emp.position_title || "--"}</p></div>
              <div><p class="text-[11px] text-neutral-500">Department</p><p class="text-sm text-neutral-900">{emp.department_name || "--"}</p></div>
              <div><p class="text-[11px] text-neutral-500">Hire Date</p><p class="text-sm text-neutral-900">{emp.hire_date || "--"}</p></div>
              <div><p class="text-[11px] text-neutral-500">Email</p><p class="text-sm text-neutral-900">{emp.email || "--"}</p></div>
              <div><p class="text-[11px] text-neutral-500">Phone</p><p class="text-sm text-neutral-900">{emp.phone_number || "--"}</p></div>
            </div>
          </section>
        </div>

      {:else}
        <!-- EDIT / CREATE MODE -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 bg-neutral-900">
        <h2 class="text-lg font-bold text-white">{isEditing ? "Edit Employee Record" : "Create Employee Record"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="emp-user" class="block text-sm font-medium text-neutral-700 mb-1">User <span class="text-red-500">*</span></label>
            <select id="emp-user" bind:value={form.user} class="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('user') ? 'border-red-400' : 'border-neutral-200'}">
              <option value="">Select user...</option>
              {#each userOptions as u (u.id)}
                <option value={String(u.id)}>{u.employee_id ? `${u.employee_id} — ` : ""}{u.full_name}</option>
              {/each}
            </select>
            {#if fieldError("user")}<p class="text-xs text-red-500 mt-1">{fieldError("user")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="emp-hire" class="block text-sm font-medium text-neutral-700 mb-1">Hire Date</label>
            <DateInput id="emp-hire" bind:value={form.hire_date} />
          </div>
          <div>
            <label for="emp-probation" class="block text-sm font-medium text-neutral-700 mb-1">Probation End</label>
            <DateInput id="emp-probation" bind:value={form.probation_end_date} />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="emp-cstart" class="block text-sm font-medium text-neutral-700 mb-1">Contract Start</label>
            <DateInput id="emp-cstart" bind:value={form.contract_start_date} />
          </div>
          <div>
            <label for="emp-cend" class="block text-sm font-medium text-neutral-700 mb-1">Contract End</label>
            <DateInput id="emp-cend" bind:value={form.contract_end_date} />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="emp-ctype" class="block text-sm font-medium text-neutral-700 mb-1">Contract Type</label>
            <input id="emp-ctype" type="text" bind:value={form.contract_type} placeholder="e.g. permanent" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="emp-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="emp-status" bind:value={form.employment_status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [val, label]}
                <option value={val}>{label}</option>
              {/each}
            </select>
          </div>
        </div>
        <div>
          <label for="emp-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="emp-notes" bind:value={form.notes} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillEmployee} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
      {/if}
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
