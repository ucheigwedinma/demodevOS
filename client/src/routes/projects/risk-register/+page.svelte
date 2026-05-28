<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ProjectListItem,
    ProjectRiskRegisterEntry,
    ProjectRiskRegisterSummary,
    ProjectRiskStatus,
    ProjectRiskTreatment,
    RiskCategory,
    RiskMitigationRule,
    RiskScoreMatrix,
    RiskSeverity,
    RoleListItem,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type SeverityOption = { value: RiskSeverity; label: string };
  type StatusOption = { value: ProjectRiskStatus; label: string };
  type TreatmentOption = { value: ProjectRiskTreatment; label: string };
  type MatrixScaleEntry = { key: string; value: number; label: string };

  const DEFAULT_MATRIX = {
    likelihood: { very_low: 1, low: 2, medium: 3, high: 4, very_high: 5 },
    impact: { very_low: 1, low: 2, medium: 3, high: 4, very_high: 5 },
    thresholds: { low: 5, medium: 10, high: 15, critical: 20 },
  };

  const severityOptions: SeverityOption[] = [
    { value: "low", label: "Low" },
    { value: "medium", label: "Medium" },
    { value: "high", label: "High" },
    { value: "critical", label: "Critical" },
  ];

  const statusOptions: StatusOption[] = [
    { value: "open", label: "Open" },
    { value: "in_progress", label: "In Progress" },
    { value: "mitigated", label: "Mitigated" },
    { value: "accepted", label: "Accepted" },
    { value: "closed", label: "Closed" },
  ];

  const treatmentOptions: TreatmentOption[] = [
    { value: "mitigate", label: "Mitigate" },
    { value: "avoid", label: "Avoid" },
    { value: "transfer", label: "Transfer" },
    { value: "accept", label: "Accept" },
  ];

  const scaleLabel: Record<string, string> = {
    very_low: "Very Low",
    low: "Low",
    medium: "Medium",
    high: "High",
    very_high: "Very High",
  };

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  type RiskForm = ReturnType<typeof emptyForm>;
  const RISK_SAMPLES: Omit<RiskForm, "project" | "risk_category" | "owner_role">[] = [
    {
      title: "Foundation settlement exceeding design tolerances",
      description: "Monitoring data from inclinometers and settlement plates on Block B indicates 12mm differential settlement over 8 weeks — approaching the 15mm design limit. If trend continues, structural remediation may be required before superstructure progresses past Level 4.",
      likelihood_key: "medium",
      impact_key: "very_high",
      status: "open",
      treatment: "mitigate",
      mitigation_plan: "Commission independent geotechnical review of monitoring data. Increase settlement monitoring frequency from fortnightly to weekly. Prepare contingency design for micro-pile underpinning if settlement exceeds 15mm threshold.",
      mitigation_actions: "1. Geotechnical consultant engaged for independent review\n2. Weekly monitoring schedule in effect from 15 Mar\n3. Structural engineer preparing underpinning design as precautionary measure",
      contingency_plan: "If settlement exceeds 15mm: halt superstructure on affected grid lines, mobilise underpinning subcontractor (pre-qualified), implement temporary propping to transfer loads. Estimated delay: 4-6 weeks.",
      response_time_hours: "24",
      escalation_required: true,
      identified_on: new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10),
      target_resolution_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      last_reviewed_on: new Date().toISOString().slice(0, 10),
    },
    {
      title: "Supply chain disruption — reinforcement steel delivery",
      description: "Primary rebar supplier has notified a 6-week delay on T25 and T32 bar due to mill production issues. Current site stock covers approximately 2 weeks of planned consumption. Delay would impact critical path for podium slab and transfer beams.",
      likelihood_key: "high",
      impact_key: "high",
      status: "in_progress",
      treatment: "mitigate",
      mitigation_plan: "Activate secondary supplier agreements. Evaluate alternative bar sizes with structural engineer approval. Pre-order long-lead items for next 3 months. Consider coupler splices to reduce waste and extend stock.",
      mitigation_actions: "1. RFQ issued to 3 alternative mills\n2. Structural engineer reviewing equivalent bar substitution options\n3. Procurement team expediting secondary supplier qualification",
      contingency_plan: "Re-sequence construction programme to prioritise non-rebar-intensive activities (blockwork, MEP rough-ins) if supply gap exceeds 3 weeks. Programme float consumed: 2 weeks.",
      response_time_hours: "48",
      escalation_required: false,
      identified_on: new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10),
      target_resolution_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
      last_reviewed_on: new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10),
    },
    {
      title: "Crane oversail licence expiry — Tower Crane TC-02",
      description: "Oversail licence for TC-02 (serving Block A south wing) expires on 30 April. Neighbouring landowner has indicated they may not renew due to planned demolition works on their site. Loss of oversail would eliminate crane coverage for approximately 40% of Block A roof-level works.",
      likelihood_key: "high",
      impact_key: "medium",
      status: "open",
      treatment: "avoid",
      mitigation_plan: "Engage neighbouring landowner in early renewal negotiations. Prepare alternative lifting strategy using mobile crane and material hoists. Assess feasibility of repositioning TC-02 within site boundary to avoid oversail.",
      mitigation_actions: "1. Project director meeting with landowner scheduled for next week\n2. Crane consultant reviewing repositioning feasibility\n3. Mobile crane hire quotations obtained from 2 suppliers",
      contingency_plan: "Deploy 500T mobile crane for heavy lifts with pre-booked road closures. Install additional material hoist on south elevation. Accept 15% productivity reduction on roof-level works.",
      response_time_hours: "72",
      escalation_required: true,
      identified_on: new Date(Date.now() - 21 * 86400000).toISOString().slice(0, 10),
      target_resolution_date: new Date(Date.now() + 45 * 86400000).toISOString().slice(0, 10),
      last_reviewed_on: new Date(Date.now() - 5 * 86400000).toISOString().slice(0, 10),
    },
  ];

  let riskDevIdx = 0;

  function devFillRisk() {
    const sample = RISK_SAMPLES[riskDevIdx % RISK_SAMPLES.length];
    riskDevIdx++;
    form = {
      ...form,
      ...sample,
      project: form.project || (projects.length > 0 ? projects[0].id : 0),
    };
  }

  let loading = $state(true);
  let saving = $state(false);
  let projects = $state<ProjectListItem[]>([]);
  let categories = $state<RiskCategory[]>([]);
  let mitigationRules = $state<RiskMitigationRule[]>([]);
  let roles = $state<RoleListItem[]>([]);
  let matrix = $state<RiskScoreMatrix | null>(null);
  let risks = $state<ProjectRiskRegisterEntry[]>([]);
  let summary = $state<ProjectRiskRegisterSummary | null>(null);

  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let severityFilter = $state<"" | RiskSeverity>("");
  let statusFilter = $state<"" | ProjectRiskStatus>("");
  let categoryFilter = $state("");
  let currentPage = $state(1);
  let pageSize = $state(10);
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let fetchToken = 0;

  let showEditor = $state(false);
  let editingRiskId = $state<number | null>(null);
  let fieldErrors = $state<Record<string, string[]>>({});
  let riskSupportingFiles = $state<File[]>([]);
  let expandedRiskRowId = $state<number | null>(null);

  const todayIso = () => new Date().toISOString().slice(0, 10);
  const emptyForm = () => ({
    project: 0,
    title: "",
    description: "",
    risk_category: 0,
    likelihood_key: "medium",
    impact_key: "medium",
    status: "open" as ProjectRiskStatus,
    treatment: "mitigate" as ProjectRiskTreatment,
    mitigation_plan: "",
    mitigation_actions: "",
    contingency_plan: "",
    owner_role: 0,
    response_time_hours: "",
    escalation_required: false,
    identified_on: todayIso(),
    target_resolution_date: "",
    last_reviewed_on: "",
  });
  let form = $state(emptyForm());

  function severityClass(severity: RiskSeverity): string {
    const classes: Record<RiskSeverity, string> = {
      low: "bg-emerald-50 text-emerald-700 border-emerald-200",
      medium: "bg-amber-50 text-amber-700 border-amber-200",
      high: "bg-orange-50 text-orange-700 border-orange-200",
      critical: "bg-rose-50 text-rose-700 border-rose-200",
    };
    return classes[severity];
  }

  function statusClass(status: ProjectRiskStatus): string {
    const classes: Record<ProjectRiskStatus, string> = {
      open: "bg-sky-50 text-sky-700 border-sky-200",
      in_progress: "bg-indigo-50 text-indigo-700 border-indigo-200",
      mitigated: "bg-emerald-50 text-emerald-700 border-emerald-200",
      accepted: "bg-amber-50 text-amber-700 border-amber-200",
      closed: "bg-neutral-100 text-neutral-700 border-neutral-200",
    };
    return classes[status];
  }

  function toLabel(value: string): string {
    return scaleLabel[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function scoreToSeverity(score: number, thresholds: Record<string, number>): RiskSeverity {
    if (score <= (thresholds.low ?? DEFAULT_MATRIX.thresholds.low)) return "low";
    if (score <= (thresholds.medium ?? DEFAULT_MATRIX.thresholds.medium)) return "medium";
    if (score <= (thresholds.high ?? DEFAULT_MATRIX.thresholds.high)) return "high";
    return "critical";
  }

  function normalizeScale(raw: Record<string, number>, fallback: Record<string, number>): MatrixScaleEntry[] {
    const src = Object.keys(raw ?? {}).length > 0 ? raw : fallback;
    return Object.entries(src)
      .map(([key, value]) => ({ key, value: Number(value), label: toLabel(key) }))
      .sort((a, b) => a.value - b.value);
  }

  const likelihoodScale = $derived.by(() =>
    normalizeScale(matrix?.matrix_config.likelihood ?? {}, DEFAULT_MATRIX.likelihood),
  );
  const impactScale = $derived.by(() =>
    normalizeScale(matrix?.matrix_config.impact ?? {}, DEFAULT_MATRIX.impact),
  );
  const thresholds = $derived.by(
    () => matrix?.matrix_config.thresholds ?? DEFAULT_MATRIX.thresholds,
  );

  const previewScore = $derived.by(() => {
    const l = likelihoodScale.find((entry) => entry.key === form.likelihood_key)?.value ?? 0;
    const i = impactScale.find((entry) => entry.key === form.impact_key)?.value ?? 0;
    return l * i;
  });
  const previewSeverity = $derived.by(() => scoreToSeverity(previewScore, thresholds));

  const suggestedRule = $derived.by(() => {
    if (!form.risk_category) return null;
    return (
      mitigationRules.find(
        (rule) =>
          rule.is_active &&
          rule.risk_category === Number(form.risk_category) &&
          rule.severity === previewSeverity,
      ) ?? null
    );
  });

  const filteredRisks = $derived.by(() =>
    risks.filter((risk) => {
      if (projectFilter && String(risk.project) !== projectFilter) return false;
      if (severityFilter && risk.severity !== severityFilter) return false;
      if (statusFilter && risk.status !== statusFilter) return false;
      if (categoryFilter && String(risk.risk_category ?? "") !== categoryFilter) return false;

      if (!searchQuery) return true;
      const haystack =
        `${risk.title} ${risk.project_name} ${risk.risk_category_name ?? ""} ${risk.description} ${risk.mitigation_plan}`.toLowerCase();
      return haystack.includes(searchQuery.toLowerCase());
    }),
  );

  const totalPages = $derived(Math.max(1, Math.ceil(filteredRisks.length / pageSize)));
  const pagedRisks = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRisks.slice(start, start + pageSize);
  });

  const mitigationCoveragePct = $derived.by(() => {
    if (risks.length === 0) return 0;
    const complete = risks.filter(
      (risk) =>
        risk.mitigation_plan.trim().length > 0 &&
        (risk.owner_role !== null || risk.response_time_hours !== null),
    ).length;
    return Math.round((complete / risks.length) * 100);
  });

  function resetEditor() {
    showEditor = false;
    editingRiskId = null;
    fieldErrors = {};
    form = emptyForm();
    riskSupportingFiles = [];
    saving = false;
  }

  function openNewRisk() {
    fieldErrors = {};
    form = emptyForm();
    showEditor = true;
    editingRiskId = null;
  }

  function openEditRisk(risk: ProjectRiskRegisterEntry) {
    fieldErrors = {};
    editingRiskId = risk.id;
    form = {
      project: risk.project,
      title: risk.title,
      description: risk.description ?? "",
      risk_category: risk.risk_category ?? 0,
      likelihood_key: risk.likelihood_key,
      impact_key: risk.impact_key,
      status: risk.status,
      treatment: risk.treatment,
      mitigation_plan: risk.mitigation_plan ?? "",
      mitigation_actions: risk.mitigation_actions ?? "",
      contingency_plan: risk.contingency_plan ?? "",
      owner_role: risk.owner_role ?? 0,
      response_time_hours: risk.response_time_hours ? String(risk.response_time_hours) : "",
      escalation_required: risk.escalation_required,
      identified_on: risk.identified_on,
      target_resolution_date: risk.target_resolution_date ?? "",
      last_reviewed_on: risk.last_reviewed_on ?? "",
    };
    showEditor = true;
  }

  function applySuggestedRule() {
    if (!suggestedRule) return;
    form.owner_role = suggestedRule.assign_to_role ?? 0;
    form.response_time_hours = suggestedRule.response_time_hours
      ? String(suggestedRule.response_time_hours)
      : "";
    form.escalation_required = suggestedRule.escalation_required;
  }

  function buildSummaryFallback(rows: ProjectRiskRegisterEntry[]): ProjectRiskRegisterSummary {
    const bySeverity: Record<RiskSeverity, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    };
    const byStatus: Record<ProjectRiskStatus, number> = {
      open: 0,
      in_progress: 0,
      mitigated: 0,
      accepted: 0,
      closed: 0,
    };
    const today = todayIso();
    let overdue = 0;
    for (const risk of rows) {
      bySeverity[risk.severity] += 1;
      byStatus[risk.status] += 1;
      if (
        risk.target_resolution_date &&
        risk.target_resolution_date < today &&
        !["mitigated", "accepted", "closed"].includes(risk.status)
      ) {
        overdue += 1;
      }
    }
    return {
      total_risks: rows.length,
      high_and_critical_risks: bySeverity.high + bySeverity.critical,
      open_risks: byStatus.open + byStatus.in_progress,
      mitigated_risks: byStatus.mitigated + byStatus.closed,
      overdue_mitigation_risks: overdue,
      by_severity: bySeverity,
      by_status: byStatus,
    };
  }

  async function fetchAllPages<T>(endpoint: string, extraParams: Record<string, string> = {}): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;
    while (true) {
      const res = await api.get<PaginatedResponse<T>>(endpoint, {
        ...extraParams,
        page: String(page),
        page_size: "200",
      });
      rows.push(...res.results);
      if (!res.next || res.results.length === 0) break;
      page += 1;
    }
    return rows;
  }

  async function loadData() {
    loading = true;
    const token = ++fetchToken;
    try {
      const [loadedProjects, loadedCategories, loadedRules, loadedRoles, loadedMatrix, loadedRisks] =
        await Promise.all([
          fetchAllPages<ProjectListItem>("/projects/", { ordering: "name" }),
          fetchAllPages<RiskCategory>("/settings/risk-categories/", { is_active: "true", ordering: "name" }),
          fetchAllPages<RiskMitigationRule>("/settings/risk-mitigation-rules/", { is_active: "true" }),
          fetchAllPages<RoleListItem>("/settings/roles/"),
          api.get<RiskScoreMatrix>("/settings/risk-score-matrix/"),
          fetchAllPages<ProjectRiskRegisterEntry>("/projects/risk-register/", { ordering: "-created_at" }),
        ]);
      if (token !== fetchToken) return;

      projects = loadedProjects;
      categories = loadedCategories;
      mitigationRules = loadedRules;
      roles = loadedRoles;
      matrix = loadedMatrix;
      risks = loadedRisks;

      try {
        summary = await api.get<ProjectRiskRegisterSummary>("/projects/risk-register/summary/");
      } catch {
        summary = buildSummaryFallback(loadedRisks);
      }
    } catch {
      if (token !== fetchToken) return;
      toast.error("Load failed", "Could not load risk register data.");
      projects = [];
      categories = [];
      mitigationRules = [];
      roles = [];
      matrix = null;
      risks = [];
      summary = null;
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  async function saveRisk() {
    if (!form.project) {
      toast.error("Validation error", "Project is required.");
      return;
    }
    if (!form.title.trim()) {
      toast.error("Validation error", "Risk title is required.");
      return;
    }

    fieldErrors = {};
    saving = true;
    const payload = {
      project: form.project,
      title: form.title.trim(),
      description: form.description.trim(),
      risk_category: form.risk_category || null,
      likelihood_key: form.likelihood_key,
      impact_key: form.impact_key,
      status: form.status,
      treatment: form.treatment,
      mitigation_plan: form.mitigation_plan.trim(),
      mitigation_actions: form.mitigation_actions.trim(),
      contingency_plan: form.contingency_plan.trim(),
      owner_role: form.owner_role || null,
      response_time_hours: form.response_time_hours ? Number(form.response_time_hours) : null,
      escalation_required: form.escalation_required,
      identified_on: form.identified_on || todayIso(),
      target_resolution_date: form.target_resolution_date || null,
      last_reviewed_on: form.last_reviewed_on || null,
    };

    try {
      let savedRisk: ProjectRiskRegisterEntry;
      if (editingRiskId) {
        savedRisk = await api.patch<ProjectRiskRegisterEntry>(`/projects/risk-register/${editingRiskId}/`, payload);
        toast.success("Risk updated", "Risk register entry updated successfully.");
      } else {
        savedRisk = await api.post<ProjectRiskRegisterEntry>("/projects/risk-register/", payload);
        toast.success("Risk added", "Risk register entry created successfully.");
      }
      if (riskSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/risk-register/${savedRisk.id}/upload-supporting-file/`,
          riskSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Risk entry was saved, but supporting files failed to upload.",
          );
        }
      }
      resetEditor();
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error("Validation error", "Please correct the highlighted fields.");
      } else {
        toast.error("Save failed", "Could not save risk entry.");
      }
      saving = false;
    }
  }

  async function deleteRisk(risk: ProjectRiskRegisterEntry) {
    if (!confirm(`Delete "${risk.title}"?`)) return;
    try {
      await api.delete(`/projects/risk-register/${risk.id}/`);
      toast.success("Risk deleted", "Risk register entry removed.");
      if (expandedRiskRowId === risk.id) expandedRiskRowId = null;
      await loadData();
    } catch (err) {
      toast.error("Delete failed", apiErrorDetail(err, "Could not delete risk entry."));
    }
  }

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim();
      currentPage = 1;
    }, 250);
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function apiErrorDetail(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data["detail"];
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (firstField) return firstField;
    }
    return fallback;
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    return new Date(`${value}T00:00:00`).toLocaleDateString();
  }

  function toggleRiskRow(riskId: number) {
    expandedRiskRowId = expandedRiskRowId === riskId ? null : riskId;
  }

  function onSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    riskSupportingFiles = Array.from(input.files ?? []);
  }

  async function uploadSupportingFiles(endpoint: string, files: File[]): Promise<boolean> {
    try {
      for (const file of files) {
        const payload = new FormData();
        payload.append("file", file);
        payload.append("caption", file.name);
        await api.upload(endpoint, payload);
      }
      return true;
    } catch {
      return false;
    }
  }

  $effect(() => {
    void projectFilter;
    void severityFilter;
    void statusFilter;
    void categoryFilter;
    currentPage = 1;
  });

  $effect(() => {
    void pagedRisks;
    if (expandedRiskRowId !== null && !pagedRisks.some((risk) => risk.id === expandedRiskRowId)) {
      expandedRiskRowId = null;
    }
  });

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Risk Register</h1>
      <p class="text-sm text-neutral-500 mt-1">
        Central register for project risks with matrix-based scoring and mitigation ownership.
      </p>
    </div>
    <button
      onclick={openNewRisk}
      class="px-4 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-800 transition-colors"
    >
      + New Risk
    </button>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-5 gap-3">
    <div class="rounded-xl border-2 border-sky-200 bg-white p-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Total Risks</p>
      <p class="mt-2 text-2xl font-bold text-neutral-900">{summary?.total_risks ?? 0}</p>
    </div>
    <div class="rounded-xl border-2 border-rose-200 bg-white p-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">High/Critical</p>
      <p class="mt-2 text-2xl font-bold text-rose-700">{summary?.high_and_critical_risks ?? 0}</p>
    </div>
    <div class="rounded-xl border-2 border-indigo-200 bg-white p-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Open/In Progress</p>
      <p class="mt-2 text-2xl font-bold text-indigo-700">{summary?.open_risks ?? 0}</p>
    </div>
    <div class="rounded-xl border-2 border-emerald-200 bg-white p-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Mitigated/Closed</p>
      <p class="mt-2 text-2xl font-bold text-emerald-700">{summary?.mitigated_risks ?? 0}</p>
    </div>
    <div class="rounded-xl border-2 border-amber-200 bg-white p-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Mitigation Coverage</p>
      <p class="mt-2 text-2xl font-bold text-amber-700">{mitigationCoveragePct}%</p>
    </div>
  </div>

  <div class="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-6">
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Configured Risk Matrix</h2>
        <p class="text-xs text-neutral-500 mt-1">Scoring and thresholds from Settings → Risk Framework.</p>
      </div>
      <div class="p-5 overflow-x-auto">
        <table class="min-w-full text-xs border-separate border-spacing-1">
          <thead>
            <tr>
              <th class="px-2 py-2 text-left text-neutral-500">Impact \ Likelihood</th>
              {#each likelihoodScale as column}
                <th class="px-2 py-2 text-center text-neutral-500">{column.label}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each [...impactScale].reverse() as row}
              <tr>
                <td class="px-2 py-2 font-medium text-neutral-700">{row.label}</td>
                {#each likelihoodScale as column}
                  {@const cellScore = row.value * column.value}
                  {@const cellSeverity = scoreToSeverity(cellScore, thresholds)}
                  <td class="px-2 py-2 text-center rounded border font-semibold {severityClass(cellSeverity)}">
                    {cellScore}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Thresholds & Adoption</h2>
      <div class="mt-3 space-y-2">
        {#each severityOptions as severity}
          <div class="flex items-center justify-between rounded-lg border px-3 py-2 {severityClass(severity.value)}">
            <span class="text-xs font-semibold">{severity.label}</span>
            <span class="text-xs tabular-nums">
              {thresholds[severity.value] ?? "-"}
            </span>
          </div>
        {/each}
      </div>
      <div class="mt-5 rounded-lg bg-neutral-50 border border-neutral-200 p-3 space-y-1.5">
        <p class="text-xs text-neutral-500">Configured mitigation rules</p>
        <p class="text-lg font-semibold text-neutral-900">{mitigationRules.length}</p>
        <p class="text-xs text-neutral-500">Overdue mitigation risks: {summary?.overdue_mitigation_risks ?? 0}</p>
      </div>
    </div>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-4">
    <div class="grid grid-cols-1 lg:grid-cols-6 gap-3">
      <input
        type="text"
        placeholder="Search title, project, mitigation..."
        value={searchInput}
        oninput={onSearchInput}
        class="lg:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm">
        <option value="">All projects</option>
        {#each projects as project}
          <option value={String(project.id)}>{project.name}</option>
        {/each}
      </select>
      <select bind:value={severityFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm">
        <option value="">All severities</option>
        {#each severityOptions as severity}
          <option value={severity.value}>{severity.label}</option>
        {/each}
      </select>
      <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm">
        <option value="">All statuses</option>
        {#each statusOptions as status}
          <option value={status.value}>{status.label}</option>
        {/each}
      </select>
      <select bind:value={categoryFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm">
        <option value="">All categories</option>
        {#each categories as category}
          <option value={String(category.id)}>{category.name}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    <table class="min-w-full text-sm">
      <thead class="bg-neutral-50 border-b border-neutral-100">
        <tr class="text-xs text-neutral-500 uppercase tracking-wider">
          <th class="px-4 py-3 text-left">Risk</th>
          <th class="px-4 py-3 text-left">Project</th>
          <th class="px-4 py-3 text-left">Score</th>
          <th class="px-4 py-3 text-left">Severity</th>
          <th class="px-4 py-3 text-left">Status</th>
          <th class="px-4 py-3 text-left">Target Date</th>
          <th class="px-4 py-3 text-right">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-100">
        {#if loading}
          <tr><td colspan="7" class="px-4 py-8 text-center text-neutral-500">Loading risk register...</td></tr>
        {:else if pagedRisks.length === 0}
          <tr><td colspan="7" class="px-4 py-8 text-center text-neutral-500">No risks found for the selected filters.</td></tr>
        {:else}
          {#each pagedRisks as risk (risk.id)}
            <tr class="hover:bg-neutral-50">
              <td class="px-4 py-3 max-w-68">
                <p class="font-medium text-neutral-900 truncate">{risk.title}</p>
                <p class="text-[11px] mt-1 text-neutral-500 truncate">{risk.risk_category_name ?? "Uncategorized"}</p>
              </td>
              <td class="px-4 py-3 text-neutral-700">{risk.project_name}</td>
              <td class="px-4 py-3 font-semibold tabular-nums text-neutral-900">
                {risk.risk_score}
                <p class="text-[11px] mt-0.5 font-normal text-neutral-500">
                  L {risk.likelihood_score} x I {risk.impact_score}
                </p>
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {severityClass(risk.severity)}">
                  {risk.severity_display}
                </span>
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {statusClass(risk.status)}">
                  {risk.status_display}
                </span>
              </td>
              <td class="px-4 py-3 text-neutral-700">{fmtDate(risk.target_resolution_date)}</td>
              <td class="px-4 py-3 text-right">
                <div class="inline-flex items-center gap-1.5">
                  <button
                    type="button"
                    onclick={() => toggleRiskRow(risk.id)}
                    aria-expanded={expandedRiskRowId === risk.id}
                    aria-label={expandedRiskRowId === risk.id ? "Hide risk details" : "View risk details"}
                    title={expandedRiskRowId === risk.id ? "Hide details" : "View details"}
                    class={`inline-flex h-8 w-8 items-center justify-center rounded border transition-colors ${
                      expandedRiskRowId === risk.id
                        ? "border-neutral-900 bg-neutral-900 text-white"
                        : "border-neutral-200 text-neutral-700 hover:bg-neutral-100"
                    }`}
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5s8.268 2.943 9.542 7c-1.274 4.057-5.065 7-9.542 7s-8.268-2.943-9.542-7Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                  <button
                    onclick={() => openEditRisk(risk)}
                    aria-label="Edit risk"
                    title="Edit"
                    class="inline-flex h-8 w-8 items-center justify-center rounded border border-neutral-200 text-neutral-700 transition-colors hover:bg-neutral-100"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m15.232 5.232 3.536 3.536M4 20l4.5-1.125L18.768 8.607a2.5 2.5 0 1 0-3.536-3.536L4.964 15.339 4 20Z" />
                    </svg>
                  </button>
                  <button
                    onclick={() => deleteRisk(risk)}
                    aria-label="Delete risk"
                    title="Delete"
                    class="inline-flex h-8 w-8 items-center justify-center rounded border border-rose-200 text-rose-700 transition-colors hover:bg-rose-50"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 7h16M10 11v6m4-6v6M9 4h6l1 3H8l1-3Zm1 16h4a2 2 0 0 0 1.997-1.895L17 7H7l1.003 11.105A2 2 0 0 0 10 20Z" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
            {#if expandedRiskRowId === risk.id}
              <tr class="bg-neutral-50/70">
                <td colspan="7" class="px-4 pb-4 pt-0">
                  <div class="grid gap-3 pt-3 md:grid-cols-3">
                    <div class="rounded-lg border border-neutral-200 bg-white p-3">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Category & Treatment</p>
                      <p class="mt-1 text-sm font-medium text-neutral-900">{risk.risk_category_name ?? "Uncategorized"}</p>
                      <p class="mt-1 text-xs text-neutral-600">Type: {risk.risk_category_type_display ?? "--"}</p>
                      <p class="mt-1 text-xs text-neutral-600">Treatment: {risk.treatment_display}</p>
                    </div>
                    <div class="rounded-lg border border-neutral-200 bg-white p-3">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Owner & SLA</p>
                      <p class="mt-1 text-sm font-medium text-neutral-900">{risk.owner_role_name ?? "Unassigned"}</p>
                      <p class="mt-1 text-xs text-neutral-600">Response SLA: {risk.response_time_hours ? `${risk.response_time_hours}h` : "--"}</p>
                      <p class="mt-1 text-xs text-neutral-600">Escalation required: {risk.escalation_required ? "Yes" : "No"}</p>
                    </div>
                    <div class="rounded-lg border border-neutral-200 bg-white p-3">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Timeline</p>
                      <p class="mt-1 text-xs text-neutral-600">Identified: {fmtDate(risk.identified_on)}</p>
                      <p class="mt-1 text-xs text-neutral-600">Target resolution: {fmtDate(risk.target_resolution_date)}</p>
                      <p class="mt-1 text-xs text-neutral-600">Last reviewed: {fmtDate(risk.last_reviewed_on)}</p>
                      <p class="mt-1 text-xs text-neutral-600">Resolved: {fmtDate(risk.resolved_on)}</p>
                    </div>
                    <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Description</p>
                      <p class="mt-2 text-xs text-neutral-700 leading-relaxed whitespace-pre-wrap">
                        {risk.description || "--"}
                      </p>
                    </div>
                    <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Mitigation Details</p>
                      <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                        <p><span class="font-semibold text-neutral-700">Mitigation plan:</span> {risk.mitigation_plan || "--"}</p>
                        <p><span class="font-semibold text-neutral-700">Mitigation actions:</span> {risk.mitigation_actions || "--"}</p>
                        <p class="md:col-span-2"><span class="font-semibold text-neutral-700">Contingency plan:</span> {risk.contingency_plan || "--"}</p>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        {/if}
      </tbody>
    </table>
    <div class="px-4 py-3 border-t border-neutral-100 flex items-center justify-between text-xs text-neutral-500">
      <span>{filteredRisks.length} risks</span>
      <div class="flex items-center gap-2">
        <button
          onclick={() => (currentPage = Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          class="px-2.5 py-1.5 rounded border border-neutral-200 disabled:opacity-40"
        >
          Prev
        </button>
        <span>Page {currentPage} / {totalPages}</span>
        <button
          onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          class="px-2.5 py-1.5 rounded border border-neutral-200 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</div>

{#if showEditor}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-neutral-900/35" onclick={resetEditor} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl h-full overflow-y-auto bg-white shadow-xl">
      <div class="sticky top-0 z-10 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between">
        <h3 class="text-base font-semibold text-neutral-900">
          {editingRiskId ? "Edit Risk Entry" : "New Risk Entry"}
        </h3>
        <button onclick={resetEditor} class="text-sm text-neutral-500 hover:text-neutral-900">Close</button>
      </div>

      <div class="px-6 py-5 space-y-5">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label for="rr-project" class="block text-xs font-semibold text-neutral-600 mb-1.5">Project *</label>
            <select id="rr-project" bind:value={form.project} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
              <option value={0}>Select project</option>
              {#each projects as project}
                <option value={project.id}>{project.name}</option>
              {/each}
            </select>
            {#if fieldError("project")}<p class="mt-1 text-xs text-rose-600">{fieldError("project")}</p>{/if}
          </div>
          <div class="sm:col-span-2">
            <label for="rr-title" class="block text-xs font-semibold text-neutral-600 mb-1.5">Risk Title *</label>
            <input id="rr-title" bind:value={form.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
            {#if fieldError("title")}<p class="mt-1 text-xs text-rose-600">{fieldError("title")}</p>{/if}
          </div>
          <div class="sm:col-span-2">
            <label for="rr-description" class="block text-xs font-semibold text-neutral-600 mb-1.5">Description</label>
            <textarea id="rr-description" bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </div>
          <div>
            <label for="rr-category" class="block text-xs font-semibold text-neutral-600 mb-1.5">Risk Category</label>
            <select id="rr-category" bind:value={form.risk_category} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
              <option value={0}>Uncategorized</option>
              {#each categories as category}
                <option value={category.id}>{category.name}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="rr-treatment" class="block text-xs font-semibold text-neutral-600 mb-1.5">Treatment</label>
            <select id="rr-treatment" bind:value={form.treatment} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
              {#each treatmentOptions as treatment}
                <option value={treatment.value}>{treatment.label}</option>
              {/each}
            </select>
          </div>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold text-neutral-900">Matrix Scoring (from Settings)</h4>
            <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {severityClass(previewSeverity)}">
              Score {previewScore} · {toLabel(previewSeverity)}
            </span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label for="rr-likelihood" class="block text-xs font-semibold text-neutral-600 mb-1.5">Likelihood</label>
              <select id="rr-likelihood" bind:value={form.likelihood_key} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
                {#each likelihoodScale as level}
                  <option value={level.key}>{level.label} ({level.value})</option>
                {/each}
              </select>
              {#if fieldError("likelihood_key")}<p class="mt-1 text-xs text-rose-600">{fieldError("likelihood_key")}</p>{/if}
            </div>
            <div>
              <label for="rr-impact" class="block text-xs font-semibold text-neutral-600 mb-1.5">Impact</label>
              <select id="rr-impact" bind:value={form.impact_key} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
                {#each impactScale as level}
                  <option value={level.key}>{level.label} ({level.value})</option>
                {/each}
              </select>
              {#if fieldError("impact_key")}<p class="mt-1 text-xs text-rose-600">{fieldError("impact_key")}</p>{/if}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label for="rr-status" class="block text-xs font-semibold text-neutral-600 mb-1.5">Status</label>
            <select id="rr-status" bind:value={form.status} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
              {#each statusOptions as status}
                <option value={status.value}>{status.label}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="rr-owner-role" class="block text-xs font-semibold text-neutral-600 mb-1.5">Mitigation Owner Role</label>
            <select id="rr-owner-role" bind:value={form.owner_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm">
              <option value={0}>Unassigned</option>
              {#each roles as role}
                <option value={role.id}>{role.name}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="rr-sla" class="block text-xs font-semibold text-neutral-600 mb-1.5">Response SLA (hours)</label>
            <input id="rr-sla" type="number" bind:value={form.response_time_hours} min="1" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="rr-identified" class="block text-xs font-semibold text-neutral-600 mb-1.5">Identified On</label>
              <DateInput id="rr-identified" bind:value={form.identified_on} />
            </div>
            <div>
              <label for="rr-target-resolution" class="block text-xs font-semibold text-neutral-600 mb-1.5">Target Resolution</label>
              <DateInput id="rr-target-resolution" bind:value={form.target_resolution_date} />
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" bind:checked={form.escalation_required} class="rounded border-neutral-300" />
              Escalation required
            </label>
          </div>
        </div>

        {#if suggestedRule}
          <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
            <p class="font-semibold">Suggested rule found for this category and severity.</p>
            <p class="mt-1">
              Role: {suggestedRule.assign_to_role_name ?? "None"} · SLA: {suggestedRule.response_time_hours ?? "-"}h
            </p>
            <button
              onclick={applySuggestedRule}
              class="mt-2 px-2.5 py-1.5 rounded border border-emerald-300 bg-white text-emerald-700 font-semibold"
            >
              Apply suggested mitigation defaults
            </button>
          </div>
        {/if}

        <div>
          <label for="rr-mitigation-plan" class="block text-xs font-semibold text-neutral-600 mb-1.5">Mitigation Plan</label>
          <textarea id="rr-mitigation-plan" bind:value={form.mitigation_plan} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </div>
        <div>
          <label for="rr-mitigation-actions" class="block text-xs font-semibold text-neutral-600 mb-1.5">Mitigation Actions</label>
          <textarea id="rr-mitigation-actions" bind:value={form.mitigation_actions} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </div>
        <div>
          <label for="rr-contingency-plan" class="block text-xs font-semibold text-neutral-600 mb-1.5">Contingency Plan</label>
          <textarea id="rr-contingency-plan" bind:value={form.contingency_plan} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <label class="block">
            <span class="block text-xs font-semibold text-neutral-600 mb-1.5">Supporting Photos/Documents</span>
            <input
              type="file"
              multiple
              onchange={onSupportingFilesSelected}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
            />
          </label>
          {#if riskSupportingFiles.length > 0}
            <p class="mt-2 text-xs text-neutral-500">{riskSupportingFiles.length} file(s) selected.</p>
          {/if}
        </div>
      </div>

      <div class="sticky bottom-0 bg-white border-t border-neutral-200 px-6 py-4 flex justify-end gap-2">
        <button onclick={resetEditor} class="px-4 py-2 rounded-lg border border-neutral-200 text-sm font-semibold text-neutral-700">
          Cancel
        </button>
        {#if isDev}
          <button
            type="button"
            onclick={devFillRisk}
            class="px-4 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600"
          >
            Dev Fill
          </button>
        {/if}
        <button
          onclick={saveRisk}
          disabled={saving}
          class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-800 disabled:opacity-50"
        >
          {saving ? "Saving..." : editingRiskId ? "Update Risk" : "Create Risk"}
        </button>
      </div>
    </div>
  </div>
{/if}
