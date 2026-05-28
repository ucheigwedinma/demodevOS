<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    CostCenter,
    HeadcountBusinessUnitGuardrail,
    HRPositionListItem,
    HRPositionRole,
    HRPositionRoleListItem,
    HREmploymentType,
    HRPositionLevel,
    HRPositionStatus,
    HRPositionSlotStatus,
    PositionBudgetGuardrailsResponse,
    SalaryStructureListItem,
    PaginatedResponse,
  } from "$lib/types";

  type DepartmentOption = {
    id: number;
    name: string;
    parent_business_unit_id?: number | null;
    parent_business_unit_name?: string | null;
  };

  let positions = $state<HRPositionListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");
  let filterLevel = $state("");
  let filterEmploymentType = $state("");
  let filterRole = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    role: "" as string,
    title: "",
    code: "",
    department: "" as string,
    team: "" as string,
    reports_to: "" as string,
    cost_center: "" as string,
    salary_structure: "" as string,
    employment_type: "full_time" as HREmploymentType,
    level: "mid" as HRPositionLevel,
    status: "active" as HRPositionStatus,
    slot_status: "proposed" as HRPositionSlotStatus,
    criticality_score: 0,
    description: "",
    requirements: "",
    headcount_budget: 1,
    is_active: true,
  });
  let showRoleSlideOver = $state(false);
  let roleSaving = $state(false);
  let roleFieldErrors = $state<Record<string, string[]>>({});
  let roleForm = $state({
    name: "",
    grade: "",
    code: "",
    key_responsibilities: "",
    hard_skills_text: "",
    soft_skills_text: "",
    kpi_metrics_text: "",
    description: "",
    requirements: "",
    is_active: true,
  });

  let departmentOptions = $state<DepartmentOption[]>([]);
  let teamOptions = $state<{ id: number; name: string }[]>([]);
  let managerOptions = $state<{ id: number; title: string; code: string }[]>([]);
  let roleOptions = $state<HRPositionRoleListItem[]>([]);
  let salaryStructureOptions = $state<SalaryStructureListItem[]>([]);
  let costCenterOptions = $state<CostCenter[]>([]);
  let businessUnitBudgetGuardrails = $state<HeadcountBusinessUnitGuardrail[]>([]);
  let allBusinessUnitsFrozen = $state(false);
  let expandedPositionIds = $state<number[]>([]);
  let roleTemplateDetails = $state<Record<number, HRPositionRole>>({});
  let roleTemplateLoading = $state<Record<number, boolean>>({});

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const levelLabels: Record<HRPositionLevel, string> = {
    intern: "Intern", junior: "Junior", mid: "Mid", senior: "Senior", lead: "Lead",
    manager: "Manager", director: "Director", vp: "VP", c_suite: "C-Suite",
  };
  const empTypeLabels: Record<HREmploymentType, string> = {
    full_time: "Full-Time", part_time: "Part-Time", contract: "Contract", temporary: "Temporary", intern: "Intern",
  };
  const statusLabels: Record<HRPositionStatus, string> = {
    active: "Active", frozen: "Frozen", abolished: "Abolished",
  };
  const slotStatusLabels: Record<HRPositionSlotStatus, string> = {
    vacant: "Vacant", filled: "Filled", proposed: "Proposed",
  };
  const levelBadge: Record<HRPositionLevel, string> = {
    intern: "bg-neutral-100 text-neutral-500", junior: "bg-neutral-100 text-neutral-600", mid: "bg-neutral-200 text-neutral-700",
    senior: "bg-neutral-300 text-neutral-800", lead: "bg-neutral-400 text-neutral-900", manager: "bg-neutral-500 text-white",
    director: "bg-neutral-600 text-white", vp: "bg-neutral-700 text-white", c_suite: "bg-neutral-900 text-white",
  };

  const selectedDepartmentOption = $derived(
    departmentOptions.find((department) => String(department.id) === form.department) ?? null,
  );

  const selectedBusinessUnitGuardrail = $derived(
    (() => {
      const businessUnitId = selectedDepartmentOption?.parent_business_unit_id;
      if (!businessUnitId) return null;
      return (
        businessUnitBudgetGuardrails.find((guardrail) => guardrail.division_id === businessUnitId)
        ?? null
      );
    })(),
  );

  const selectedBusinessUnitFrozen = $derived(
    !isEditing && !!selectedBusinessUnitGuardrail?.hiring_freeze,
  );

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const POSITION_SAMPLES = [
    { title: "Senior Site Engineer", code: "POS-ENG-001", employment_type: "full_time" as HREmploymentType, level: "senior" as HRPositionLevel, status: "active" as HRPositionStatus, slot_status: "vacant" as HRPositionSlotStatus, criticality_score: 72, headcount_budget: 3, description: "Oversees on-site structural and MEP works for residential tower projects. Coordinates with subcontractors and ensures compliance with approved shop drawings.", requirements: "BSc Civil Engineering, 8+ years site experience, PMP or equivalent preferred", is_active: true },
    { title: "Sales Executive — Off-Plan", code: "POS-SALES-002", employment_type: "full_time" as HREmploymentType, level: "mid" as HRPositionLevel, status: "active" as HRPositionStatus, slot_status: "filled" as HRPositionSlotStatus, criticality_score: 44, headcount_budget: 5, description: "Manages off-plan sales pipeline from lead qualification through SPA signing. Conducts site tours and handles client objections.", requirements: "3+ years real estate sales experience, RERA broker card, fluent English and Arabic", is_active: true },
    { title: "Quantity Surveyor", code: "POS-QS-003", employment_type: "contract" as HREmploymentType, level: "senior" as HRPositionLevel, status: "active" as HRPositionStatus, slot_status: "proposed" as HRPositionSlotStatus, criticality_score: 88, headcount_budget: 2, description: "Prepares BOQs, evaluates contractor claims, and manages variation orders. Produces monthly cost reports for project management.", requirements: "BSc Quantity Surveying, MRICS or working towards, 6+ years in GCC construction", is_active: true },
  ];
  let posDevIdx = 0;
  function devFillPosition() {
    const s = POSITION_SAMPLES[posDevIdx % POSITION_SAMPLES.length];
    posDevIdx++;
    form.role = roleOptions.length > 0 ? String(roleOptions[posDevIdx % roleOptions.length].id) : "";
    form.title = s.title;
    form.code = s.code;
    form.employment_type = s.employment_type;
    form.level = s.level;
    form.status = s.status;
    form.slot_status = s.slot_status;
    form.criticality_score = s.criticality_score;
    form.headcount_budget = s.headcount_budget;
    form.description = s.description;
    form.requirements = s.requirements;
    form.is_active = s.is_active;
    form.department = departmentOptions.length > 0 ? String(departmentOptions[posDevIdx % departmentOptions.length].id) : "";
    form.team = teamOptions.length > 0 ? String(teamOptions[posDevIdx % teamOptions.length].id) : "";
    form.reports_to = "";
    form.cost_center = costCenterOptions.length > 0 ? String(costCenterOptions[posDevIdx % costCenterOptions.length].id) : "";
    form.salary_structure = salaryStructureOptions.length > 0 ? String(salaryStructureOptions[posDevIdx % salaryStructureOptions.length].id) : "";
  }

  const ROLE_SAMPLES = [
    {
      name: "Senior Site Engineer", grade: "G6", code: "SE-SR",
      key_responsibilities: "Supervise on-site construction activities, ensure quality standards, coordinate with design consultants and subcontractors.",
      hard_skills_text: "Structural engineering, AutoCAD, Revit, Quality control, Surveying",
      soft_skills_text: "Attention to detail, Decision-making, Team coordination",
      kpi_metrics_text: "Defect rate, Safety incident count, Daily progress vs plan",
      description: "Technical lead for on-site construction execution and quality assurance",
      requirements: "BSc Civil/Structural Engineering, 8+ years site experience, NEBOSH preferred",
      is_active: true,
    },
    {
      name: "Finance Manager", grade: "G6", code: "FIN-MGR",
      key_responsibilities: "Oversee financial reporting, budgeting, and cash flow management. Ensure regulatory compliance and coordinate external audits.",
      hard_skills_text: "IFRS, Financial modelling, ERP systems, Tax compliance, Audit coordination",
      soft_skills_text: "Analytical thinking, Strategic planning, Stakeholder management",
      kpi_metrics_text: "Reporting deadline adherence, Audit findings count, Budget accuracy",
      description: "Head of finance operations for the organization",
      requirements: "ACCA/CPA qualified, 6+ years in real estate finance, ERP experience",
      is_active: true,
    },
    {
      name: "Procurement Officer", grade: "G4", code: "PROC-OFF",
      key_responsibilities: "Process purchase requisitions, solicit quotes, evaluate vendors, and manage purchase orders through to delivery.",
      hard_skills_text: "RFQ processing, Vendor evaluation, ERP data entry, Contract review",
      soft_skills_text: "Organization, Follow-through, Negotiation",
      kpi_metrics_text: "PO processing time, Quote comparison accuracy, Vendor on-time delivery",
      description: "Handles procurement operations from requisition to delivery",
      requirements: "Diploma in Supply Chain or Business, 3+ years procurement experience",
      is_active: true,
    },
  ];
  let roleDevIdx = 0;
  function devFillRole() {
    const s = ROLE_SAMPLES[roleDevIdx % ROLE_SAMPLES.length];
    roleDevIdx++;
    roleForm.name = s.name;
    roleForm.grade = s.grade;
    roleForm.code = s.code;
    roleForm.key_responsibilities = s.key_responsibilities;
    roleForm.hard_skills_text = s.hard_skills_text;
    roleForm.soft_skills_text = s.soft_skills_text;
    roleForm.kpi_metrics_text = s.kpi_metrics_text;
    roleForm.description = s.description;
    roleForm.requirements = s.requirements;
    roleForm.is_active = s.is_active;
  }

  async function fetchPositions() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      if (filterLevel) params.level = filterLevel;
      if (filterEmploymentType) params.employment_type = filterEmploymentType;
      if (filterRole) params.role = filterRole;
      const res = await api.get<PaginatedResponse<HRPositionListItem>>("/hr/positions/", params);
      positions = res.results;
      totalCount = res.count;
    } catch {
      positions = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchFormOptions() {
    try {
      const [deptRes, teamRes, roleRes, managerRes, salaryRes, costCenterRes] = await Promise.all([
        api.get<{ results: DepartmentOption[] }>("/settings/departments/", { page_size: "200" }),
        api.get<{ results: { id: number; name: string }[] }>("/hr/teams/", { page_size: "200" }),
        api.get<PaginatedResponse<HRPositionRoleListItem>>("/hr/position-roles/", { page_size: "200" }),
        api.get<PaginatedResponse<HRPositionListItem>>("/hr/positions/", { page_size: "500" }),
        api.get<PaginatedResponse<SalaryStructureListItem>>("/hr/salary-structures/", { page_size: "200", is_active: "true" }),
        api.get<PaginatedResponse<CostCenter>>("/settings/cost-centers/", { page_size: "500", is_active: "true" }),
      ]);
      departmentOptions = deptRes.results;
      teamOptions = teamRes.results;
      roleOptions = roleRes.results;
      managerOptions = managerRes.results.map((item) => ({
        id: item.id,
        title: item.title,
        code: item.code,
      }));
      salaryStructureOptions = salaryRes.results;
      costCenterOptions = costCenterRes.results;
    } catch { /* ignore */ }
  }

  async function fetchBudgetGuardrails() {
    try {
      const response = await api.get<PositionBudgetGuardrailsResponse>("/hr/positions/budget-guardrails/");
      businessUnitBudgetGuardrails = response.business_units ?? [];
      allBusinessUnitsFrozen = response.all_frozen ?? false;
    } catch {
      businessUnitBudgetGuardrails = [];
      allBusinessUnitsFrozen = false;
    }
  }

  function guardrailForDepartment(departmentId: string): HeadcountBusinessUnitGuardrail | null {
    const department = departmentOptions.find((item) => String(item.id) === departmentId);
    if (!department?.parent_business_unit_id) return null;
    return (
      businessUnitBudgetGuardrails.find(
        (guardrail) => guardrail.division_id === department.parent_business_unit_id,
      )
      ?? null
    );
  }

  function isDepartmentUnderHiringFreeze(departmentId: string): boolean {
    const guardrail = guardrailForDepartment(departmentId);
    return !!guardrail?.hiring_freeze;
  }

  function resetForm() {
    form = {
      role: "",
      title: "",
      code: "",
      department: "",
      team: "",
      reports_to: "",
      cost_center: "",
      salary_structure: "",
      employment_type: "full_time",
      level: "mid",
      status: "active",
      slot_status: "proposed",
      criticality_score: 0,
      description: "",
      requirements: "",
      headcount_budget: 1,
      is_active: true,
    };
    fieldErrors = {};
    editingId = null;
  }

  function openCreate() {
    if (allBusinessUnitsFrozen) {
      toast.error(
        "Hiring freeze active",
        "All business units are under hiring freeze because position-budget variance is exhausted.",
      );
      return;
    }
    resetForm();
    fetchFormOptions();
    fetchBudgetGuardrails();
    showSlideOver = true;
  }

  async function openEdit(pos: HRPositionListItem) {
    resetForm();
    editingId = pos.id;
    form.role = pos.role ? String(pos.role) : "";
    form.title = pos.title;
    form.code = pos.code;
    form.department = String(pos.department);
    form.team = pos.team ? String(pos.team) : "";
    form.reports_to = pos.reports_to ? String(pos.reports_to) : "";
    form.cost_center = pos.cost_center ? String(pos.cost_center) : "";
    form.salary_structure = pos.salary_structure ? String(pos.salary_structure) : "";
    form.employment_type = pos.employment_type;
    form.level = pos.level;
    form.status = pos.status;
    form.slot_status = pos.slot_status;
    form.criticality_score = pos.criticality_score;
    form.headcount_budget = pos.headcount_budget;
    form.is_active = pos.is_active;
    await fetchFormOptions();
    try {
      const detail = await api.get<{ description: string; requirements: string }>(`/hr/positions/${pos.id}/`);
      form.description = detail.description;
      form.requirements = detail.requirements;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    if (!form.role) {
      fieldErrors = { role: ["Role template is required."] };
      saving = false;
      return;
    }
    if (!form.cost_center) {
      fieldErrors = { cost_center: ["Cost center is required."] };
      saving = false;
      return;
    }
    if (!isEditing && selectedBusinessUnitFrozen) {
      fieldErrors = {
        department: ["Selected department belongs to a Business Unit under hiring freeze."],
      };
      saving = false;
      return;
    }
    try {
      const payload: Record<string, unknown> = {
        role: form.role ? Number(form.role) : null,
        title: form.title,
        code: form.code,
        department: form.department ? Number(form.department) : undefined,
        team: form.team ? Number(form.team) : null,
        reports_to: form.reports_to ? Number(form.reports_to) : null,
        cost_center: form.cost_center ? Number(form.cost_center) : null,
        salary_structure: form.salary_structure ? Number(form.salary_structure) : null,
        employment_type: form.employment_type,
        level: form.level,
        status: form.status,
        slot_status: form.slot_status,
        criticality_score: form.criticality_score,
        description: form.description,
        requirements: form.requirements,
        headcount_budget: form.headcount_budget,
        is_active: form.is_active,
      };

      if (isEditing) {
        await api.patch(`/hr/positions/${editingId}/`, payload);
        toast.success("Position updated");
      } else {
        await api.post("/hr/positions/", payload);
        toast.success("Position created");
      }
      showSlideOver = false;
      resetForm();
      fetchPositions();
      fetchBudgetGuardrails();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const validationMessage =
          err.fieldErrors.non_field_errors?.[0]
          ?? err.fieldErrors.department?.[0]
          ?? "";
        if (validationMessage) {
          toast.error("Validation error", validationMessage);
        }
      } else {
        toast.error("Failed to save position");
      }
    } finally {
      saving = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchPositions(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchPositions();
  }

  function costCentersForDepartment(departmentId: string) {
    if (!departmentId) return costCenterOptions;
    const parsedDepartment = Number(departmentId);
    return costCenterOptions.filter(
      (costCenter) =>
        costCenter.department === null || costCenter.department === parsedDepartment,
    );
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function isPositionExpanded(positionId: number): boolean {
    return expandedPositionIds.includes(positionId);
  }

  async function ensureRoleTemplateLoaded(roleId: number | null): Promise<void> {
    if (!roleId) return;
    if (roleTemplateDetails[roleId] || roleTemplateLoading[roleId]) return;
    roleTemplateLoading = { ...roleTemplateLoading, [roleId]: true };
    try {
      const detail = await api.get<HRPositionRole>(`/hr/position-roles/${roleId}/`);
      roleTemplateDetails = { ...roleTemplateDetails, [roleId]: detail };
    } catch {
      // Keep table usable even when role detail fetch fails.
    } finally {
      roleTemplateLoading = { ...roleTemplateLoading, [roleId]: false };
    }
  }

  function roleDetailForPosition(pos: HRPositionListItem): HRPositionRole | null {
    if (!pos.role) return null;
    return roleTemplateDetails[pos.role] ?? null;
  }

  function splitDetailList(input: string): string[] {
    return (input || "")
      .split(/\r?\n|;+/)
      .map((item) => item.replace(/^-+\s*/, "").trim())
      .filter(Boolean);
  }

  function togglePositionExpansion(pos: HRPositionListItem): void {
    if (isPositionExpanded(pos.id)) {
      expandedPositionIds = expandedPositionIds.filter((id) => id !== pos.id);
      return;
    }
    expandedPositionIds = [...expandedPositionIds, pos.id];
    void ensureRoleTemplateLoaded(pos.role);
  }

  function resetRoleForm() {
    roleForm = {
      name: "",
      grade: "",
      code: "",
      key_responsibilities: "",
      hard_skills_text: "",
      soft_skills_text: "",
      kpi_metrics_text: "",
      description: "",
      requirements: "",
      is_active: true,
    };
    roleFieldErrors = {};
  }

  function parseCommaList(input: string) {
    return input
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function openCreateRole() {
    resetRoleForm();
    showRoleSlideOver = true;
  }

  function roleFieldError(field: string): string {
    return roleFieldErrors[field]?.[0] ?? "";
  }

  async function handleSaveRole() {
    roleSaving = true;
    roleFieldErrors = {};
    try {
      const created = await api.post<HRPositionRoleListItem>("/hr/position-roles/", {
        name: roleForm.name,
        grade: roleForm.grade,
        code: roleForm.code,
        key_responsibilities: roleForm.key_responsibilities,
        hard_skills: parseCommaList(roleForm.hard_skills_text),
        soft_skills: parseCommaList(roleForm.soft_skills_text),
        kpi_metrics: parseCommaList(roleForm.kpi_metrics_text),
        description: roleForm.description,
        requirements: roleForm.requirements,
        is_active: roleForm.is_active,
      });
      await fetchFormOptions();
      form.role = String(created.id);
      showRoleSlideOver = false;
      resetRoleForm();
      toast.success("Role template created");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        roleFieldErrors = err.fieldErrors;
      } else {
        toast.error("Failed to save role template");
      }
    } finally {
      roleSaving = false;
    }
  }

  $effect(() => {
    fetchFormOptions();
    fetchBudgetGuardrails();
    fetchPositions();
  });
</script>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Positions & Roles</h1>
      <p class="mt-1 text-sm text-neutral-500">Blueprint of role templates and budgeted position slots</p>
    </div>
    <div class="flex items-center gap-2">
      <button
        onclick={openCreateRole}
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-neutral-800 border border-neutral-300 rounded-lg hover:bg-neutral-100 transition-colors"
      >
        Add Role Template
      </button>
      <button
        onclick={openCreate}
        disabled={allBusinessUnitsFrozen}
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
        Add Position
      </button>
    </div>
  </div>

  <div class="mb-6 rounded-xl border border-neutral-200 bg-white px-4 py-3">
    <p class="text-xs uppercase tracking-wide text-neutral-500">Definition Guide</p>
    <p class="mt-1 text-sm text-neutral-700">
      <span class="font-semibold text-neutral-900">Role</span>: reusable functional template.
      <span class="mx-2 text-neutral-300">|</span>
      <span class="font-semibold text-neutral-900">Position</span>: budgeted slot that references one role.
    </p>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search positions..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchPositions(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Lifecycle Status</option>
      {#each Object.entries(statusLabels) as [k, v]}
        <option value={k}>{v}</option>
      {/each}
    </select>
    <select value={filterLevel} onchange={(e) => { filterLevel = e.currentTarget.value; currentPage = 1; fetchPositions(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Levels</option>
      {#each Object.entries(levelLabels) as [k, v]}
        <option value={k}>{v}</option>
      {/each}
    </select>
    <select value={filterEmploymentType} onchange={(e) => { filterEmploymentType = e.currentTarget.value; currentPage = 1; fetchPositions(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(empTypeLabels) as [k, v]}
        <option value={k}>{v}</option>
      {/each}
    </select>
    <select value={filterRole} onchange={(e) => { filterRole = e.currentTarget.value; currentPage = 1; fetchPositions(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Roles</option>
      {#each roleOptions as role}
        <option value={String(role.id)}>{role.name}</option>
      {/each}
    </select>
  </div>

  <!-- Table -->
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if positions.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">{searchQuery || filterStatus || filterLevel || filterEmploymentType || filterRole ? "No positions match your filters" : "No positions created yet"}</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/50">
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position Slot</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Role Template</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Level</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reporting Line</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Type</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Filled</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Open</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each positions as pos}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-3.5">
                  <div class="flex items-start gap-2">
                    <button
                      type="button"
                      class="mt-0.5 rounded p-1 text-neutral-500 hover:bg-neutral-200/70 hover:text-neutral-800 transition-colors"
                      aria-label={isPositionExpanded(pos.id) ? "Collapse position summary" : "Expand position summary"}
                      onclick={() => togglePositionExpansion(pos)}
                    >
                      <svg
                        class="h-4 w-4 transition-transform {isPositionExpanded(pos.id) ? 'rotate-90' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        stroke-width="2"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" d="m9 5 7 7-7 7" />
                      </svg>
                    </button>
                    <div>
                      <span class="font-medium text-neutral-900">{pos.title}</span>
                      {#if pos.reports_to_title}
                        <p class="text-xs text-neutral-400 mt-0.5">Reports to: {pos.reports_to_title}</p>
                      {/if}
                    </div>
                  </div>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">
                  {#if pos.role_name}
                    <span class="font-medium text-neutral-800">
                      {pos.role_name}{pos.role_grade ? ` - ${pos.role_grade}` : ""}
                    </span>
                    {#if pos.role_code}
                      <p class="text-[11px] font-mono text-neutral-400 mt-0.5">{pos.role_code}</p>
                    {/if}
                  {:else}
                    <span class="text-neutral-400">Unlinked</span>
                  {/if}
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{pos.department_name}</td>
                <td class="px-5 py-3.5">
                  <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {levelBadge[pos.level] ?? ''}">{levelLabels[pos.level] ?? pos.level}</span>
                </td>
                <td class="px-5 py-3.5 text-xs text-neutral-600">
                  <p class="text-xs text-neutral-700">
                    {pos.reports_to_title ? `Manager: ${pos.reports_to_title}` : "Manager: None"}
                  </p>
                  <p class="mt-0.5 text-[11px] text-neutral-500">{pos.direct_report_count} direct report{pos.direct_report_count === 1 ? "" : "s"}</p>
                </td>
                <td class="px-5 py-3.5 text-neutral-600 text-xs">{empTypeLabels[pos.employment_type] ?? pos.employment_type}</td>
                <td class="px-5 py-3.5 text-center text-neutral-600">{pos.filled_count}</td>
                <td class="px-5 py-3.5 text-center text-neutral-600">{pos.vacancy_count}</td>
                <td class="px-5 py-3.5 text-center">
                  <StatusBadge status={pos.slot_status} />
                  <p class="mt-1 text-[10px] text-neutral-400">{statusLabels[pos.status]}</p>
                  <button
                    type="button"
                    onclick={() => openEdit(pos)}
                    class="mt-1 inline-flex text-[11px] font-semibold text-blue-700 hover:text-blue-800"
                  >
                    Edit
                  </button>
                </td>
              </tr>
              {#if isPositionExpanded(pos.id)}
                <tr class="bg-neutral-50/60">
                  <td colspan={9} class="px-5 py-4">
                    <div class="grid gap-4 lg:grid-cols-2">
                      <section class="rounded-lg border border-neutral-200 bg-white p-4">
                        <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Position Slot Details</h3>
                        <dl class="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Department</dt>
                            <dd class="font-medium text-neutral-900">{pos.department_name}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Team</dt>
                            <dd class="text-neutral-700">{pos.team_name ?? "None"}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Employment</dt>
                            <dd class="text-neutral-700">{empTypeLabels[pos.employment_type] ?? pos.employment_type}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Level</dt>
                            <dd class="text-neutral-700">{levelLabels[pos.level] ?? pos.level}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Reporting Line</dt>
                            <dd class="text-neutral-700">
                              {pos.reports_to_title ? `${pos.reports_to_title} (${pos.direct_report_count} direct reports)` : "No manager assigned"}
                            </dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Cost Center</dt>
                            <dd class="text-neutral-700">{pos.cost_center_code ?? "Not linked"}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Slot Status</dt>
                            <dd class="text-neutral-700">{slotStatusLabels[pos.slot_status] ?? pos.slot_status}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Lifecycle</dt>
                            <dd class="text-neutral-700">{statusLabels[pos.status] ?? pos.status}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Salary Band</dt>
                            <dd class="text-neutral-700">
                              {#if pos.salary_structure_name}
                                {pos.salary_structure_name}
                                {#if pos.salary_range_min !== null && pos.salary_range_max !== null}
                                  <span class="text-neutral-500"> ({pos.salary_currency ?? ""} {pos.salary_range_min} - {pos.salary_range_max})</span>
                                {/if}
                              {:else}
                                Not linked
                              {/if}
                            </dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Budget</dt>
                            <dd class="text-neutral-700">{pos.headcount_budget}</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Headcount</dt>
                            <dd class="text-neutral-700">{pos.filled_count}/{pos.headcount_budget} filled ({pos.vacancy_count} open)</dd>
                          </div>
                          <div>
                            <dt class="text-[11px] uppercase tracking-wide text-neutral-500">Criticality</dt>
                            <dd class="text-neutral-700">
                              <span class="font-semibold {pos.criticality_score >= 80 ? 'text-red-700' : pos.criticality_score >= 60 ? 'text-amber-700' : 'text-neutral-700'}">
                                {pos.criticality_score}
                              </span>
                              {#if pos.criticality_score >= 80}
                                <span class="text-red-600"> (Critical)</span>
                              {/if}
                            </dd>
                          </div>
                        </dl>

                        <div class="mt-4 rounded-md border border-neutral-200 p-3">
                          <p class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Automation</p>
                          <div class="mt-2 space-y-1 text-sm text-neutral-700">
                            <p>
                              <span class="font-semibold text-neutral-800">Budget Validation:</span>
                              {pos.budget_guard_active ? " Guarded" : " Not linked"}
                            </p>
                            <p>
                              <span class="font-semibold text-neutral-800">Recruitment Trigger:</span>
                              {#if pos.active_requisition_id}
                                {" "}#{pos.active_requisition_id}
                                {#if pos.active_requisition_status}
                                  <span class="text-neutral-500"> ({pos.active_requisition_status.replace("_", " ")})</span>
                                {/if}
                              {:else}
                                <span class="text-neutral-500"> None</span>
                              {/if}
                            </p>
                            {#if pos.criticality_score >= 80}
                              <p>
                                <span class="font-semibold text-neutral-800">Succession Alert:</span>
                                {#if pos.succession_alert_due}
                                  <span class="text-red-700"> Urgent ({pos.vacancy_days_open}d vacant)</span>
                                {:else if pos.vacancy_alert_sent_at}
                                  <span class="text-emerald-700"> Alert sent</span>
                                {:else}
                                  <span class="text-neutral-500"> Monitoring</span>
                                {/if}
                              </p>
                            {/if}
                          </div>
                        </div>
                      </section>

                      <section class="rounded-lg border border-neutral-200 bg-white p-4">
                        <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Role Template Nest</h3>
                        {#if !pos.role}
                          <p class="mt-3 text-sm text-neutral-500">This position has no role template linked.</p>
                        {:else if roleTemplateLoading[pos.role]}
                          <div class="mt-3 flex items-center gap-2 text-sm text-neutral-500">
                            <span class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-700 animate-spin"></span>
                            Loading role template details...
                          </div>
                        {:else if roleDetailForPosition(pos)}
                          {@const roleDetail = roleDetailForPosition(pos)}
                          <div class="mt-3 space-y-3">
                            <div class="rounded-md border border-neutral-200 p-3">
                              <p class="text-sm font-semibold text-neutral-900">
                                {roleDetail?.name}
                                {#if roleDetail?.grade}
                                  <span class="text-neutral-500"> - {roleDetail.grade}</span>
                                {/if}
                              </p>
                              {#if roleDetail?.code}
                                <p class="mt-1 text-[11px] font-mono text-neutral-500">{roleDetail.code}</p>
                              {/if}
                              {#if roleDetail?.description}
                                <p class="mt-2 text-sm text-neutral-700">{roleDetail.description}</p>
                              {/if}
                              {#if roleDetail?.requirements}
                                <p class="mt-2 text-xs text-neutral-600">
                                  <span class="font-semibold text-neutral-700">Requirements:</span> {roleDetail.requirements}
                                </p>
                              {/if}
                            </div>

                            <div class="grid gap-3 sm:grid-cols-2">
                              <div class="rounded-md border border-neutral-200 p-3 sm:col-span-2">
                                <p class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Key Responsibilities</p>
                                {#if splitDetailList(roleDetail?.key_responsibilities ?? "").length > 0}
                                  <ul class="mt-2 space-y-1 text-sm text-neutral-700">
                                    {#each splitDetailList(roleDetail?.key_responsibilities ?? "") as responsibility}
                                      <li>• {responsibility}</li>
                                    {/each}
                                  </ul>
                                {:else}
                                  <p class="mt-2 text-sm text-neutral-500">No responsibilities captured.</p>
                                {/if}
                              </div>
                              <div class="rounded-md border border-neutral-200 p-3">
                                <p class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Hard Skills</p>
                                <p class="mt-2 text-sm text-neutral-700">{roleDetail?.hard_skills?.length ? roleDetail.hard_skills.join(", ") : "Not specified"}</p>
                              </div>
                              <div class="rounded-md border border-neutral-200 p-3">
                                <p class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Soft Skills</p>
                                <p class="mt-2 text-sm text-neutral-700">{roleDetail?.soft_skills?.length ? roleDetail.soft_skills.join(", ") : "Not specified"}</p>
                              </div>
                              <div class="rounded-md border border-neutral-200 p-3 sm:col-span-2">
                                <p class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">KPIs</p>
                                <p class="mt-2 text-sm text-neutral-700">{roleDetail?.kpi_metrics?.length ? roleDetail.kpi_metrics.join(", ") : "Not specified"}</p>
                              </div>
                            </div>
                          </div>
                        {:else}
                          <p class="mt-3 text-sm text-neutral-500">Role template details are unavailable right now.</p>
                        {/if}
                      </section>
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} position{totalCount !== 1 ? 's' : ''}</span>
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

<!-- Slide-over -->
{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-lg bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Position" : "Create Position"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="pos-role" class="block text-sm font-medium text-neutral-700 mb-1">Role Template <span class="text-red-500">*</span></label>
          <div class="flex items-center gap-2">
            <select id="pos-role" bind:value={form.role} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('role') ? 'border-red-400' : ''}">
              <option value="">Select role template</option>
              {#each roleOptions as role}
                <option value={String(role.id)}>
                  {role.name}{role.grade ? ` - ${role.grade}` : ""}{role.code ? ` (${role.code})` : ""}
                </option>
              {/each}
            </select>
            <button
              type="button"
              onclick={openCreateRole}
              class="shrink-0 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
            >
              New Role
            </button>
          </div>
          {#if fieldError("role")}<p class="text-xs text-red-500 mt-1">{fieldError("role")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pos-title" class="block text-sm font-medium text-neutral-700 mb-1">Position Slot Title <span class="text-red-500">*</span></label>
            <input id="pos-title" type="text" bind:value={form.title} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('title') ? 'border-red-400' : ''}" />
            {#if fieldError("title")}<p class="text-xs text-red-500 mt-1">{fieldError("title")}</p>{/if}
          </div>
          <div>
            <label for="pos-code" class="block text-sm font-medium text-neutral-700 mb-1">Code <span class="text-red-500">*</span></label>
            <input id="pos-code" type="text" bind:value={form.code} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 font-mono {fieldError('code') ? 'border-red-400' : ''}" />
            {#if fieldError("code")}<p class="text-xs text-red-500 mt-1">{fieldError("code")}</p>{/if}
          </div>
        </div>
        <div>
          <label for="pos-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department <span class="text-red-500">*</span></label>
          <select id="pos-dept" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('department') ? 'border-red-400' : ''}">
            <option value="">Select department</option>
            {#each departmentOptions as dept}
              <option
                value={String(dept.id)}
                disabled={!isEditing && isDepartmentUnderHiringFreeze(String(dept.id))}
              >
                {dept.name}{isDepartmentUnderHiringFreeze(String(dept.id)) ? " (Hiring freeze)" : ""}
              </option>
            {/each}
          </select>
          {#if fieldError("department")}<p class="text-xs text-red-500 mt-1">{fieldError("department")}</p>{/if}
          {#if selectedBusinessUnitFrozen}
            <p class="mt-1 text-xs text-amber-700">
              Hiring freeze is active for {selectedBusinessUnitGuardrail?.division_name}.
              Unallocated budget: {selectedBusinessUnitGuardrail?.unallocated_budget ?? "0"}.
            </p>
          {/if}
        </div>
        <div>
          <label for="pos-team" class="block text-sm font-medium text-neutral-700 mb-1">Team</label>
          <select id="pos-team" bind:value={form.team} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">None</option>
            {#each teamOptions as t}
              <option value={String(t.id)}>{t.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for="pos-manager" class="block text-sm font-medium text-neutral-700 mb-1">Reporting Manager</label>
          <select id="pos-manager" bind:value={form.reports_to} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">None</option>
            {#each managerOptions as item}
              {#if !editingId || item.id !== editingId}
                <option value={String(item.id)}>{item.title} ({item.code})</option>
              {/if}
            {/each}
          </select>
        </div>
        <div>
          <label for="pos-cost-center" class="block text-sm font-medium text-neutral-700 mb-1">Cost Center <span class="text-red-500">*</span></label>
          <select id="pos-cost-center" bind:value={form.cost_center} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('cost_center') ? 'border-red-400' : ''}">
            <option value="">Select cost center</option>
            {#each costCentersForDepartment(form.department) as center}
              <option value={String(center.id)}>{center.code} - {center.name}</option>
            {/each}
          </select>
          {#if fieldError("cost_center")}<p class="text-xs text-red-500 mt-1">{fieldError("cost_center")}</p>{/if}
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="pos-level" class="block text-sm font-medium text-neutral-700 mb-1">Level</label>
            <select id="pos-level" bind:value={form.level} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(levelLabels) as [k, v]}
                <option value={k}>{v}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="pos-emp-type" class="block text-sm font-medium text-neutral-700 mb-1">Employment</label>
            <select id="pos-emp-type" bind:value={form.employment_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(empTypeLabels) as [k, v]}
                <option value={k}>{v}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="pos-headcount" class="block text-sm font-medium text-neutral-700 mb-1">Headcount</label>
            <input id="pos-headcount" type="number" min="1" bind:value={form.headcount_budget} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="pos-salary-structure" class="block text-sm font-medium text-neutral-700 mb-1">Salary Band (Finance Link)</label>
          <select id="pos-salary-structure" bind:value={form.salary_structure} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">None</option>
            {#each salaryStructureOptions as structure}
              <option value={String(structure.id)}>
                {structure.name} ({structure.currency} {structure.min_salary} - {structure.max_salary})
              </option>
            {/each}
          </select>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="pos-slot-status" class="block text-sm font-medium text-neutral-700 mb-1">Position Status</label>
            <select id="pos-slot-status" bind:value={form.slot_status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(slotStatusLabels) as [k, v]}
                <option value={k}>{v}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="pos-status" class="block text-sm font-medium text-neutral-700 mb-1">Lifecycle Status</label>
            <select id="pos-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [k, v]}
                <option value={k}>{v}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="pos-criticality" class="block text-sm font-medium text-neutral-700 mb-1">Criticality Score</label>
            <input
              id="pos-criticality"
              type="number"
              min="0"
              max="100"
              bind:value={form.criticality_score}
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
            />
            <p class="mt-1 text-[11px] text-neutral-500">80+ triggers succession urgency automation.</p>
          </div>
        </div>
        <div>
          <label for="pos-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="pos-desc" bind:value={form.description} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="pos-req" class="block text-sm font-medium text-neutral-700 mb-1">Requirements</label>
          <textarea id="pos-req" bind:value={form.requirements} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <input id="pos-active" type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" />
          <label for="pos-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillPosition} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving || selectedBusinessUnitFrozen} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if showRoleSlideOver}
  <div class="fixed inset-0 z-60 flex justify-end">
    <button
      class="absolute inset-0 bg-black/30 backdrop-blur-sm"
      onclick={() => { showRoleSlideOver = false; resetRoleForm(); }}
      aria-label="Close role template editor"
    ></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">Create Role Template</h2>
        <button onclick={() => { showRoleSlideOver = false; resetRoleForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close role template editor">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="role-name" class="block text-sm font-medium text-neutral-700 mb-1">Job Title <span class="text-red-500">*</span></label>
          <input id="role-name" type="text" bind:value={roleForm.name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {roleFieldError('name') ? 'border-red-400' : ''}" />
          {#if roleFieldError("name")}<p class="text-xs text-red-500 mt-1">{roleFieldError("name")}</p>{/if}
        </div>
        <div>
          <label for="role-grade" class="block text-sm font-medium text-neutral-700 mb-1">Grade</label>
          <input id="role-grade" type="text" bind:value={roleForm.grade} placeholder="e.g., Grade 4" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          <p class="mt-1 text-xs text-neutral-500">Supports Finance salary banding.</p>
        </div>
        <div>
          <label for="role-code" class="block text-sm font-medium text-neutral-700 mb-1">Role Code</label>
          <input id="role-code" type="text" bind:value={roleForm.code} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900 {roleFieldError('code') ? 'border-red-400' : ''}" />
          {#if roleFieldError("code")}<p class="text-xs text-red-500 mt-1">{roleFieldError("code")}</p>{/if}
        </div>
        <div>
          <label for="role-responsibilities" class="block text-sm font-medium text-neutral-700 mb-1">Key Responsibilities</label>
          <textarea id="role-responsibilities" bind:value={roleForm.key_responsibilities} rows={4} placeholder={"- Lead weekly site planning\n- Track contractor output\n- Validate quality checks"} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900"></textarea>
        </div>
        <div>
          <label for="role-hard-skills" class="block text-sm font-medium text-neutral-700 mb-1">Required Competencies (Hard Skills)</label>
          <input id="role-hard-skills" type="text" bind:value={roleForm.hard_skills_text} placeholder="AutoCAD, Revit, Primavera P6" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="role-soft-skills" class="block text-sm font-medium text-neutral-700 mb-1">Required Competencies (Soft Skills)</label>
          <input id="role-soft-skills" type="text" bind:value={roleForm.soft_skills_text} placeholder="Stakeholder Management, Team Leadership" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="role-kpis" class="block text-sm font-medium text-neutral-700 mb-1">Key Performance Indicators (KPIs)</label>
          <input id="role-kpis" type="text" bind:value={roleForm.kpi_metrics_text} placeholder="% milestones met on time, cost variance, rework rate" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div class="flex items-center gap-2">
          <input id="role-active" type="checkbox" bind:checked={roleForm.is_active} class="rounded border-neutral-300" />
          <label for="role-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillRole} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showRoleSlideOver = false; resetRoleForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSaveRole} disabled={roleSaving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {roleSaving ? "Saving..." : "Create Role"}
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
