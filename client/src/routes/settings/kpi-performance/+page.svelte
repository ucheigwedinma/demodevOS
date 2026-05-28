<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { KpiDefinitionListItem, KpiDefinition, KpiAssignment, PaginatedResponse, RoleListItem, Department } from "$lib/types";

  type Tab = "library" | "assignments";

  let activeTab = $state<Tab>("library");
  let loading = $state(true);

  // KPI Library state
  let kpis = $state<KpiDefinitionListItem[]>([]);
  let showKpiForm = $state(false);
  let editingKpi = $state<KpiDefinition | null>(null);
  let savingKpi = $state(false);
  let kpiForm = $state<Record<string, unknown>>({});

  // Assignments state
  let assignments = $state<KpiAssignment[]>([]);
  let showAssignForm = $state(false);
  let editingAssign = $state<KpiAssignment | null>(null);
  let savingAssign = $state(false);
  let assignForm = $state<Record<string, unknown>>({});

  // Lookup data
  let roles = $state<RoleListItem[]>([]);
  let departments = $state<Department[]>([]);

  function resetKpiForm() {
    kpiForm = {
      name: "",
      code: "",
      description: "",
      category: "construction",
      unit: "percentage",
      direction: "higher_is_better",
      frequency: "monthly",
      formula_expression: "",
      data_source: "",
      green_threshold: "",
      amber_threshold: "",
      bonus_green_pct: "",
      bonus_amber_pct: "",
      bonus_red_pct: "",
      is_active: true,
      sort_order: 0,
    };
  }

  function resetAssignForm() {
    assignForm = {
      kpi: "",
      role: "",
      department: "",
      target_value: "",
      weight: "100",
      is_active: true,
    };
  }

  async function loadKpis() {
    try {
      const data = await api.get<PaginatedResponse<KpiDefinitionListItem>>("/settings/kpi-definitions/");
      kpis = data.results;
    } catch {
      toast.error("Load failed", "Could not load KPI definitions.");
    }
  }

  async function loadAssignments() {
    try {
      const data = await api.get<PaginatedResponse<KpiAssignment>>("/settings/kpi-assignments/");
      assignments = data.results;
    } catch {
      toast.error("Load failed", "Could not load KPI assignments.");
    }
  }

  async function loadLookups() {
    try {
      const [roleData, deptData] = await Promise.all([
        api.get<PaginatedResponse<RoleListItem>>("/settings/roles/"),
        api.get<Department[]>("/settings/divisions/"),
      ]);
      roles = roleData.results;
      // Flatten departments from divisions
      const allDepts: Department[] = [];
      if (Array.isArray(deptData)) {
        for (const div of deptData as Array<{ departments?: Department[] }>) {
          if (div.departments) allDepts.push(...div.departments);
        }
      }
      departments = allDepts;
    } catch {
      // Non-critical — form dropdowns will be empty
    }
  }

  async function loadAll() {
    loading = true;
    await Promise.all([loadKpis(), loadAssignments(), loadLookups()]);
    loading = false;
  }

  async function handleSaveKpi() {
    savingKpi = true;
    try {
      const payload = { ...kpiForm };
      // Clean empty optional bonus fields
      for (const key of ["bonus_green_pct", "bonus_amber_pct", "bonus_red_pct"]) {
        if (payload[key] === "" || payload[key] === null) payload[key] = null;
      }
      if (editingKpi) {
        await api.patch(`/settings/kpi-definitions/${editingKpi.id}/`, payload);
        toast.success("Updated", "KPI definition updated.");
      } else {
        await api.post("/settings/kpi-definitions/", payload);
        toast.success("Created", "KPI definition created.");
      }
      showKpiForm = false;
      editingKpi = null;
      await loadKpis();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      savingKpi = false;
    }
  }

  async function handleDeleteKpi(kpi: KpiDefinitionListItem) {
    if (!confirm(`Delete KPI "${kpi.name}"?`)) return;
    try {
      await api.delete(`/settings/kpi-definitions/${kpi.id}/`);
      toast.success("Deleted", `KPI "${kpi.name}" removed.`);
      await loadKpis();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Delete failed", messages[0] || "Could not delete KPI.");
      } else {
        toast.error("Delete failed", "An unexpected error occurred.");
      }
    }
  }

  async function startEditKpi(kpi: KpiDefinitionListItem) {
    try {
      const detail = await api.get<KpiDefinition>(`/settings/kpi-definitions/${kpi.id}/`);
      editingKpi = detail;
      kpiForm = {
        name: detail.name,
        code: detail.code,
        description: detail.description,
        category: detail.category,
        unit: detail.unit,
        direction: detail.direction,
        frequency: detail.frequency,
        formula_expression: detail.formula_expression,
        data_source: detail.data_source,
        green_threshold: detail.green_threshold,
        amber_threshold: detail.amber_threshold,
        bonus_green_pct: detail.bonus_green_pct ?? "",
        bonus_amber_pct: detail.bonus_amber_pct ?? "",
        bonus_red_pct: detail.bonus_red_pct ?? "",
        is_active: detail.is_active,
        sort_order: detail.sort_order,
      };
      showKpiForm = true;
    } catch {
      toast.error("Load failed", "Could not load KPI details.");
    }
  }

  async function handleSaveAssign() {
    savingAssign = true;
    try {
      const payload = { ...assignForm };
      if (!payload.role) payload.role = null;
      if (!payload.department) payload.department = null;
      if (editingAssign) {
        await api.patch(`/settings/kpi-assignments/${editingAssign.id}/`, payload);
        toast.success("Updated", "KPI assignment updated.");
      } else {
        await api.post("/settings/kpi-assignments/", payload);
        toast.success("Created", "KPI assignment created.");
      }
      showAssignForm = false;
      editingAssign = null;
      await loadAssignments();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      savingAssign = false;
    }
  }

  async function handleDeleteAssign(assign: KpiAssignment) {
    if (!confirm(`Remove assignment for "${assign.kpi_name}"?`)) return;
    try {
      await api.delete(`/settings/kpi-assignments/${assign.id}/`);
      toast.success("Deleted", "KPI assignment removed.");
      await loadAssignments();
    } catch {
      toast.error("Delete failed", "Could not delete assignment.");
    }
  }

  function startEditAssign(assign: KpiAssignment) {
    editingAssign = assign;
    assignForm = {
      kpi: assign.kpi,
      role: assign.role ?? "",
      department: assign.department ?? "",
      target_value: assign.target_value,
      weight: assign.weight,
      is_active: assign.is_active,
    };
    showAssignForm = true;
  }

  function ragColor(kpi: KpiDefinitionListItem): string {
    if (kpi.direction === "higher_is_better") {
      return "Green ≥ " + kpi.green_threshold + ", Amber ≥ " + kpi.amber_threshold;
    }
    return "Green ≤ " + kpi.green_threshold + ", Amber ≤ " + kpi.amber_threshold;
  }

  $effect(() => {
    loadAll();
  });

  const categories = [
    { value: "construction", label: "Construction" },
    { value: "sales", label: "Sales" },
    { value: "finance", label: "Finance" },
    { value: "operations", label: "Operations" },
    { value: "compliance", label: "Compliance" },
    { value: "hr", label: "Human Resources" },
    { value: "procurement", label: "Procurement" },
    { value: "project_management", label: "Project Management" },
    { value: "property", label: "Property" },
    { value: "safety", label: "Safety" },
    { value: "quality", label: "Quality" },
  ];

  const units = [
    { value: "percentage", label: "Percentage (%)" },
    { value: "currency", label: "Currency" },
    { value: "count", label: "Count" },
    { value: "ratio", label: "Ratio" },
    { value: "days", label: "Days" },
    { value: "score", label: "Score (0–100)" },
  ];

  const frequencies = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "annual", label: "Annual" },
  ];

  const inputClass = "w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow";
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">KPI & Performance Configuration</h2>
      <p class="mt-1 text-sm text-neutral-500">Define KPIs, configure RAG thresholds, assign to roles and departments, and manage bonus linkage rules.</p>
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 mb-6 border-b border-neutral-200">
    <button
      onclick={() => { activeTab = "library"; }}
      class="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px
             {activeTab === 'library' ? 'border-neutral-800 text-neutral-800' : 'border-transparent text-neutral-500 hover:text-neutral-700'}"
    >
      KPI Library ({kpis.length})
    </button>
    <button
      onclick={() => { activeTab = "assignments"; }}
      class="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px
             {activeTab === 'assignments' ? 'border-neutral-800 text-neutral-800' : 'border-transparent text-neutral-500 hover:text-neutral-700'}"
    >
      Assignments ({assignments.length})
    </button>
  </div>

  <!-- KPI Library Tab -->
  {#if activeTab === "library"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button
          onclick={() => { resetKpiForm(); editingKpi = null; showKpiForm = true; }}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
        >
          + Add KPI
        </button>
      </div>

      {#if showKpiForm}
        <section class="rounded-xl border border-neutral-200 bg-white p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-5">{editingKpi ? "Edit KPI" : "New KPI Definition"}</h3>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label for="kpi_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name</label>
              <input id="kpi_name" type="text" bind:value={kpiForm.name} placeholder="Cost Variance %" class={inputClass} />
            </div>
            <div>
              <label for="kpi_code" class="block text-sm font-medium text-neutral-700 mb-1.5">Code</label>
              <input id="kpi_code" type="text" bind:value={kpiForm.code} placeholder="COST_VARIANCE_PCT" class={inputClass} />
              <p class="text-xs text-neutral-400 mt-1">Uppercase letters, digits, underscores.</p>
            </div>
            <div>
              <label for="kpi_cat" class="block text-sm font-medium text-neutral-700 mb-1.5">Category</label>
              <select id="kpi_cat" bind:value={kpiForm.category} class={inputClass}>
                {#each categories as cat}
                  <option value={cat.value}>{cat.label}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="kpi_unit" class="block text-sm font-medium text-neutral-700 mb-1.5">Unit</label>
              <select id="kpi_unit" bind:value={kpiForm.unit} class={inputClass}>
                {#each units as u}
                  <option value={u.value}>{u.label}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="kpi_dir" class="block text-sm font-medium text-neutral-700 mb-1.5">Direction</label>
              <select id="kpi_dir" bind:value={kpiForm.direction} class={inputClass}>
                <option value="higher_is_better">Higher is Better</option>
                <option value="lower_is_better">Lower is Better</option>
              </select>
            </div>
            <div>
              <label for="kpi_freq" class="block text-sm font-medium text-neutral-700 mb-1.5">Frequency</label>
              <select id="kpi_freq" bind:value={kpiForm.frequency} class={inputClass}>
                {#each frequencies as f}
                  <option value={f.value}>{f.label}</option>
                {/each}
              </select>
            </div>
          </div>

          <div class="mt-4">
            <label for="kpi_desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
            <textarea id="kpi_desc" bind:value={kpiForm.description} rows="2" placeholder="What this KPI measures..." class={inputClass}></textarea>
          </div>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-4">
            <div>
              <label for="kpi_formula" class="block text-sm font-medium text-neutral-700 mb-1.5">Formula Expression</label>
              <input id="kpi_formula" type="text" bind:value={kpiForm.formula_expression} placeholder="(Budget - Actual) / Budget × 100" class={inputClass} />
            </div>
            <div>
              <label for="kpi_source" class="block text-sm font-medium text-neutral-700 mb-1.5">Data Source</label>
              <input id="kpi_source" type="text" bind:value={kpiForm.data_source} placeholder="Project cost entries" class={inputClass} />
            </div>
          </div>

          <!-- RAG Thresholds -->
          <div class="mt-5 pt-5 border-t border-neutral-100">
            <h4 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">RAG Thresholds</h4>
            <div class="rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3 mb-4">
              <p class="text-xs text-neutral-500">
                {#if kpiForm.direction === "higher_is_better"}
                  <span class="font-semibold text-neutral-600">Higher is better:</span> Value ≥ green threshold → <span class="text-emerald-600 font-semibold">Green</span>, ≥ amber → <span class="text-amber-600 font-semibold">Amber</span>, below → <span class="text-red-600 font-semibold">Red</span>
                {:else}
                  <span class="font-semibold text-neutral-600">Lower is better:</span> Value ≤ green threshold → <span class="text-emerald-600 font-semibold">Green</span>, ≤ amber → <span class="text-amber-600 font-semibold">Amber</span>, above → <span class="text-red-600 font-semibold">Red</span>
                {/if}
              </p>
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label for="green_thresh" class="block text-sm font-medium text-emerald-700 mb-1.5">Green Threshold</label>
                <input id="green_thresh" type="number" step="0.01" bind:value={kpiForm.green_threshold} class={inputClass} />
              </div>
              <div>
                <label for="amber_thresh" class="block text-sm font-medium text-amber-700 mb-1.5">Amber Threshold</label>
                <input id="amber_thresh" type="number" step="0.01" bind:value={kpiForm.amber_threshold} class={inputClass} />
              </div>
            </div>
          </div>

          <!-- Bonus Linkage -->
          <div class="mt-5 pt-5 border-t border-neutral-100">
            <h4 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Bonus Linkage (Optional)</h4>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label for="bonus_green" class="block text-sm font-medium text-emerald-700 mb-1.5">Green Bonus (%)</label>
                <input id="bonus_green" type="number" step="0.01" bind:value={kpiForm.bonus_green_pct} placeholder="e.g. 15" class={inputClass} />
              </div>
              <div>
                <label for="bonus_amber" class="block text-sm font-medium text-amber-700 mb-1.5">Amber Bonus (%)</label>
                <input id="bonus_amber" type="number" step="0.01" bind:value={kpiForm.bonus_amber_pct} placeholder="e.g. 5" class={inputClass} />
              </div>
              <div>
                <label for="bonus_red" class="block text-sm font-medium text-red-700 mb-1.5">Red Bonus (%)</label>
                <input id="bonus_red" type="number" step="0.01" bind:value={kpiForm.bonus_red_pct} placeholder="e.g. 0" class={inputClass} />
              </div>
            </div>
          </div>

          <div class="flex items-center gap-3 mt-6 pt-4 border-t border-neutral-100">
            <button
              onclick={handleSaveKpi}
              disabled={savingKpi}
              class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 transition-colors"
            >
              {savingKpi ? "Saving..." : editingKpi ? "Update KPI" : "Create KPI"}
            </button>
            <button
              onclick={() => { showKpiForm = false; editingKpi = null; }}
              class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </section>
      {/if}

      <!-- KPI Table -->
      {#if kpis.length > 0}
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Code</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Name</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Category</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Unit</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">RAG Logic</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Frequency</th>
                  <th class="text-center font-medium text-neutral-500 px-4 py-3">Assignments</th>
                  <th class="text-right font-medium text-neutral-500 px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {#each kpis as kpi}
                  <tr class="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td class="px-4 py-3 font-mono text-xs text-neutral-600">{kpi.code}</td>
                    <td class="px-4 py-3">
                      <div class="flex items-center gap-2">
                        <span class="font-medium text-neutral-800">{kpi.name}</span>
                        {#if !kpi.is_active}
                          <span class="inline-flex items-center rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500">Inactive</span>
                        {/if}
                        {#if kpi.is_system}
                          <span class="inline-flex items-center rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">System</span>
                        {/if}
                      </div>
                    </td>
                    <td class="px-4 py-3 text-neutral-600">{kpi.category_display}</td>
                    <td class="px-4 py-3 text-neutral-600">{kpi.unit_display}</td>
                    <td class="px-4 py-3">
                      <div class="flex items-center gap-1.5">
                        <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span class="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
                        <span class="inline-block w-2 h-2 rounded-full bg-red-500"></span>
                        <span class="text-xs text-neutral-500 ml-1">{ragColor(kpi)}</span>
                      </div>
                    </td>
                    <td class="px-4 py-3 text-neutral-600">{kpi.frequency_display}</td>
                    <td class="px-4 py-3 text-center text-neutral-600">{kpi.assignment_count}</td>
                    <td class="px-4 py-3 text-right">
                      <div class="flex items-center justify-end gap-2">
                        <button
                          onclick={() => startEditKpi(kpi)}
                          class="text-xs font-medium text-neutral-500 hover:text-neutral-800 transition-colors"
                        >
                          Edit
                        </button>
                        {#if !kpi.is_system}
                          <button
                            onclick={() => handleDeleteKpi(kpi)}
                            class="text-xs font-medium text-red-500 hover:text-red-700 transition-colors"
                          >
                            Delete
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else if !showKpiForm}
        <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
          <svg class="mx-auto h-8 w-8 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
          </svg>
          <p class="mt-2 text-sm text-neutral-400">No KPIs defined yet.</p>
          <p class="text-xs text-neutral-400 mt-1">Start building your KPI library by clicking "Add KPI" above.</p>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Assignments Tab -->
  {#if activeTab === "assignments"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button
          onclick={() => { resetAssignForm(); editingAssign = null; showAssignForm = true; }}
          disabled={kpis.length === 0}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 transition-colors"
        >
          + Assign KPI
        </button>
      </div>

      {#if showAssignForm}
        <section class="rounded-xl border border-neutral-200 bg-white p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-5">{editingAssign ? "Edit Assignment" : "New KPI Assignment"}</h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label for="assign_kpi" class="block text-sm font-medium text-neutral-700 mb-1.5">KPI</label>
              <select id="assign_kpi" bind:value={assignForm.kpi} class={inputClass}>
                <option value="">Select KPI...</option>
                {#each kpis.filter(k => k.is_active) as k}
                  <option value={k.id}>{k.code} — {k.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="assign_target" class="block text-sm font-medium text-neutral-700 mb-1.5">Target Value</label>
              <input id="assign_target" type="number" step="0.01" bind:value={assignForm.target_value} placeholder="e.g. 95" class={inputClass} />
            </div>
            <div>
              <label for="assign_role" class="block text-sm font-medium text-neutral-700 mb-1.5">Role (optional)</label>
              <select id="assign_role" bind:value={assignForm.role} class={inputClass}>
                <option value="">No role</option>
                {#each roles as r}
                  <option value={r.id}>{r.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="assign_dept" class="block text-sm font-medium text-neutral-700 mb-1.5">Department (optional)</label>
              <select id="assign_dept" bind:value={assignForm.department} class={inputClass}>
                <option value="">No department</option>
                {#each departments as d}
                  <option value={d.id}>{d.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="assign_weight" class="block text-sm font-medium text-neutral-700 mb-1.5">Weight (0–100)</label>
              <input id="assign_weight" type="number" min="0" max="100" step="0.01" bind:value={assignForm.weight} class={inputClass} />
            </div>
            <div class="flex items-end">
              <div class="flex items-center justify-between w-full py-2.5">
                <span class="text-sm font-medium text-neutral-700">Active</span>
                <button
                  type="button"
                  onclick={() => { assignForm.is_active = !assignForm.is_active; }}
                  class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                         {assignForm.is_active ? 'bg-neutral-800' : 'bg-neutral-200'}"
                  role="switch"
                  aria-checked={assignForm.is_active as boolean}
                  aria-label="Toggle active"
                >
                  <span
                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                           {assignForm.is_active ? 'translate-x-5' : 'translate-x-0.5'}"
                    style="margin-top: 2px;"
                  ></span>
                </button>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-6 pt-4 border-t border-neutral-100">
            <button
              onclick={handleSaveAssign}
              disabled={savingAssign}
              class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 transition-colors"
            >
              {savingAssign ? "Saving..." : editingAssign ? "Update Assignment" : "Create Assignment"}
            </button>
            <button
              onclick={() => { showAssignForm = false; editingAssign = null; }}
              class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </section>
      {/if}

      {#if assignments.length > 0}
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">KPI</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Category</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Role</th>
                  <th class="text-left font-medium text-neutral-500 px-4 py-3">Department</th>
                  <th class="text-right font-medium text-neutral-500 px-4 py-3">Target</th>
                  <th class="text-right font-medium text-neutral-500 px-4 py-3">Weight</th>
                  <th class="text-right font-medium text-neutral-500 px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {#each assignments as assign}
                  <tr class="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td class="px-4 py-3">
                      <div>
                        <p class="font-medium text-neutral-800">{assign.kpi_name}</p>
                        <p class="text-xs text-neutral-400 font-mono">{assign.kpi_code}</p>
                      </div>
                    </td>
                    <td class="px-4 py-3 text-neutral-600">{assign.kpi_category_display}</td>
                    <td class="px-4 py-3 text-neutral-600">{assign.role_name || "—"}</td>
                    <td class="px-4 py-3 text-neutral-600">{assign.department_name || "—"}</td>
                    <td class="px-4 py-3 text-right text-neutral-700 font-medium">{assign.target_value} <span class="text-neutral-400 font-normal text-xs">{assign.kpi_unit_display}</span></td>
                    <td class="px-4 py-3 text-right text-neutral-600">{assign.weight}%</td>
                    <td class="px-4 py-3 text-right">
                      <div class="flex items-center justify-end gap-2">
                        <button
                          onclick={() => startEditAssign(assign)}
                          class="text-xs font-medium text-neutral-500 hover:text-neutral-800 transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onclick={() => handleDeleteAssign(assign)}
                          class="text-xs font-medium text-red-500 hover:text-red-700 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else if !showAssignForm}
        <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
          <svg class="mx-auto h-8 w-8 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
          <p class="mt-2 text-sm text-neutral-400">No KPI assignments yet.</p>
          <p class="text-xs text-neutral-400 mt-1">{kpis.length === 0 ? "Define KPIs in the library first, then assign them here." : "Assign KPIs to roles and departments by clicking \"Assign KPI\" above."}</p>
        </div>
      {/if}
    </div>
  {/if}
{/if}
