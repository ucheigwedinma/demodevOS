<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    ProjectSetupConfigItem,
    ProjectTeamMemberItem,
    TeamMemberRole,
    TeamAccessLevel,
    SetupStep,
    PipelineOpportunityListItem,
    PaginatedResponse,
    PropertyListItem,
    LandStatus,
    ProjectType,
    ProjectTemplate,
    ProjectTemplateListItem,
    HRPositionRoleListItem,
    HRTeamListItem,
    HREmploymentType,
    HRPositionLevel,
    Department,
    CostCenter,
  } from "$lib/types";

  // ── Types for ownership / role-library / template-phase rows ───────────
  type OwnershipAllocationRow = { party_name: string; ownership_percentage: string };

  type RoleLibraryProvisionRow = {
    role: string;
    department: string;
    cost_center: string;
    team: string;
    quantity: string;
    employment_type: HREmploymentType;
    level: HRPositionLevel;
    criticality_score: string;
  };

  type EditableMilestone = { name: string; description: string; days_from_phase_start: string };
  type EditableDocument = { name: string; category: string; description: string; is_mandatory: boolean };
  type EditableCheckpoint = { name: string; description: string; regulatory_reference: string; is_mandatory: boolean };
  type EditablePhase = {
    name: string;
    description: string;
    sort_order: number;
    duration_days: string;
    weight: string;
    milestones: EditableMilestone[];
    required_documents: EditableDocument[];
    compliance_checkpoints: EditableCheckpoint[];
  };

  function emptyOwnershipRow(): OwnershipAllocationRow {
    return { party_name: "", ownership_percentage: "" };
  }
  function emptyRoleLibraryRow(): RoleLibraryProvisionRow {
    return {
      role: "",
      department: "",
      cost_center: "",
      team: "",
      quantity: "1",
      employment_type: "full_time",
      level: "mid",
      criticality_score: "0",
    };
  }

  // ── State ─────────────────────────────────────────────────────────────
  let configs = $state<ProjectSetupConfigItem[]>([]);
  let loading = $state(true);

  // Wizard drawer
  let wizardOpen = $state(false);
  let wizardStep = $state(1);
  let saving = $state(false);

  // Step 1: Identity & Schedule
  let form = $state(defaultForm());
  let pipelines = $state<PipelineOpportunityListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);

  // Step 2: Ownership
  let ownershipRows = $state<OwnershipAllocationRow[]>([emptyOwnershipRow()]);

  // Step 3: Team & Roles
  let teamRows = $state<{ name: string; role: TeamMemberRole; access_level: TeamAccessLevel; email: string; company: string }[]>([]);
  let roleLibraryRows = $state<RoleLibraryProvisionRow[]>([]);
  let roleLibraryOptions = $state<HRPositionRoleListItem[]>([]);
  let roleLibraryDepartments = $state<Department[]>([]);
  let roleLibraryTeams = $state<HRTeamListItem[]>([]);
  let roleLibraryCostCenters = $state<CostCenter[]>([]);

  // Step 4: Phases & Files
  let phaseNames = $state<string[]>([]);
  let templates = $state<ProjectTemplateListItem[]>([]);
  let templateMode = $state(false);
  let selectedTemplateId = $state<string>("");
  let selectedTemplate = $state<ProjectTemplate | null>(null);
  let templatePhases = $state<EditablePhase[]>([]);
  let templateLoading = $state(false);
  let supportingFiles = $state<File[]>([]);
  let expandedPhaseIdx = $state<number | null>(null);

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<ProjectSetupConfigItem | null>(null);
  let detailLoading = $state(false);

  // Add team member drawer
  let teamMemberOpen = $state(false);
  let teamSaving = $state(false);
  let teamForm = $state(defaultTeamForm());
  let teamProjectId = $state<number | null>(null);

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      pipeline_source: "",
      name: "",
      project_type: "residential" as ProjectType,
      status: "planning",
      location: "",
      description: "",
      property: "" as string,
      gps_latitude: "",
      gps_longitude: "",
      spv_entity: "",
      land_status: "" as LandStatus | "",
      number_of_units: "",
      start_date: "",
      target_end_date: "",
      land_acquisition_date: "",
      permit_approval_date: "",
      construction_start_date: "",
      budget: "",
      target_irr: "",
      planned_phases: "3",
      survey_plan_ref: "",
      certificate_of_occupancy: "",
    };
  }

  function defaultTeamForm() {
    return {
      name: "",
      role: "other" as TeamMemberRole,
      access_level: "contributor" as TeamAccessLevel,
      email: "",
      phone: "",
      company: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  function devFillBasicInfo() {
    form = {
      ...form,
      name: "The Eko Zenith Towers",
      project_type: "mixed_use" as ProjectType,
      status: "planning",
      location: "Plot 12, Adeola Odeku Street, Victoria Island, Lagos",
      description: "35-storey mixed-use development — 18 floors Grade A office, 12 floors luxury residential, 5 floors retail/parking podium.",
      property: properties[0]?.id ? String(properties[0].id) : "",
      gps_latitude: "6.4281",
      gps_longitude: "3.4219",
      spv_entity: "Eko Zenith Holdings Ltd",
      land_status: "freehold" as LandStatus,
      start_date: "2026-09-01",
      target_end_date: "2029-03-31",
      land_acquisition_date: "2026-04-15",
      permit_approval_date: "2026-08-01",
      construction_start_date: "2026-09-15",
      budget: "12200000000",
      target_irr: "21.50",
      number_of_units: "180",
      planned_phases: "5",
      survey_plan_ref: "LSG/REG/2026/VI/0487",
      certificate_of_occupancy: "C of O — FCT/ABJ/2026/0891",
    };
  }

  function devFillOwnership() {
    ownershipRows = [
      { party_name: "Eko Zenith Holdings Ltd", ownership_percentage: "60" },
      { party_name: "Gulf Capital Partners", ownership_percentage: "25" },
      { party_name: "HNI Co-Investment Pool", ownership_percentage: "15" },
    ];
  }

  function devFillRoleLibrary() {
    const dept = roleLibraryDepartments[0];
    const cc = dept ? roleLibraryCostCenters.find(c => c.department === dept.id || c.department === null) : roleLibraryCostCenters[0];
    const team = dept ? roleLibraryTeams.find(t => t.department === dept.id) : roleLibraryTeams[0];
    roleLibraryRows = [
      {
        role: roleLibraryOptions[0]?.id ? String(roleLibraryOptions[0].id) : "",
        department: dept?.id ? String(dept.id) : "",
        cost_center: cc?.id ? String(cc.id) : "",
        team: team?.id ? String(team.id) : "",
        quantity: "3",
        employment_type: "full_time",
        level: "senior",
        criticality_score: "72",
      },
    ];
  }

  function devFillTeam() {
    teamRows = [
      { name: "Engr. Adewale Okonkwo", role: "project_manager", access_level: "full_access", email: "adewale@example.com", company: "" },
      { name: "Arc. Folake Balogun", role: "lead_architect", access_level: "contributor", email: "folake@designstudio.ng", company: "Balogun Design Studio" },
      { name: "Engr. Chidi Nwosu", role: "structural_engineer", access_level: "contributor", email: "chidi@structeng.ng", company: "Nwosu Structural Consultants" },
      { name: "Engr. Kemi Adeboye", role: "mep_consultant", access_level: "contributor", email: "kemi@mepconsult.ng", company: "Adeboye MEP Services" },
      { name: "QS Funke Adeyemi", role: "quantity_surveyor", access_level: "financial_edit", email: "funke@qs.ng", company: "Adeyemi QS Partnership" },
    ];
  }

  function devFillPhases() {
    phaseNames = ["Substructure & Piling", "Superstructure (Levels 1-15)", "Superstructure (Levels 16-35)", "MEP & Finishing", "External Works & Landscaping"];
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  let lookupsLoaded = false;

  async function fetchSetups() {
    loading = true;
    try {
      const [res] = await Promise.all([
        api.get<PaginatedResponse<ProjectSetupConfigItem>>("/projects/setup/", { page_size: "100" }),
      ]);
      configs = res.results;
    } catch { configs = []; }
    loading = false;
  }

  async function fetchLookups() {
    if (lookupsLoaded) return;
    const results = await Promise.allSettled([
      api.get<PaginatedResponse<PipelineOpportunityListItem>>("/projects/pipeline/", { page_size: "100", stage: "approved" }),
      api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" }),
      api.get<PaginatedResponse<HRPositionRoleListItem>>("/hr/position-roles/", { page_size: "200", is_active: "true" }),
      api.get<PaginatedResponse<Department>>("/settings/departments/", { page_size: "500" }),
      api.get<PaginatedResponse<HRTeamListItem>>("/hr/teams/", { page_size: "500", is_active: "true" }),
      api.get<PaginatedResponse<CostCenter>>("/settings/cost-centers/", { page_size: "500", is_active: "true" }),
      api.get<PaginatedResponse<ProjectTemplateListItem>>("/settings/project-templates/", { is_active: "true", page_size: "100" }),
    ]);
    const settled = <T,>(r: PromiseSettledResult<PaginatedResponse<T>>): T[] =>
      r.status === "fulfilled" ? r.value.results : [];
    pipelines = settled<PipelineOpportunityListItem>(results[0] as PromiseSettledResult<PaginatedResponse<PipelineOpportunityListItem>>);
    properties = settled<PropertyListItem>(results[1] as PromiseSettledResult<PaginatedResponse<PropertyListItem>>);
    roleLibraryOptions = settled<HRPositionRoleListItem>(results[2] as PromiseSettledResult<PaginatedResponse<HRPositionRoleListItem>>);
    roleLibraryDepartments = settled<Department>(results[3] as PromiseSettledResult<PaginatedResponse<Department>>);
    roleLibraryTeams = settled<HRTeamListItem>(results[4] as PromiseSettledResult<PaginatedResponse<HRTeamListItem>>);
    roleLibraryCostCenters = settled<CostCenter>(results[5] as PromiseSettledResult<PaginatedResponse<CostCenter>>);
    templates = settled<ProjectTemplateListItem>(results[6] as PromiseSettledResult<PaginatedResponse<ProjectTemplateListItem>>);
    lookupsLoaded = true;
  }

  $effect(() => { fetchSetups(); fetchLookups(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  function startWizard() {
    form = defaultForm();
    teamRows = [];
    phaseNames = [];
    ownershipRows = [emptyOwnershipRow()];
    roleLibraryRows = [];
    templateMode = false;
    selectedTemplateId = "";
    selectedTemplate = null;
    templatePhases = [];
    supportingFiles = [];
    expandedPhaseIdx = null;
    wizardStep = 1;
    wizardOpen = true;
  }

  // Pipeline auto-fill
  function onPipelineSelect() {
    if (!form.pipeline_source) return;
    const pip = pipelines.find(p => String(p.id) === form.pipeline_source);
    if (pip) {
      form.name = form.name || pip.name;
      form.location = form.location || pip.location;
      form.description = form.description || pip.description;
      form.budget = form.budget || pip.estimated_cost;
      form.number_of_units = form.number_of_units || String(pip.number_of_units);
      form.project_type = pip.development_type === "mixed_use" ? "mixed_use" : pip.development_type === "commercial" ? "commercial" : pip.development_type === "infrastructure" ? "infrastructure" : "residential";
    }
  }

  // Wizard navigation
  function nextStep() {
    if (wizardStep === 1 && !form.name.trim()) { toast.error("Required", "Project name is required."); return; }
    if (wizardStep < 4) wizardStep++;
  }
  function prevStep() { if (wizardStep > 1) wizardStep--; }

  // Phase names from count (only used in manual mode)
  $effect(() => {
    if (templateMode) return;
    const count = Number(form.planned_phases) || 3;
    if (phaseNames.length !== count) {
      const existing = [...phaseNames];
      phaseNames = Array.from({ length: count }, (_, i) => existing[i] || `Phase ${i + 1}`);
    }
  });

  // ── Ownership helpers ──────────────────────────────────────────────────
  function addOwnershipRow() { ownershipRows = [...ownershipRows, emptyOwnershipRow()]; }
  function removeOwnershipRow(idx: number) {
    if (ownershipRows.length <= 1) return;
    ownershipRows = ownershipRows.filter((_, i) => i !== idx);
  }
  const ownershipTotal = $derived.by(() =>
    ownershipRows.reduce((sum, r) => {
      const pct = Number(r.ownership_percentage);
      return Number.isFinite(pct) ? sum + pct : sum;
    }, 0),
  );
  function buildOwnershipPayload() {
    return ownershipRows
      .map((row, idx) => ({
        party_name: row.party_name.trim(),
        ownership_percentage: row.ownership_percentage,
        sort_order: idx,
      }))
      .filter((row) => row.party_name || row.ownership_percentage);
  }

  // ── Role library helpers ───────────────────────────────────────────────
  function addRoleLibraryRow() { roleLibraryRows = [...roleLibraryRows, emptyRoleLibraryRow()]; }
  function removeRoleLibraryRow(idx: number) {
    roleLibraryRows = roleLibraryRows.filter((_, i) => i !== idx);
  }
  function roleLibraryTeamOptions(departmentId: string) {
    if (!departmentId) return roleLibraryTeams;
    const id = Number(departmentId);
    return roleLibraryTeams.filter(t => t.department === id);
  }
  function roleLibraryCostCenterOptions(departmentId: string) {
    if (!departmentId) return roleLibraryCostCenters;
    const id = Number(departmentId);
    return roleLibraryCostCenters.filter(c => c.department === null || c.department === id);
  }
  function buildRoleLibraryPayload() {
    return roleLibraryRows
      .map((row) => ({
        role: row.role ? Number(row.role) : null,
        department: row.department ? Number(row.department) : null,
        cost_center: row.cost_center ? Number(row.cost_center) : null,
        team: row.team ? Number(row.team) : null,
        quantity: Number(row.quantity),
        employment_type: row.employment_type,
        level: row.level,
        criticality_score: Number(row.criticality_score || "0"),
      }))
      .filter((row) => row.role && row.department && row.cost_center && Number.isFinite(row.quantity) && row.quantity > 0);
  }

  // ── Supporting files helpers ───────────────────────────────────────────
  function onSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const newFiles = Array.from(input.files ?? []);
    supportingFiles = [...supportingFiles, ...newFiles];
    input.value = ""; // allow re-selecting the same file
  }
  function removeSupportingFile(idx: number) {
    supportingFiles = supportingFiles.filter((_, i) => i !== idx);
  }

  // ── Template phase helpers ─────────────────────────────────────────────
  async function loadTemplate(id: string) {
    if (!id) { selectedTemplate = null; templatePhases = []; return; }
    templateLoading = true;
    try {
      const t = await api.get<ProjectTemplate>(`/settings/project-templates/${id}/`);
      selectedTemplate = t;
      templatePhases = (t.phases ?? [])
        .slice()
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((p, i) => ({
          name: p.name,
          description: p.description,
          sort_order: i,
          duration_days: p.duration_days != null ? String(p.duration_days) : "",
          weight: String(p.weight),
          milestones: (p.milestones ?? [])
            .slice()
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((ms) => ({
              name: ms.name,
              description: ms.description,
              days_from_phase_start: ms.days_from_phase_start != null ? String(ms.days_from_phase_start) : "",
            })),
          required_documents: (p.required_documents ?? []).map((d) => ({
            name: d.name,
            category: d.category_display || d.category,
            description: d.description,
            is_mandatory: d.is_mandatory,
          })),
          compliance_checkpoints: (p.compliance_checkpoints ?? []).map((c) => ({
            name: c.name,
            description: c.description,
            regulatory_reference: c.regulatory_reference,
            is_mandatory: c.is_mandatory,
          })),
        }));
    } catch {
      toast.error("Template", "Could not load template details.");
    } finally {
      templateLoading = false;
    }
  }
  function addTemplatePhase() {
    templatePhases = [...templatePhases, {
      name: "", description: "", sort_order: templatePhases.length,
      duration_days: "", weight: "",
      milestones: [], required_documents: [], compliance_checkpoints: [],
    }];
  }
  function removeTemplatePhase(idx: number) {
    templatePhases = templatePhases.filter((_, i) => i !== idx).map((p, i) => ({ ...p, sort_order: i }));
  }

  async function submitWizard() {
    saving = true;
    let projectId: number | null = null;
    let setupId: number | null = null;
    try {
      // ── 1. Create project + setup config (initialize) ────────────────
      const res = await api.post<ProjectSetupConfigItem>("/projects/setup/initialize/", {
        pipeline_source: form.pipeline_source ? Number(form.pipeline_source) : null,
        name: form.name,
        project_type: form.project_type,
        location: form.location,
        description: form.description,
        start_date: form.start_date || null,
        target_end_date: form.target_end_date || null,
        budget: form.budget || null,
        number_of_units: form.number_of_units ? Number(form.number_of_units) : null,
        planned_phases: Number(form.planned_phases) || 3,
        survey_plan_ref: form.survey_plan_ref,
        certificate_of_occupancy: form.certificate_of_occupancy,
      });
      projectId = res.project;
      setupId = res.id;

      // ── 2. PATCH the project with the rest of the fields ─────────────
      try {
        await api.patch(`/projects/${projectId}/`, {
          status: form.status,
          property: form.property ? Number(form.property) : null,
          gps_latitude: form.gps_latitude === "" ? null : Number(form.gps_latitude),
          gps_longitude: form.gps_longitude === "" ? null : Number(form.gps_longitude),
          spv_entity: form.spv_entity,
          land_status: form.land_status || "",
          land_acquisition_date: form.land_acquisition_date || null,
          permit_approval_date: form.permit_approval_date || null,
          construction_start_date: form.construction_start_date || null,
          target_irr: form.target_irr || null,
          ownership_allocations: buildOwnershipPayload(),
        });
      } catch (err) {
        console.error("[setup] PATCH project failed:", err);
        toast.error("Partial save", "Project was created but some extended fields failed to save.");
      }

      // ── 3. Upload supporting files ───────────────────────────────────
      if (supportingFiles.length > 0) {
        const failed: string[] = [];
        for (const file of supportingFiles) {
          try {
            const fd = new FormData();
            fd.append("file", file);
            fd.append("caption", file.name);
            await api.upload(`/projects/${projectId}/upload-supporting-file/`, fd);
          } catch {
            failed.push(file.name || "Unnamed file");
          }
        }
        if (failed.length > 0) {
          toast.error("Files not uploaded", `${failed.length} file(s) could not be uploaded.`);
        }
      }

      // ── 4. Create team members ───────────────────────────────────────
      for (const member of teamRows) {
        if (!member.name.trim()) continue;
        try { await api.post("/projects/team-members/", { project: projectId, ...member }); }
        catch (err) { console.error("[setup] team member failed:", err); }
      }

      // ── 5. Provision role library ────────────────────────────────────
      const roleEntries = buildRoleLibraryPayload();
      if (roleEntries.length > 0) {
        try {
          const r = await api.post<{ created_count: number }>(
            `/projects/${projectId}/provision-role-library/`,
            { append_project_name: true, entries: roleEntries },
          );
          if (r.created_count > 0) {
            toast.success("Role library applied", `${r.created_count} position slot(s) provisioned.`);
          }
        } catch (err) {
          console.error("[setup] role library failed:", err);
          toast.error("Role library", "Project was created but role library provisioning failed.");
        }
      }

      // ── 6. Create phases ─────────────────────────────────────────────
      if (templateMode && templatePhases.length > 0) {
        for (const phase of templatePhases) {
          if (!phase.name.trim()) continue;
          try {
            const phaseRes = await api.post<{ id: number }>(`/projects/${projectId}/phases/`, {
              name: phase.name.trim(),
              description: phase.description.trim(),
              sort_order: phase.sort_order,
              weight: phase.weight ? Number(phase.weight) : 0,
              status: "not_started",
              estimated_duration_days: phase.duration_days ? Number(phase.duration_days) : null,
              deliverables: phase.required_documents
                .filter(d => d.name.trim())
                .map(d => ({ name: d.name.trim(), description: d.description.trim(), is_mandatory: d.is_mandatory })),
              exit_criteria: phase.compliance_checkpoints
                .filter(c => c.name.trim())
                .map(c => ({ criterion: c.name.trim(), verification_method: c.regulatory_reference.trim() || c.description.trim() })),
            });
            for (const ms of phase.milestones) {
              if (!ms.name.trim()) continue;
              try {
                await api.post(`/projects/${projectId}/phases/${phaseRes.id}/milestones/`, {
                  name: ms.name.trim(),
                  typical_offset_days: ms.days_from_phase_start ? Number(ms.days_from_phase_start) : null,
                });
              } catch (err) { console.error("[setup] milestone failed:", err); }
            }
          } catch (err) { console.error("[setup] phase failed:", err); }
        }
      } else {
        for (let i = 0; i < phaseNames.length; i++) {
          if (!phaseNames[i].trim()) continue;
          try {
            await api.post(`/projects/${projectId}/phases/`, {
              name: phaseNames[i],
              sort_order: i,
              status: "not_started",
              weight: Math.round(100 / phaseNames.length),
            });
          } catch (err) { console.error("[setup] phase failed:", err); }
        }
      }

      // ── 7. Mark setup complete ───────────────────────────────────────
      try {
        await api.patch(`/projects/setup/${setupId}/`, {
          current_step: "completed",
          is_complete: true,
        });
      } catch (err) { console.error("[setup] mark complete failed:", err); }

      toast.success("Project initialized", `"${form.name}" is ready for execution.`);
      wizardOpen = false;
      await fetchSetups();
      // ── 8. Navigate to the new project ───────────────────────────────
      void goto(`/projects/${projectId}`);
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Setup failed.") : "Setup failed.";
      toast.error("Setup failed", msg);
    } finally { saving = false; }
  }

  async function saveTeamMember(e: Event) {
    e.preventDefault();
    if (!teamProjectId || !teamForm.name.trim()) return;
    teamSaving = true;
    try {
      await api.post("/projects/team-members/", { project: teamProjectId, ...teamForm });
      toast.success("Member added", "");
      teamMemberOpen = false;
      teamForm = defaultTeamForm();
      if (detail) { detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${detail.id}/`); }
    } catch { toast.error("Failed", "Could not add team member."); }
    teamSaving = false;
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function stepColor(step: SetupStep, current: SetupStep): string {
    const order: SetupStep[] = ["basic_info", "team_allocation", "phase_definition", "boq_baseline", "completed"];
    const ci = order.indexOf(current);
    const si = order.indexOf(step);
    if (si < ci || current === "completed") return "bg-emerald-500 text-white";
    if (si === ci) return "bg-neutral-900 text-white";
    return "bg-neutral-200 text-neutral-400";
  }

  const STEPS: { key: SetupStep; label: string }[] = [
    { key: "basic_info", label: "Basic Info" },
    { key: "team_allocation", label: "Team" },
    { key: "phase_definition", label: "Phases" },
    { key: "boq_baseline", label: "BoQ" },
    { key: "completed", label: "Complete" },
  ];

  function stepTargetHref(key: SetupStep, projectId: number): string | null {
    switch (key) {
      case "basic_info":
        return `/projects/${projectId}/edit`;
      case "team_allocation":
        return `/projects/${projectId}`;
      case "phase_definition":
        return `/projects/${projectId}`;
      case "boq_baseline":
        return `/projects/budget-cost`;
      case "completed":
        return null;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
        <a href="/projects" class="hover:text-indigo-700">Projects</a>
        <span class="text-neutral-300"> › </span>
        <span class="text-indigo-600">Kickoff</span>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Project Kickoff</h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">
        Projects that have just been committed from a Blueprint. Walk each one through the remaining setup — team, property, ownership, BoQ baseline — before it moves into formal execution.
      </p>
    </div>
    <a href="/projects/blueprints" class="rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Open Blueprints</a>
  </div>

  <!-- Existing setups -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if configs.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center">
      <p class="text-sm font-semibold text-neutral-800">No kickoffs in flight</p>
      <p class="mt-2 text-sm text-neutral-500 max-w-md mx-auto">Commit a Blueprint to begin a project. Once committed, the project will appear here so you can finalize team, ownership, and BoQ baseline.</p>
      <a href="/projects/blueprints" class="mt-4 inline-block rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800">Open Blueprints</a>
    </div>
  {:else}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each configs as cfg}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(cfg.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{cfg.project_name}</p>
              {#if cfg.pipeline_source_ref}
                <p class="text-[10px] text-indigo-500 mt-0.5">From: {cfg.pipeline_source_ref}</p>
              {/if}
            </div>
            <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold {cfg.is_complete ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
              {cfg.is_complete ? "Complete" : cfg.current_step_display}
            </span>
          </div>

          <!-- Progress steps -->
          <div class="flex items-center gap-1 mb-3">
            {#each STEPS as step, idx}
              <div class="flex-1 h-1.5 rounded-full {stepColor(step.key, cfg.current_step)}"></div>
            {/each}
          </div>

          <div class="flex items-center justify-between text-xs text-neutral-500">
            <span>{cfg.planned_phases} phases</span>
            <span>{cfg.team_members.length} team members</span>
            <span>{fmtDate(cfg.created_at)}</span>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Project Kickoff" subtitle={detail?.project_name ?? ""} width="max-w-xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Progress — click a step pill to jump to its data-entry page -->
      <div>
        <div class="flex items-center gap-2">
          {#each STEPS as step, idx}
            {@const targetHref = stepTargetHref(step.key, detail.project)}
            <div class="flex items-center gap-1">
              {#if targetHref}
                <a href={targetHref} class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-transform hover:scale-110 {stepColor(step.key, detail.current_step)}" title={step.label}>{idx + 1}</a>
              {:else}
                <div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold {stepColor(step.key, detail.current_step)}" title={step.label}>{idx + 1}</div>
              {/if}
              {#if idx < STEPS.length - 1}<div class="w-4 h-0.5 {stepColor(step.key, detail.current_step)}"></div>{/if}
            </div>
          {/each}
        </div>
        <div class="mt-2 grid grid-cols-5 gap-2 text-[9px] uppercase tracking-wider text-neutral-400 text-center">
          {#each STEPS as step}
            <span class="truncate">{step.label}</span>
          {/each}
        </div>
        <p class="mt-3 text-xs text-neutral-500">Click a step to jump to its data-entry page.</p>
      </div>

      {#if detail.pipeline_source_ref}
        <div class="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Pipeline Source</p>
          <p class="text-sm font-semibold text-indigo-900 mt-0.5">{detail.pipeline_source_ref} — {detail.pipeline_source_name}</p>
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Planned Phases</p><p class="text-sm text-neutral-900">{detail.planned_phases}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">BoQ Initialized</p><p class="text-sm text-neutral-900">{detail.boq_initialized ? "Yes" : "No"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Survey Plan</p><p class="text-sm text-neutral-900">{detail.survey_plan_ref || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">C of O</p><p class="text-sm text-neutral-900">{detail.certificate_of_occupancy || "--"}</p></div>
      </div>

      <!-- Team Members -->
      <div class="border-t border-neutral-200 pt-4">
        <div class="flex items-center justify-between mb-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Team ({detail.team_members.length})</p>
          <button onclick={() => { teamProjectId = detail!.project; teamForm = defaultTeamForm(); teamMemberOpen = true; }} class="rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200">+ Add</button>
        </div>
        {#if detail.team_members.length > 0}
          <div class="space-y-2">
            {#each detail.team_members as member}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3 flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-neutral-900">{member.name}</p>
                  <p class="text-xs text-neutral-500">{member.role_display}{member.company ? ` — ${member.company}` : ""}</p>
                </div>
                <span class="rounded-full px-2 py-0.5 text-[9px] font-semibold bg-neutral-100 text-neutral-600">{member.access_level_display}</span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="text-sm text-neutral-400 text-center py-4">No team members assigned.</p>
        {/if}
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      <!-- Management Controls -->
      <div class="border-t border-neutral-200 pt-4 space-y-3">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Management Controls</p>

        <div class="grid grid-cols-2 gap-2">
          {#if !detail.is_complete}
            <button
              onclick={async () => {
                try {
                  await api.patch(`/projects/setup/${detail!.id}/`, { current_step: "completed", is_complete: true });
                  toast.success("Setup completed", "Project marked as setup complete.");
                  detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${detail!.id}/`);
                  await fetchSetups();
                } catch { toast.error("Failed", "Could not mark as complete."); }
              }}
              class="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
            >Mark Complete</button>
          {:else}
            <button
              onclick={async () => {
                try {
                  await api.patch(`/projects/setup/${detail!.id}/`, { current_step: "basic_info", is_complete: false });
                  toast.success("Setup re-opened", "Project setup has been re-opened for editing.");
                  detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${detail!.id}/`);
                  await fetchSetups();
                } catch { toast.error("Failed", "Could not re-open setup."); }
              }}
              class="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100"
            >Re-open Setup</button>
          {/if}

          <select
            value={detail.current_step}
            onchange={async (e) => {
              const step = (e.target as HTMLSelectElement).value;
              try {
                await api.patch(`/projects/setup/${detail!.id}/`, { current_step: step });
                detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${detail!.id}/`);
                await fetchSetups();
              } catch { toast.error("Failed", "Could not update step."); }
            }}
            class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            {#each STEPS as step}
              <option value={step.key}>{step.label}</option>
            {/each}
            <option value="completed">Completed</option>
          </select>
        </div>

        <!-- Project Status -->
        <div>
          <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Project Status</p>
          <select
            value={detail.project_status || "planning"}
            onchange={async (e) => {
              const newStatus = (e.target as HTMLSelectElement).value;
              try {
                await api.patch(`/projects/${detail!.project}/`, { status: newStatus });
                toast.success("Status updated", `Project status changed to ${newStatus}.`);
                detail = await api.get<ProjectSetupConfigItem>(`/projects/setup/${detail!.id}/`);
              } catch { toast.error("Failed", "Could not update project status."); }
            }}
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="planning">Planning</option>
            <option value="active">Active</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <!-- Danger Zone -->
        <div class="rounded-lg border border-red-200 bg-red-50 p-3">
          <p class="text-[10px] font-semibold uppercase text-red-700 mb-2">Danger Zone</p>
          <button
            onclick={async () => {
              if (!confirm("Are you sure you want to archive this setup? This cannot be undone.")) return;
              try {
                await api.delete(`/projects/setup/${detail!.id}/`);
                toast.success("Archived", "Project setup has been removed.");
                detailOpen = false;
                detail = null;
                await fetchSetups();
              } catch { toast.error("Failed", "Could not archive setup."); }
            }}
            class="rounded-lg border border-red-300 bg-white px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
          >Delete Setup Record</button>
        </div>
      </div>
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ WIZARD DRAWER ═══════════ -->
<DrawerShell open={wizardOpen} title="Initialize Project" subtitle="Step {wizardStep} of 4" width="max-w-2xl" onclose={() => (wizardOpen = false)}>
  <div class="p-6">
    <!-- Step indicator -->
    <div class="flex items-center gap-2 mb-6">
      {#each [1, 2, 3, 4] as step}
        <div class="flex items-center gap-1 flex-1">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold {wizardStep >= step ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-400'}">{step}</div>
          <p class="text-[10px] font-medium {wizardStep >= step ? 'text-neutral-900' : 'text-neutral-400'}">{["Identity", "Ownership", "Team & Roles", "Phases & Files"][step - 1]}</p>
        </div>
      {/each}
    </div>

    <!-- Step 1: Identity & Schedule -->
    {#if wizardStep === 1}
      <div class="space-y-4">
        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Link from Pipeline</span>
          <select bind:value={form.pipeline_source} onchange={onPipelineSelect} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">None — start fresh</option>
            {#each pipelines as pip}
              <option value={String(pip.id)}>{pip.pipeline_ref} — {pip.name}</option>
            {/each}
          </select>
        </label>

        <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Project Name *</span><input bind:value={form.name} placeholder="e.g. The Eko Zenith Towers" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>

        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span><select bind:value={form.project_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="residential">Residential</option><option value="commercial">Commercial</option><option value="mixed_use">Mixed-Use</option><option value="infrastructure">Infrastructure</option>
          </select></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span><select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="planning">Planning</option><option value="in_progress">In Progress</option><option value="on_hold">On Hold</option><option value="completed">Completed</option>
          </select></label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Units</span><input type="number" bind:value={form.number_of_units} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Status</span><select bind:value={form.land_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">(unspecified)</option><option value="freehold">Freehold</option><option value="leasehold">Leasehold</option><option value="under_contract">Under Contract</option><option value="to_acquire">To Acquire</option><option value="joint_venture">Joint Venture</option>
          </select></label>
        </div>

        <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Linked Property</span>
          <select bind:value={form.property} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">— Not linked —</option>
            {#each properties as prop}
              <option value={String(prop.id)}>{prop.name}</option>
            {/each}
          </select>
        </label>

        <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={form.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>

        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">GPS Latitude</span><input type="number" step="0.0000001" bind:value={form.gps_latitude} placeholder="-90 to 90" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">GPS Longitude</span><input type="number" step="0.0000001" bind:value={form.gps_longitude} placeholder="-180 to 180" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        </div>

        <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">SPV / Entity</span><input bind:value={form.spv_entity} placeholder="Special Purpose Vehicle name" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>

        <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

        <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3 space-y-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Schedule</p>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Start Date</span><DateInput bind:value={form.start_date} /></label>
            <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Completion Target</span><DateInput bind:value={form.target_end_date} /></label>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Acquisition</span><DateInput bind:value={form.land_acquisition_date} /></label>
            <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Permit Approval</span><DateInput bind:value={form.permit_approval_date} /></label>
            <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Construction Start</span><DateInput bind:value={form.construction_start_date} /></label>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Budget</span><input type="number" step="0.01" bind:value={form.budget} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Target IRR (%)</span><input type="number" step="0.01" bind:value={form.target_irr} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Survey Plan Ref</span><input bind:value={form.survey_plan_ref} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">C of O Reference</span><input bind:value={form.certificate_of_occupancy} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        </div>
      </div>
    {/if}

    <!-- Step 2: Ownership -->
    {#if wizardStep === 2}
      <div class="space-y-3">
        <p class="text-xs text-neutral-500">Define the ownership split for this project. Percentages should total 100%.</p>
        {#each ownershipRows as row, idx}
          <div class="flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-neutral-200 text-neutral-600 text-xs font-bold flex items-center justify-center shrink-0">{idx + 1}</span>
            <input bind:value={row.party_name} placeholder="Party / Entity name" class="flex-1 rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
            <div class="relative">
              <input type="number" step="0.01" min="0" max="100" bind:value={row.ownership_percentage} placeholder="0.00" class="w-28 rounded-md border border-neutral-200 px-3 py-1.5 text-sm text-right pr-7" />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-400">%</span>
            </div>
            <button onclick={() => removeOwnershipRow(idx)} disabled={ownershipRows.length <= 1} class="text-neutral-400 hover:text-red-500 text-xs disabled:opacity-30 disabled:cursor-not-allowed px-1">X</button>
          </div>
        {/each}
        <button onclick={addOwnershipRow} class="w-full rounded-lg border border-dashed border-neutral-300 py-2 text-xs font-medium text-neutral-500 hover:border-neutral-400 hover:text-neutral-700">+ Add Allocation</button>

        <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2 text-xs">
          <span class="text-neutral-500">Total allocated</span>
          <span class="font-bold tabular-nums {Math.abs(ownershipTotal - 100) < 0.01 ? 'text-emerald-700' : ownershipTotal > 0 ? 'text-amber-700' : 'text-neutral-400'}">
            {ownershipTotal.toFixed(2)}%
          </span>
        </div>
        {#if ownershipTotal > 0 && Math.abs(ownershipTotal - 100) >= 0.01}
          <p class="text-[11px] text-amber-700">Allocations don't total 100% — you can still save and adjust later.</p>
        {/if}
      </div>
    {/if}

    <!-- Step 3: Team & Roles -->
    {#if wizardStep === 3}
      <div class="space-y-6">
        <div class="space-y-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Team Members</p>
          <p class="text-xs text-neutral-500">Assign the project team. You can add more members later.</p>
          {#each teamRows as row, idx}
            <div class="rounded-lg border border-neutral-200 p-3 space-y-2 relative">
              <button onclick={() => { teamRows = teamRows.filter((_, i) => i !== idx); }} class="absolute top-2 right-2 text-neutral-400 hover:text-red-500 text-xs">X</button>
              <input bind:value={row.name} placeholder="Full name" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
              <div class="grid grid-cols-2 gap-2">
                <select bind:value={row.role} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="project_manager">Project Manager</option><option value="lead_architect">Lead Architect</option><option value="structural_engineer">Structural Engineer</option><option value="mep_consultant">MEP Consultant</option><option value="quantity_surveyor">Quantity Surveyor</option><option value="site_engineer">Site Engineer</option><option value="safety_officer">Safety Officer</option><option value="project_director">Project Director</option><option value="legal_counsel">Legal Counsel</option><option value="finance_controller">Finance Controller</option><option value="other">Other</option>
                </select>
                <select bind:value={row.access_level} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="read_only">Read Only</option><option value="contributor">Contributor</option><option value="financial_edit">Financial Edit</option><option value="full_access">Full Access</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <input bind:value={row.email} placeholder="Email" class="rounded-md border border-neutral-200 px-2 py-1.5 text-xs" />
                <input bind:value={row.company} placeholder="Company (if external)" class="rounded-md border border-neutral-200 px-2 py-1.5 text-xs" />
              </div>
            </div>
          {/each}
          <button onclick={() => { teamRows = [...teamRows, { name: "", role: "other", access_level: "contributor", email: "", company: "" }]; }} class="w-full rounded-lg border border-dashed border-neutral-300 py-2 text-xs font-medium text-neutral-500 hover:border-neutral-400 hover:text-neutral-700">+ Add Team Member</button>
        </div>

        <div class="space-y-3 border-t border-neutral-100 pt-5">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Role Library Provisioning</p>
          <p class="text-xs text-neutral-500">Optionally provision HR position slots for this project from the role library.</p>
          {#each roleLibraryRows as row, idx}
            <div class="rounded-lg border border-neutral-200 p-3 space-y-2 relative">
              <button onclick={() => removeRoleLibraryRow(idx)} class="absolute top-2 right-2 text-neutral-400 hover:text-red-500 text-xs">X</button>
              <div class="grid grid-cols-2 gap-2">
                <select bind:value={row.role} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="">— Role —</option>
                  {#each roleLibraryOptions as r}<option value={String(r.id)}>{r.name}</option>{/each}
                </select>
                <select bind:value={row.department} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="">— Department —</option>
                  {#each roleLibraryDepartments as d}<option value={String(d.id)}>{d.name}</option>{/each}
                </select>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <select bind:value={row.team} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="">— Team —</option>
                  {#each roleLibraryTeamOptions(row.department) as t}<option value={String(t.id)}>{t.name}</option>{/each}
                </select>
                <select bind:value={row.cost_center} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="">— Cost Center —</option>
                  {#each roleLibraryCostCenterOptions(row.department) as c}<option value={String(c.id)}>{c.code} — {c.name}</option>{/each}
                </select>
              </div>
              <div class="grid grid-cols-4 gap-2">
                <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Qty</span><input type="number" min="1" bind:value={row.quantity} class="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs" /></label>
                <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Type</span><select bind:value={row.employment_type} class="w-full rounded-md border border-neutral-200 bg-white px-1 py-1 text-xs">
                  <option value="full_time">Full-Time</option><option value="part_time">Part-Time</option><option value="contract">Contract</option><option value="temporary">Temporary</option><option value="intern">Intern</option>
                </select></label>
                <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Level</span><select bind:value={row.level} class="w-full rounded-md border border-neutral-200 bg-white px-1 py-1 text-xs">
                  <option value="intern">Intern</option><option value="junior">Junior</option><option value="mid">Mid</option><option value="senior">Senior</option><option value="lead">Lead</option><option value="manager">Manager</option><option value="director">Director</option><option value="vp">VP</option><option value="c_suite">C-Suite</option>
                </select></label>
                <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Criticality</span><input type="number" min="0" max="100" bind:value={row.criticality_score} class="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs" /></label>
              </div>
            </div>
          {/each}
          <button onclick={addRoleLibraryRow} class="w-full rounded-lg border border-dashed border-neutral-300 py-2 text-xs font-medium text-neutral-500 hover:border-neutral-400 hover:text-neutral-700">+ Add Role Library Row</button>
        </div>
      </div>
    {/if}

    <!-- Step 4: Phases & Files -->
    {#if wizardStep === 4}
      <div class="space-y-6">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Phases</p>
            <label class="inline-flex items-center gap-2 text-xs text-neutral-600">
              <input type="checkbox" bind:checked={templateMode} class="rounded border-neutral-300" />
              Import from template
            </label>
          </div>

          {#if templateMode}
            <div class="space-y-2">
              <select bind:value={selectedTemplateId} onchange={() => loadTemplate(selectedTemplateId)} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                <option value="">— Select template —</option>
                {#each templates as t}<option value={String(t.id)}>{t.name} ({t.phase_count} phase{t.phase_count === 1 ? "" : "s"})</option>{/each}
              </select>
              {#if templateLoading}
                <p class="text-xs text-neutral-500">Loading template…</p>
              {:else if selectedTemplate}
                <p class="text-[11px] text-neutral-500">{selectedTemplate.description}</p>
                {#each templatePhases as phase, pi}
                  <div class="rounded-lg border border-neutral-200">
                    <button type="button" onclick={() => (expandedPhaseIdx = expandedPhaseIdx === pi ? null : pi)} class="w-full flex items-center justify-between p-3 hover:bg-neutral-50">
                      <span class="text-sm font-semibold text-neutral-900">{pi + 1}. {phase.name || "(unnamed phase)"}</span>
                      <span class="text-xs text-neutral-400">{phase.milestones.length} ms · {phase.required_documents.length} docs · {phase.compliance_checkpoints.length} checks</span>
                    </button>
                    {#if expandedPhaseIdx === pi}
                      <div class="border-t border-neutral-100 p-3 space-y-3">
                        <input bind:value={phase.name} placeholder="Phase name" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
                        <textarea bind:value={phase.description} rows="2" placeholder="Description" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-xs"></textarea>
                        <div class="grid grid-cols-2 gap-2">
                          <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Duration (days)</span><input type="number" bind:value={phase.duration_days} class="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs" /></label>
                          <label class="text-xs"><span class="block text-[10px] text-neutral-500 mb-0.5">Weight</span><input type="number" bind:value={phase.weight} class="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs" /></label>
                        </div>
                        {#if phase.milestones.length > 0}
                          <div>
                            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-1">Milestones</p>
                            {#each phase.milestones as ms}<p class="text-xs text-neutral-600">• {ms.name}</p>{/each}
                          </div>
                        {/if}
                        {#if phase.required_documents.length > 0}
                          <div>
                            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-1">Required Documents</p>
                            {#each phase.required_documents as d}<p class="text-xs text-neutral-600">• {d.name}{d.is_mandatory ? " *" : ""}</p>{/each}
                          </div>
                        {/if}
                        {#if phase.compliance_checkpoints.length > 0}
                          <div>
                            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-1">Compliance Checkpoints</p>
                            {#each phase.compliance_checkpoints as c}<p class="text-xs text-neutral-600">• {c.name}{c.is_mandatory ? " *" : ""}</p>{/each}
                          </div>
                        {/if}
                        <button type="button" onclick={() => removeTemplatePhase(pi)} class="text-xs text-red-600 hover:text-red-700">Remove phase</button>
                      </div>
                    {/if}
                  </div>
                {/each}
                <button type="button" onclick={addTemplatePhase} class="w-full rounded-lg border border-dashed border-neutral-300 py-2 text-xs font-medium text-neutral-500 hover:border-neutral-400 hover:text-neutral-700">+ Add Phase</button>
              {/if}
            </div>
          {:else}
            <label class="block">
              <span class="mb-1 block text-xs font-semibold text-neutral-600">Number of Phases</span>
              <input type="number" min="1" max="10" bind:value={form.planned_phases} class="w-32 rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
            </label>
            <p class="text-xs text-neutral-500">Name each phase below. These will become your WBS structure.</p>
            {#each phaseNames as name, idx}
              <div class="flex items-center gap-2">
                <span class="w-6 h-6 rounded-full bg-neutral-200 text-neutral-600 text-xs font-bold flex items-center justify-center shrink-0">{idx + 1}</span>
                <input bind:value={phaseNames[idx]} class="flex-1 rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
              </div>
            {/each}
          {/if}
        </div>

        <div class="space-y-3 border-t border-neutral-100 pt-5">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Supporting Files</p>
          <p class="text-xs text-neutral-500">Optional. Attach project documents, plans, or references.</p>
          <input type="file" multiple onchange={onSupportingFilesSelected} class="block w-full text-xs text-neutral-600 file:mr-3 file:rounded-md file:border-0 file:bg-neutral-900 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-neutral-800" />
          {#if supportingFiles.length > 0}
            <div class="space-y-1.5">
              {#each supportingFiles as file, idx}
                <div class="flex items-center justify-between rounded-md bg-neutral-50 px-3 py-1.5 text-xs">
                  <span class="truncate text-neutral-700">{file.name}</span>
                  <button onclick={() => removeSupportingFile(idx)} class="text-neutral-400 hover:text-red-500 ml-2">X</button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Navigation -->
    <div class="flex items-center justify-between mt-6 pt-4 border-t border-neutral-100">
      <div>
        {#if wizardStep > 1}
          <button onclick={prevStep} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Back</button>
        {/if}
      </div>
      <div class="flex items-center gap-2">
        {#if isDev}
          <button onclick={() => {
            if (wizardStep === 1) devFillBasicInfo();
            else if (wizardStep === 2) devFillOwnership();
            else if (wizardStep === 3) { devFillTeam(); devFillRoleLibrary(); }
            else devFillPhases();
          }} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
        {/if}
        {#if wizardStep < 4}
          <button onclick={nextStep} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800">Next</button>
        {:else}
          <button onclick={submitWizard} disabled={saving} class="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">{saving ? "Creating..." : "Initialize Project"}</button>
        {/if}
      </div>
    </div>
  </div>
</DrawerShell>

<!-- ═══════════ ADD TEAM MEMBER DRAWER ═══════════ -->
<DrawerShell open={teamMemberOpen} title="Add Team Member" subtitle="" width="max-w-md" onclose={() => (teamMemberOpen = false)}>
  <form onsubmit={saveTeamMember} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Name *</span><input bind:value={teamForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Role</span><select bind:value={teamForm.role} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="project_manager">Project Manager</option><option value="lead_architect">Lead Architect</option><option value="structural_engineer">Structural Engineer</option><option value="mep_consultant">MEP Consultant</option><option value="quantity_surveyor">Quantity Surveyor</option><option value="site_engineer">Site Engineer</option><option value="safety_officer">Safety Officer</option><option value="other">Other</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Access</span><select bind:value={teamForm.access_level} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="read_only">Read Only</option><option value="contributor">Contributor</option><option value="financial_edit">Financial Edit</option><option value="full_access">Full Access</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Email</span><input type="email" bind:value={teamForm.email} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Company</span><input bind:value={teamForm.company} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (teamMemberOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button type="submit" disabled={teamSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{teamSaving ? "Saving..." : "Add Member"}</button>
    </div>
  </form>
</DrawerShell>
