<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { DivisionListItem, Division, Department, CostCenter, ProfitCenter, PaginatedResponse } from "$lib/types";

  let activeTab = $state<"divisions" | "cost-centers" | "profit-centers">("divisions");

  // --- Divisions ---
  let divisionsLoading = $state(true);
  let divisions = $state<DivisionListItem[]>([]);
  let expandedDivision = $state<number | null>(null);
  let divisionDetail = $state<Division | null>(null);
  let showDivisionModal = $state(false);
  let editingDivisionId = $state<number | null>(null);
  let divisionForm = $state({ name: "", code: "", description: "", is_active: true, sort_order: 0 });
  let savingDivision = $state(false);

  // --- Departments ---
  let showDeptModal = $state(false);
  let editingDeptId = $state<number | null>(null);
  let deptParentDivisionId = $state<number | null>(null);
  let deptForm = $state({ name: "", code: "", cost_center_id: "", description: "", is_active: true, sort_order: 0 });
  let savingDept = $state(false);

  // --- Cost Centers ---
  let costCentersLoading = $state(true);
  let costCenters = $state<CostCenter[]>([]);
  let costCenterDepartmentOptions = $state<Department[]>([]);
  let showCCModal = $state(false);
  let editingCCId = $state<number | null>(null);
  let ccForm = $state({ code: "", name: "", department: null as number | null, is_active: true });
  let savingCC = $state(false);

  // --- Profit Centers ---
  let profitCentersLoading = $state(true);
  let profitCenters = $state<ProfitCenter[]>([]);
  let showPCModal = $state(false);
  let editingPCId = $state<number | null>(null);
  let pcForm = $state({ code: "", name: "", department: null as number | null, is_active: true });
  let savingPC = $state(false);

  // ======================== DIVISIONS ========================

  async function loadDivisions() {
    try {
      const res = await api.get<PaginatedResponse<DivisionListItem>>("/settings/divisions/");
      divisions = res.results;
    } catch {
      toast.error("Load failed", "Could not load divisions.");
    } finally {
      divisionsLoading = false;
    }
  }

  async function toggleDivision(id: number) {
    if (expandedDivision === id) {
      expandedDivision = null;
      divisionDetail = null;
      return;
    }
    try {
      divisionDetail = await api.get<Division>(`/settings/divisions/${id}/`);
      expandedDivision = id;
    } catch {
      toast.error("Error", "Could not load division details.");
    }
  }

  function openAddDivision() {
    editingDivisionId = null;
    divisionForm = { name: "", code: "", description: "", is_active: true, sort_order: 0 };
    showDivisionModal = true;
  }

  async function openEditDivision(div: DivisionListItem) {
    editingDivisionId = div.id;
    divisionForm = { name: div.name, code: div.code, is_active: div.is_active, description: "", sort_order: div.sort_order };
    showDivisionModal = true;
  }

  async function saveDivision() {
    if (!divisionForm.name.trim()) { toast.error("Validation", "Name is required."); return; }
    savingDivision = true;
    try {
      if (editingDivisionId) {
        await api.patch(`/settings/divisions/${editingDivisionId}/`, divisionForm);
        toast.success("Updated", "Division updated.");
      } else {
        await api.post("/settings/divisions/", divisionForm);
        toast.success("Created", "Division created.");
      }
      showDivisionModal = false;
      await loadDivisions();
    } catch { toast.error("Save failed", "Please check the form."); }
    finally { savingDivision = false; }
  }

  async function deleteDivision(id: number) {
    try {
      await api.delete(`/settings/divisions/${id}/`);
      toast.success("Deleted", "Division removed.");
      if (expandedDivision === id) { expandedDivision = null; divisionDetail = null; }
      await loadDivisions();
    } catch { toast.error("Delete failed", "Could not delete division."); }
  }

  // ======================== DEPARTMENTS ========================

  function openAddDept(divisionId: number) {
    deptParentDivisionId = divisionId;
    editingDeptId = null;
    deptForm = { name: "", code: "", cost_center_id: "", description: "", is_active: true, sort_order: 0 };
    showDeptModal = true;
  }

  function openEditDept(dept: Department, divisionId: number) {
    deptParentDivisionId = divisionId;
    editingDeptId = dept.id;
    deptForm = {
      name: dept.name,
      code: dept.code,
      cost_center_id: dept.cost_center_id ?? "",
      description: dept.description,
      is_active: dept.is_active,
      sort_order: dept.sort_order,
    };
    showDeptModal = true;
  }

  async function saveDept() {
    if (!deptForm.name.trim() || !deptParentDivisionId) {
      toast.error("Validation", "Name is required.");
      return;
    }
    if (!deptForm.cost_center_id.trim()) {
      toast.error("Validation", "Cost Center ID is required.");
      return;
    }

    const payload = {
      ...deptForm,
      cost_center_id: deptForm.cost_center_id.trim().toUpperCase(),
    };

    savingDept = true;
    try {
      if (editingDeptId) {
        await api.patch(`/settings/divisions/${deptParentDivisionId}/departments/${editingDeptId}/`, payload);
        toast.success("Updated", "Department updated.");
      } else {
        await api.post(`/settings/divisions/${deptParentDivisionId}/departments/`, payload);
        toast.success("Created", "Department created.");
      }
      showDeptModal = false;
      divisionDetail = await api.get<Division>(`/settings/divisions/${deptParentDivisionId}/`);
      await loadDivisions();
    } catch { toast.error("Save failed", "Please check the form."); }
    finally { savingDept = false; }
  }

  async function deleteDept(divisionId: number, deptId: number) {
    try {
      await api.delete(`/settings/divisions/${divisionId}/departments/${deptId}/`);
      toast.success("Deleted", "Department removed.");
      divisionDetail = await api.get<Division>(`/settings/divisions/${divisionId}/`);
      await loadDivisions();
    } catch { toast.error("Delete failed", "Could not delete department."); }
  }

  // ======================== COST CENTERS ========================

  async function loadCostCenters() {
    try {
      const res = await api.get<PaginatedResponse<CostCenter>>("/settings/cost-centers/");
      costCenters = res.results;
    } catch {
      toast.error("Load failed", "Could not load cost centers.");
    } finally {
      costCentersLoading = false;
    }
  }

  async function loadCostCenterDepartmentOptions() {
    try {
      const res = await api.get<PaginatedResponse<Department>>("/settings/departments/", {
        page_size: "500",
        ordering: "name",
      });
      costCenterDepartmentOptions = res.results;
    } catch {
      costCenterDepartmentOptions = [];
    }
  }

  async function openAddCC() {
    editingCCId = null;
    ccForm = { code: "", name: "", department: null, is_active: true };
    await loadCostCenterDepartmentOptions();
    showCCModal = true;
  }

  async function openEditCC(cc: CostCenter) {
    editingCCId = cc.id;
    ccForm = { code: cc.code, name: cc.name, department: cc.department, is_active: cc.is_active };
    await loadCostCenterDepartmentOptions();
    showCCModal = true;
  }

  async function saveCC() {
    if (!ccForm.code.trim() || !ccForm.name.trim()) { toast.error("Validation", "Code and name are required."); return; }
    savingCC = true;
    try {
      if (editingCCId) {
        await api.patch(`/settings/cost-centers/${editingCCId}/`, ccForm);
        toast.success("Updated", "Cost center updated.");
      } else {
        await api.post("/settings/cost-centers/", ccForm);
        toast.success("Created", "Cost center created.");
      }
      showCCModal = false;
      await loadCostCenters();
    } catch { toast.error("Save failed", "Please check the form."); }
    finally { savingCC = false; }
  }

  async function deleteCC(id: number) {
    try {
      await api.delete(`/settings/cost-centers/${id}/`);
      toast.success("Deleted", "Cost center removed.");
      await loadCostCenters();
    } catch { toast.error("Delete failed", "Could not delete cost center."); }
  }

  // ======================== PROFIT CENTERS ========================

  async function loadProfitCenters() {
    try {
      const res = await api.get<PaginatedResponse<ProfitCenter>>("/settings/profit-centers/");
      profitCenters = res.results;
    } catch {
      toast.error("Load failed", "Could not load profit centers.");
    } finally {
      profitCentersLoading = false;
    }
  }

  async function openAddPC() {
    editingPCId = null;
    pcForm = { code: "", name: "", department: null, is_active: true };
    await loadCostCenterDepartmentOptions();
    showPCModal = true;
  }

  async function openEditPC(pc: ProfitCenter) {
    editingPCId = pc.id;
    pcForm = { code: pc.code, name: pc.name, department: pc.department, is_active: pc.is_active };
    await loadCostCenterDepartmentOptions();
    showPCModal = true;
  }

  async function savePC() {
    if (!pcForm.code.trim() || !pcForm.name.trim()) { toast.error("Validation", "Code and name are required."); return; }
    savingPC = true;
    try {
      if (editingPCId) {
        await api.patch(`/settings/profit-centers/${editingPCId}/`, pcForm);
        toast.success("Updated", "Profit center updated.");
      } else {
        await api.post("/settings/profit-centers/", pcForm);
        toast.success("Created", "Profit center created.");
      }
      showPCModal = false;
      await loadProfitCenters();
    } catch { toast.error("Save failed", "Please check the form."); }
    finally { savingPC = false; }
  }

  async function deletePC(id: number) {
    try {
      await api.delete(`/settings/profit-centers/${id}/`);
      toast.success("Deleted", "Profit center removed.");
      await loadProfitCenters();
    } catch { toast.error("Delete failed", "Could not delete profit center."); }
  }

  // ── Dev fill ──
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const DIVISION_SAMPLES = [
    {
      name: "Construction & Engineering",
      code: "CON",
      description: "Oversees all on-site construction activities, structural engineering, MEP installations, and quality assurance across active project sites.",
      is_active: true,
      sort_order: 1,
    },
    {
      name: "Sales & Marketing",
      code: "S&M",
      description: "Manages off-plan sales, broker relations, marketing campaigns, show-unit fit-outs, and customer journey from inquiry to handover.",
      is_active: true,
      sort_order: 2,
    },
    {
      name: "Finance & Administration",
      code: "FIN",
      description: "Handles corporate finance, project accounting, treasury, accounts payable/receivable, payroll, and regulatory filings across all SPVs.",
      is_active: true,
      sort_order: 3,
    },
  ];

  const DEPARTMENT_SAMPLES = [
    {
      name: "Structural Engineering",
      code: "STR-ENG",
      cost_center_id: "CC-STR-001",
      description: "Responsible for structural design review, RFI management, rebar inspection, concrete pour scheduling, and load testing across all project phases.",
      is_active: true,
      sort_order: 1,
    },
    {
      name: "Procurement & Supply Chain",
      code: "PROC",
      cost_center_id: "CC-PROC-001",
      description: "Manages vendor prequalification, purchase orders, material delivery scheduling, warehouse operations, and supplier performance evaluation.",
      is_active: true,
      sort_order: 2,
    },
    {
      name: "Human Resources",
      code: "HR",
      cost_center_id: "CC-HR-001",
      description: "Handles recruitment, onboarding, employee relations, performance reviews, training programs, and labour camp administration for site workers.",
      is_active: true,
      sort_order: 3,
    },
  ];

  const COST_CENTER_SAMPLES = [
    {
      code: "CC-CON-01",
      name: "Site Construction — Direct Costs",
      department: null as number | null,
      is_active: true,
    },
    {
      code: "CC-MKT-01",
      name: "Marketing & Sales Operations",
      department: null as number | null,
      is_active: true,
    },
    {
      code: "CC-ADM-01",
      name: "General & Administrative",
      department: null as number | null,
      is_active: true,
    },
  ];

  const PROFIT_CENTER_SAMPLES = [
    {
      code: "PC-RES-01",
      name: "Residential Sales Revenue",
      department: null as number | null,
      is_active: true,
    },
    {
      code: "PC-COM-01",
      name: "Commercial Leasing Income",
      department: null as number | null,
      is_active: true,
    },
    {
      code: "PC-PM-01",
      name: "Project Management Fees",
      department: null as number | null,
      is_active: true,
    },
  ];

  let divDevIdx = 0;
  let deptDevIdx = 0;
  let ccDevIdx = 0;
  let pcDevIdx = 0;

  function devFillDivision() {
    const sample = DIVISION_SAMPLES[divDevIdx % DIVISION_SAMPLES.length];
    divDevIdx++;
    divisionForm = { ...sample };
  }

  function devFillDept() {
    const sample = DEPARTMENT_SAMPLES[deptDevIdx % DEPARTMENT_SAMPLES.length];
    deptDevIdx++;
    deptForm = { ...sample };
  }

  function devFillCC() {
    const sample = COST_CENTER_SAMPLES[ccDevIdx % COST_CENTER_SAMPLES.length];
    ccDevIdx++;
    ccForm = {
      ...sample,
      department: costCenterDepartmentOptions.length
        ? costCenterDepartmentOptions[ccDevIdx % costCenterDepartmentOptions.length].id
        : null,
    };
  }

  function devFillPC() {
    const sample = PROFIT_CENTER_SAMPLES[pcDevIdx % PROFIT_CENTER_SAMPLES.length];
    pcDevIdx++;
    pcForm = {
      ...sample,
      department: costCenterDepartmentOptions.length
        ? costCenterDepartmentOptions[pcDevIdx % costCenterDepartmentOptions.length].id
        : null,
    };
  }

  // ======================== INIT ========================

  $effect(() => {
    loadDivisions();
    loadCostCenters();
    loadCostCenterDepartmentOptions();
    loadProfitCenters();
  });
</script>

<!-- Header -->
<div class="mb-8">
  <h2 class="text-xl font-bold text-neutral-800">Organizational Hierarchy</h2>
  <p class="mt-1 text-sm text-neutral-500">Manage divisions, departments, cost centers, and profit centers.</p>
</div>

<!-- Tabs -->
<div class="flex items-center gap-1 border-b border-neutral-200 mb-8">
  {#each [
    { key: "divisions", label: "Divisions & Departments" },
    { key: "cost-centers", label: "Cost Centers" },
    { key: "profit-centers", label: "Profit Centers" },
  ] as tab}
    <button
      onclick={() => (activeTab = tab.key as typeof activeTab)}
      class="px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px
             {activeTab === tab.key
               ? 'border-neutral-800 text-neutral-800'
               : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
    >
      {tab.label}
    </button>
  {/each}
</div>

<!-- TAB: Divisions & Departments -->
{#if activeTab === "divisions"}
  <div class="flex items-center justify-between mb-5">
    <p class="text-sm text-neutral-500">{divisions.length} division{divisions.length !== 1 ? "s" : ""}</p>
    <button onclick={openAddDivision} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">
      Add Division
    </button>
  </div>

  {#if divisionsLoading}
    <div class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
    </div>
  {:else if divisions.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No divisions yet</h3>
      <p class="mt-1.5 text-sm text-neutral-500">Create your first organizational division.</p>
      <button onclick={openAddDivision} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">Add Division</button>
    </div>
  {:else}
    <div class="space-y-3">
      {#each divisions as div}
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <!-- Division Header -->
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            onclick={() => toggleDivision(div.id)}
            class="w-full flex items-center justify-between px-5 py-4 hover:bg-neutral-50 transition-colors text-left cursor-pointer"
          >
            <div class="flex items-center gap-4">
              <svg class="w-4 h-4 text-neutral-400 transition-transform {expandedDivision === div.id ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              <div>
                <p class="text-sm font-semibold text-neutral-800">{div.name}</p>
                {#if div.code}
                  <p class="text-xs text-neutral-400">{div.code}</p>
                {/if}
              </div>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-neutral-400">{div.department_count} dept{div.department_count !== 1 ? "s" : ""}</span>
              {#if !div.is_active}
                <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500">Inactive</span>
              {/if}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div class="flex gap-1" onclick={(e) => e.stopPropagation()}>
                <button onclick={() => openEditDivision(div)} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100 transition-colors">Edit</button>
                <button onclick={() => deleteDivision(div.id)} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 transition-colors">Delete</button>
              </div>
            </div>
          </div>

          <!-- Expanded: Departments -->
          {#if expandedDivision === div.id && divisionDetail}
            <div class="border-t border-neutral-100 bg-neutral-50 px-5 py-4">
              <div class="flex items-center justify-between mb-3">
                <p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Departments</p>
                <button onclick={() => openAddDept(div.id)} class="text-xs font-medium text-neutral-800 hover:underline">+ Add Department</button>
              </div>
              {#if divisionDetail.departments.length === 0}
                <p class="text-sm text-neutral-400 py-2">No departments in this division.</p>
              {:else}
                <div class="space-y-1">
                  {#each divisionDetail.departments as dept}
                    <div class="flex items-center justify-between rounded-lg bg-white px-4 py-3 border border-neutral-200">
                      <div>
                        <p class="text-sm font-medium text-neutral-800">{dept.name}</p>
                        <p class="text-xs text-neutral-400">{[dept.code, dept.head_name].filter(Boolean).join(" · ") || "—"}</p>
                      </div>
                      <div class="flex gap-1">
                        <button onclick={() => openEditDept(dept, div.id)} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100 transition-colors">Edit</button>
                        <button onclick={() => deleteDept(div.id, dept.id)} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 transition-colors">Delete</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
{/if}

<!-- TAB: Cost Centers -->
{#if activeTab === "cost-centers"}
  <div class="flex items-center justify-between mb-5">
    <p class="text-sm text-neutral-500">{costCenters.length} cost center{costCenters.length !== 1 ? "s" : ""}</p>
    <button onclick={openAddCC} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">
      Add Cost Center
    </button>
  </div>

  {#if costCentersLoading}
    <div class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
    </div>
  {:else if costCenters.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No cost centers yet</h3>
      <p class="mt-1.5 text-sm text-neutral-500">Define cost centers for financial tracking.</p>
      <button onclick={openAddCC} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">Add Cost Center</button>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Code</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Name</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Department</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Status</th>
            <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each costCenters as cc}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 font-mono text-xs text-neutral-600">{cc.code}</td>
              <td class="px-5 py-4 font-medium text-neutral-800">{cc.name}</td>
              <td class="px-5 py-4 text-neutral-500">{cc.department_name ?? "—"}</td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {cc.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                  {cc.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button onclick={() => openEditCC(cc)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">Edit</button>
                  <button onclick={() => deleteCC(cc.id)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<!-- TAB: Profit Centers -->
{#if activeTab === "profit-centers"}
  <div class="flex items-center justify-between mb-5">
    <p class="text-sm text-neutral-500">{profitCenters.length} profit center{profitCenters.length !== 1 ? "s" : ""}</p>
    <button onclick={openAddPC} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">
      Add Profit Center
    </button>
  </div>

  {#if profitCentersLoading}
    <div class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
    </div>
  {:else if profitCenters.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No profit centers yet</h3>
      <p class="mt-1.5 text-sm text-neutral-500">Define profit centers for revenue tracking.</p>
      <button onclick={openAddPC} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">Add Profit Center</button>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Code</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Name</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Department</th>
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Status</th>
            <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each profitCenters as pc}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 font-mono text-xs text-neutral-600">{pc.code}</td>
              <td class="px-5 py-4 font-medium text-neutral-800">{pc.name}</td>
              <td class="px-5 py-4 text-neutral-500">{pc.department_name ?? "—"}</td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {pc.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                  {pc.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button onclick={() => openEditPC(pc)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">Edit</button>
                  <button onclick={() => deletePC(pc.id)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<!-- ======== MODALS ======== -->

<!-- Division Modal -->
{#if showDivisionModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showDivisionModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h2 class="text-lg font-bold text-neutral-800 mb-5">{editingDivisionId ? "Edit Division" : "Add Division"}</h2>
      <div class="space-y-4">
        <div>
          <label for="div-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
          <input id="div-name" type="text" bind:value={divisionForm.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="div-code" class="block text-sm font-medium text-neutral-700 mb-1.5">Code</label>
            <input id="div-code" type="text" bind:value={divisionForm.code} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="e.g. ENG" />
          </div>
          <div>
            <label for="div-order" class="block text-sm font-medium text-neutral-700 mb-1.5">Sort Order</label>
            <input id="div-order" type="number" bind:value={divisionForm.sort_order} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>
        </div>
        <div>
          <label for="div-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <textarea id="div-desc" rows="2" bind:value={divisionForm.description} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <input id="div-active" type="checkbox" bind:checked={divisionForm.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
          <label for="div-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="mt-6 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillDivision} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => (showDivisionModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">Cancel</button>
        <button onclick={saveDivision} disabled={savingDivision} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">{savingDivision ? "Saving..." : editingDivisionId ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Department Modal -->
{#if showDeptModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showDeptModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h2 class="text-lg font-bold text-neutral-800 mb-5">{editingDeptId ? "Edit Department" : "Add Department"}</h2>
      <div class="space-y-4">
        <div>
          <label for="dept-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
          <input id="dept-name" type="text" bind:value={deptForm.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="dept-code" class="block text-sm font-medium text-neutral-700 mb-1.5">Code</label>
            <input id="dept-code" type="text" bind:value={deptForm.code} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>
          <div>
            <label for="dept-order" class="block text-sm font-medium text-neutral-700 mb-1.5">Sort Order</label>
            <input id="dept-order" type="number" bind:value={deptForm.sort_order} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>
        </div>
        <div>
          <label for="dept-cost-center-id" class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Center ID *</label>
          <input
            id="dept-cost-center-id"
            type="text"
            bind:value={deptForm.cost_center_id}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            placeholder="e.g. CC-OPS-001"
          />
          <p class="mt-1.5 text-xs text-neutral-500">Required for accounting sync.</p>
        </div>
        <div>
          <label for="dept-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <textarea id="dept-desc" rows="2" bind:value={deptForm.description} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <input id="dept-active" type="checkbox" bind:checked={deptForm.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
          <label for="dept-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="mt-6 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillDept} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => (showDeptModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">Cancel</button>
        <button onclick={saveDept} disabled={savingDept} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">{savingDept ? "Saving..." : editingDeptId ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Cost Center Modal -->
{#if showCCModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showCCModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h2 class="text-lg font-bold text-neutral-800 mb-5">{editingCCId ? "Edit Cost Center" : "Add Cost Center"}</h2>
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="cc-code" class="block text-sm font-medium text-neutral-700 mb-1.5">Code *</label>
            <input id="cc-code" type="text" bind:value={ccForm.code} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="e.g. CC-001" />
          </div>
          <div>
            <label for="cc-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
            <input id="cc-name" type="text" bind:value={ccForm.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>
        </div>
        <div>
          <label for="cc-department" class="block text-sm font-medium text-neutral-700 mb-1.5">Department</label>
          <select
            id="cc-department"
            bind:value={ccForm.department}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value={null}>Unassigned</option>
            {#each costCenterDepartmentOptions as dept}
              <option value={dept.id}>
                {dept.name}{dept.parent_business_unit_name ? ` (${dept.parent_business_unit_name})` : ""}
              </option>
            {/each}
          </select>
          <p class="mt-1.5 text-xs text-neutral-500">
            Assigning a department links this cost center to department-level details.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <input id="cc-active" type="checkbox" bind:checked={ccForm.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
          <label for="cc-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="mt-6 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillCC} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => (showCCModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">Cancel</button>
        <button onclick={saveCC} disabled={savingCC} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">{savingCC ? "Saving..." : editingCCId ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Profit Center Modal -->
{#if showPCModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showPCModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h2 class="text-lg font-bold text-neutral-800 mb-5">{editingPCId ? "Edit Profit Center" : "Add Profit Center"}</h2>
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pc-code" class="block text-sm font-medium text-neutral-700 mb-1.5">Code *</label>
            <input id="pc-code" type="text" bind:value={pcForm.code} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" placeholder="e.g. PC-001" />
          </div>
          <div>
            <label for="pc-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
            <input id="pc-name" type="text" bind:value={pcForm.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>
        </div>
        <div>
          <label for="pc-department" class="block text-sm font-medium text-neutral-700 mb-1.5">Department</label>
          <select
            id="pc-department"
            bind:value={pcForm.department}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value={null}>Unassigned</option>
            {#each costCenterDepartmentOptions as dept}
              <option value={dept.id}>
                {dept.name}{dept.parent_business_unit_name ? ` (${dept.parent_business_unit_name})` : ""}
              </option>
            {/each}
          </select>
          <p class="mt-1.5 text-xs text-neutral-500">
            Assigning a department links this profit center to department reporting.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <input id="pc-active" type="checkbox" bind:checked={pcForm.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
          <label for="pc-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="mt-6 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillPC} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => (showPCModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">Cancel</button>
        <button onclick={savePC} disabled={savingPC} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">{savingPC ? "Saving..." : editingPCId ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}
