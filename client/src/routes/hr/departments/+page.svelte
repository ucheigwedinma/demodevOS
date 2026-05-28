<script lang="ts">
  import { api } from "$lib/api";
  import type { Division, PaginatedResponse } from "$lib/types";

  let divisions = $state<Division[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let expandedDepartmentIds = $state<Set<number>>(new Set());

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { include_departments: "true" };
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<Division>>("/settings/divisions/", params);
      divisions = res.results;
    } catch {
      divisions = [];
    } finally {
      loading = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchData, 300);
  }

  function isDepartmentExpanded(departmentId: number) {
    return expandedDepartmentIds.has(departmentId);
  }

  function toggleDepartmentExpansion(departmentId: number) {
    const next = new Set(expandedDepartmentIds);
    if (next.has(departmentId)) {
      next.delete(departmentId);
    } else {
      next.add(departmentId);
    }
    expandedDepartmentIds = next;
  }

  function getFillPercentage(division: Division["departments"][number]) {
    const approvedRoles = division.headcount_summary?.approved_roles ?? 0;
    const activeEmployees = division.headcount_summary?.active_employees ?? 0;
    if (approvedRoles <= 0) return 0;
    return Math.min(100, Math.round((activeEmployees / approvedRoles) * 100));
  }

  function getUtilizationBarWidth(department: Division["departments"][number]) {
    const utilization = department.utilization_rate?.percent ?? 0;
    return Math.max(0, Math.min(100, Math.round(utilization)));
  }

  function formatStatusLabel(value: string | null | undefined) {
    if (!value) return "Unknown";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function getProjectStatusClass(status: string | null | undefined) {
    switch (status) {
      case "in_progress":
        return "bg-blue-100 text-blue-700 border-blue-200";
      case "planning":
        return "bg-amber-100 text-amber-700 border-amber-200";
      case "on_hold":
        return "bg-rose-100 text-rose-700 border-rose-200";
      default:
        return "bg-neutral-100 text-neutral-600 border-neutral-200";
    }
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return "No date";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "No date";
    return parsed.toLocaleDateString();
  }

  $effect(() => {
    fetchData();
  });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Departments</h1>
      <p class="mt-1 text-sm text-neutral-500">Departments grouped by business unit</p>
    </div>
  </div>

  <section class="mb-6 rounded-xl border border-neutral-200 bg-white p-4">
    <h2 class="text-sm font-semibold text-neutral-900">Department Identity &amp; Ownership</h2>
    <p class="mt-1 text-xs text-neutral-500">
      Each department row provides identity, ownership hierarchy, and accounting linkage.
    </p>
  </section>

  <!-- Search -->
  <div class="mb-6">
    <div class="relative max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input
        type="text"
        placeholder="Search departments..."
        value={searchQuery}
        oninput={(e) => handleSearch(e.currentTarget.value)}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if divisions.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">No departments found</p>
    </div>
  {:else}
    <div class="space-y-6">
      {#each divisions as division}
        <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
          <div class="px-5 py-3.5 border-b border-neutral-100 bg-neutral-50/50">
            <div class="flex items-center gap-2">
              <h3 class="font-semibold text-neutral-900 text-sm">{division.name}</h3>
              <span class="text-xs font-mono text-neutral-400">{division.code}</span>
              {#if division.departments?.length}
                <span class="ml-auto text-xs text-neutral-400">{division.departments.length} department{division.departments.length !== 1 ? 's' : ''}</span>
              {/if}
            </div>
          </div>
          {#if division.departments?.length}
            <table class="w-full table-fixed text-sm">
              <colgroup>
                <col class="w-[36%]" />
                <col class="w-[18%]" />
                <col class="w-[22%]" />
                <col class="w-[14%]" />
                <col class="w-[10%]" />
              </colgroup>
              <thead>
                <tr class="border-b border-neutral-100">
                  <th class="text-left px-5 py-2.5 font-medium text-neutral-400 text-xs uppercase tracking-wider">Department Name</th>
                  <th class="text-left px-5 py-2.5 font-medium text-neutral-400 text-xs uppercase tracking-wider">Department Head</th>
                  <th class="text-left px-5 py-2.5 font-medium text-neutral-400 text-xs uppercase tracking-wider">Parent Business Unit</th>
                  <th class="text-left px-5 py-2.5 font-medium text-neutral-400 text-xs uppercase tracking-wider">Cost Center ID</th>
                  <th class="text-center px-5 py-2.5 font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-50">
                {#each division.departments as dept}
                  <tr class="hover:bg-neutral-50 transition-colors">
                    <td class="px-5 py-3">
                      <div class="flex flex-col gap-1.5 min-w-0">
                        <div class="flex items-center gap-2 min-w-0">
                          <span class="font-medium text-neutral-800 truncate">{dept.name}</span>
                          {#if dept.code}
                            <span class="text-xs font-mono text-neutral-400">{dept.code}</span>
                          {/if}
                        </div>
                        <div class="pt-2">
                          <button
                            type="button"
                            class="w-fit text-xs font-semibold text-neutral-600 hover:text-blue-700 active:text-blue-800 transition-colors"
                            onclick={() => toggleDepartmentExpansion(dept.id)}
                            aria-expanded={isDepartmentExpanded(dept.id)}
                          >
                            {isDepartmentExpanded(dept.id) ? "Hide summary" : "View summary"}
                          </button>
                        </div>
                      </div>
                    </td>
                    <td class="px-5 py-3 text-neutral-600">{dept.head_name ?? "\u2014"}</td>
                    <td class="px-5 py-3">
                      <span class="text-neutral-600">{dept.parent_business_unit_name ?? division.name}</span>
                    </td>
                    <td class="px-5 py-3">
                      <span class="font-mono text-xs text-neutral-600">{dept.cost_center_id ?? "\u2014"}</span>
                    </td>
                    <td class="px-5 py-3 text-center">
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {dept.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                        {dept.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                  {#if isDepartmentExpanded(dept.id)}
                    <tr class="bg-neutral-50/40">
                      <td colspan="5" class="px-5 py-4">
                        <div class="rounded-lg border border-neutral-200 bg-white p-4">
                          <div class="flex items-center justify-between gap-3">
                            <div>
                              <h4 class="text-sm font-semibold text-neutral-900">Talent &amp; Headcount Summary</h4>
                              <p class="mt-1 text-xs text-neutral-500">
                                Employee directory, fill-rate against approved roles, and top skills coverage.
                              </p>
                            </div>
                            <span class="text-xs font-medium text-neutral-600 rounded-full bg-neutral-100 px-2.5 py-1">
                              {dept.headcount_summary?.filled_vs_approved ?? "0/0"} roles filled
                            </span>
                          </div>

                          <div class="mt-4 grid gap-4 lg:grid-cols-12">
                            <section class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 lg:col-span-3">
                              <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Total Headcount</h5>
                              <p class="mt-2 text-xl font-semibold text-neutral-900">
                                {dept.headcount_summary?.filled_vs_approved ?? "0/0"}
                              </p>
                              <p class="mt-1 text-xs text-neutral-500">
                                Vacant roles: {dept.headcount_summary?.vacant_roles ?? 0}
                              </p>
                              <div class="mt-3 h-2 rounded-full bg-neutral-200 overflow-hidden">
                                <div
                                  class="h-2 rounded-full bg-emerald-500 transition-[width] duration-300"
                                  style={`width: ${getFillPercentage(dept)}%`}
                                ></div>
                              </div>
                            </section>

                            <section class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 lg:col-span-4">
                              <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Skills Matrix</h5>
                              {#if dept.skills_matrix?.length}
                                <div class="mt-2 flex flex-wrap gap-2">
                                  {#each dept.skills_matrix as skill}
                                    <span class="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">
                                      <span>{skill.skill_name}</span>
                                      <span class="text-sky-500">({skill.employee_count})</span>
                                    </span>
                                  {/each}
                                </div>
                              {:else}
                                <p class="mt-2 text-sm text-neutral-500">No skills mapped to this department yet.</p>
                              {/if}
                            </section>

                            <section class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 lg:col-span-5">
                              <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Employee Directory</h5>
                              {#if dept.employee_directory?.length}
                                <div class="mt-2 max-h-56 overflow-y-auto pr-1 grid gap-2 sm:grid-cols-2">
                                  {#each dept.employee_directory as employee}
                                    <article class="rounded-md border border-neutral-200 bg-white p-2.5">
                                      <p class="text-sm font-medium text-neutral-900">{employee.full_name}</p>
                                      <p class="mt-0.5 text-xs text-neutral-600">{employee.job_title || "Role not set"}</p>
                                      <p class="mt-1 text-[11px] font-mono text-neutral-500">
                                        {employee.employee_id || "EMP-\u2014"}
                                      </p>
                                      <a
                                        href={`mailto:${employee.email}`}
                                        class="mt-1 block text-[11px] text-neutral-500 hover:text-neutral-900 hover:underline underline-offset-2 transition-colors truncate"
                                      >
                                        {employee.email}
                                      </a>
                                    </article>
                                  {/each}
                                </div>
                              {:else}
                                <p class="mt-2 text-sm text-neutral-500">No employees currently assigned.</p>
                              {/if}
                            </section>
                          </div>

                          <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
                            <div class="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <h4 class="text-sm font-semibold text-neutral-900">Operational Integration</h4>
                                <p class="mt-1 text-xs text-neutral-500">
                                  Active project allocation, utilization load, and department SOP library.
                                </p>
                              </div>
                              <span class="text-xs font-medium text-neutral-600 rounded-full bg-white border border-neutral-200 px-2.5 py-1">
                                {dept.project_allocation?.length ?? 0} active project{(dept.project_allocation?.length ?? 0) === 1 ? "" : "s"}
                              </span>
                            </div>

                            <div class="mt-4 grid gap-4 lg:grid-cols-12">
                              <section class="rounded-lg border border-neutral-200 bg-white p-3 lg:col-span-5">
                                <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Project Allocation</h5>
                                {#if dept.project_allocation?.length}
                                  <div class="mt-2 space-y-2 max-h-56 overflow-y-auto pr-1">
                                    {#each dept.project_allocation as allocation}
                                      <article class="rounded-md border border-neutral-200 bg-neutral-50 p-2.5">
                                        <div class="flex items-center justify-between gap-2">
                                          <p class="text-sm font-medium text-neutral-900 truncate">{allocation.project_name}</p>
                                          <span class={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${getProjectStatusClass(allocation.project_status)}`}>
                                            {formatStatusLabel(allocation.project_status)}
                                          </span>
                                        </div>
                                        <div class="mt-1 grid grid-cols-3 gap-2 text-[11px] text-neutral-500">
                                          <span>{allocation.task_count} tasks</span>
                                          <span>{allocation.open_task_count} open</span>
                                          <span>{allocation.logged_hours} hrs</span>
                                        </div>
                                      </article>
                                    {/each}
                                  </div>
                                {:else}
                                  <p class="mt-2 text-sm text-neutral-500">No active project allocation yet.</p>
                                {/if}
                              </section>

                              <section class="rounded-lg border border-neutral-200 bg-white p-3 lg:col-span-3">
                                <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Utilization Rate</h5>
                                <p class="mt-2 text-2xl font-semibold text-neutral-900">
                                  {(dept.utilization_rate?.percent ?? 0).toFixed(1)}%
                                </p>
                                <p class="mt-1 text-xs text-neutral-500">{dept.utilization_rate?.period_label ?? "Current period"}</p>
                                <div class="mt-3 h-2 rounded-full bg-neutral-200 overflow-hidden">
                                  <div
                                    class="h-2 rounded-full bg-blue-500 transition-[width] duration-300"
                                    style={`width: ${getUtilizationBarWidth(dept)}%`}
                                  ></div>
                                </div>
                                <p class="mt-2 text-[11px] text-neutral-500">
                                  {(dept.utilization_rate?.hours_logged ?? 0).toFixed(1)}h /
                                  {(dept.utilization_rate?.available_hours ?? 0).toFixed(1)}h
                                </p>
                                <p class="mt-1 text-[11px] text-neutral-400">
                                  {dept.utilization_rate?.formula ?? "Total project-task effort hours / Total available staff hours"}
                                </p>
                              </section>

                              <section class="rounded-lg border border-neutral-200 bg-white p-3 lg:col-span-4">
                                <div class="flex items-center justify-between gap-2">
                                  <h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">SOP Library</h5>
                                  <span class="text-[11px] text-neutral-500">
                                    {dept.sop_library?.sop_count ?? 0} SOP / {dept.sop_library?.document_count ?? 0} docs
                                  </span>
                                </div>
                                {#if dept.sop_library?.documents?.length}
                                  <div class="mt-2 space-y-2 max-h-56 overflow-y-auto pr-1">
                                    {#each dept.sop_library.documents as document}
                                      <article class="rounded-md border border-neutral-200 bg-neutral-50 p-2.5">
                                        <div class="flex items-start justify-between gap-2">
                                          <p class="text-sm font-medium text-neutral-900 leading-tight">{document.title}</p>
                                          {#if document.is_sop}
                                            <span class="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                                              SOP
                                            </span>
                                          {/if}
                                        </div>
                                        <p class="mt-1 text-[11px] text-neutral-500 font-mono">{document.document_number || "DOC-\u2014"}</p>
                                        <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-neutral-500">
                                          <span>{formatStatusLabel(document.status)}</span>
                                          <span>{document.document_type_name || "Unclassified"}</span>
                                          <span>{formatDate(document.created_at)}</span>
                                        </div>
                                      </article>
                                    {/each}
                                  </div>
                                {:else}
                                  <p class="mt-2 text-sm text-neutral-500">
                                    No department documents mapped yet.
                                  </p>
                                {/if}
                              </section>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  {/if}
                {/each}
              </tbody>
            </table>
          {:else}
            <p class="px-5 py-4 text-sm text-neutral-400 italic">No departments in this division</p>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
