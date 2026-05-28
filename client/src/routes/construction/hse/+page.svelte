<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    HSEDashboard,
    HSEIncidentListItem,
    HSEIncidentDetail,
    HSEIncidentClassification,
    HSEIncidentRootCause,
    HSEIncidentStatus,
    HSEPermitListItem,
    HSEPermitDetail,
    HSEPermitType,
    HSEPermitStatus,
    HSEToolboxTalkListItem,
    HSEToolboxTalkDetail,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── Tab State ─────────────────────────────────────────────────────────
  type Tab = "dashboard" | "permits" | "incidents" | "toolbox_talks";
  let activeTab = $state<Tab>("dashboard");

  // ── Dashboard ─────────────────────────────────────────────────────────
  let dashboard = $state<HSEDashboard | null>(null);
  let dashLoading = $state(true);

  // ── Incidents ─────────────────────────────────────────────────────────
  let incidents = $state<HSEIncidentListItem[]>([]);
  let incidentsLoading = $state(true);
  let incidentsTotal = $state(0);
  let incidentsPage = $state(1);
  let incidentsSearch = $state("");
  let incidentsSearchInput = $state("");
  let incidentsClassFilter = $state("");
  let incidentsStatusFilter = $state("");
  let incSearchTimeout: ReturnType<typeof setTimeout> | undefined;

  let incidentDetailOpen = $state(false);
  let incidentDetail = $state<HSEIncidentDetail | null>(null);
  let incidentDetailLoading = $state(false);

  let incidentCreateOpen = $state(false);
  let incidentSaving = $state(false);
  let incidentForm = $state(defaultIncidentForm());

  // ── Permits ───────────────────────────────────────────────────────────
  let permits = $state<HSEPermitListItem[]>([]);
  let permitsLoading = $state(true);
  let permitsTotal = $state(0);
  let permitsPage = $state(1);
  let permitsSearch = $state("");
  let permitsSearchInput = $state("");
  let permitsTypeFilter = $state("");
  let permitsStatusFilter = $state("");
  let permitSearchTimeout: ReturnType<typeof setTimeout> | undefined;

  let permitDetailOpen = $state(false);
  let permitDetail = $state<HSEPermitDetail | null>(null);
  let permitDetailLoading = $state(false);

  let permitCreateOpen = $state(false);
  let permitSaving = $state(false);
  let permitForm = $state(defaultPermitForm());

  // ── Toolbox Talks ─────────────────────────────────────────────────────
  let tbts = $state<HSEToolboxTalkListItem[]>([]);
  let tbtsLoading = $state(true);
  let tbtsTotal = $state(0);
  let tbtsPage = $state(1);
  let tbtsSearch = $state("");
  let tbtsSearchInput = $state("");
  let tbtSearchTimeout: ReturnType<typeof setTimeout> | undefined;

  let tbtDetailOpen = $state(false);
  let tbtDetail = $state<HSEToolboxTalkDetail | null>(null);
  let tbtDetailLoading = $state(false);

  let tbtCreateOpen = $state(false);
  let tbtSaving = $state(false);
  let tbtForm = $state(defaultTBTForm());

  // Shared
  let projects = $state<ProjectListItem[]>([]);
  const pageSize = 15;
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  // ── Defaults ──────────────────────────────────────────────────────────

  function defaultIncidentForm() {
    return {
      project: "",
      title: "",
      description: "",
      classification: "near_miss" as HSEIncidentClassification,
      root_cause: "" as HSEIncidentRootCause | "",
      status: "reported" as HSEIncidentStatus,
      location: "",
      incident_date: new Date().toISOString().slice(0, 10),
      incident_time: "",
      reported_by: "",
      persons_involved: "",
      witness_statements: "",
      injuries_description: "",
      lost_time_days: "0",
      corrective_actions: "",
      preventive_actions: "",
      requires_regulatory_report: false,
      notes: "",
    };
  }

  function defaultPermitForm() {
    return {
      project: "",
      permit_type: "working_at_heights" as HSEPermitType,
      title: "",
      description: "",
      status: "draft" as HSEPermitStatus,
      location: "",
      task_description: "",
      hazards_identified: "",
      mitigations: "",
      required_ppe: "",
      valid_from: "",
      valid_until: "",
      requested_by: "",
      approved_by: "",
      notes: "",
    };
  }

  function defaultTBTForm() {
    return {
      project: "",
      topic: "",
      description: "",
      conducted_by: "",
      conducted_date: new Date().toISOString().slice(0, 10),
      shift: "day",
      location: "",
      attendees_count: "0",
      attendees_names: "",
      key_points: "",
      follow_up_actions: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let incDevIdx = 0;
  const INC_SAMPLES = [
    {
      title: "Near miss — unsecured scaffold plank at Level 5",
      description: "During morning walkthrough, a loose scaffold plank was discovered at Level 5, Block B. The plank had shifted approximately 30cm from its bracket. No workers were on the platform at the time. Area was immediately cordoned off.",
      classification: "near_miss" as HSEIncidentClassification,
      root_cause: "unsafe_conditions" as HSEIncidentRootCause,
      location: "Block B, Level 5, East Scaffolding",
      reported_by: "Safety Officer Amina Yusuf",
      persons_involved: "None (area unoccupied at time of discovery)",
      injuries_description: "",
      lost_time_days: "0",
      corrective_actions: "1. All scaffold planks on Block B inspected and re-secured\n2. Scaffold clamps replaced where worn\n3. Daily scaffold inspection checklist updated",
      preventive_actions: "Scaffold inspection frequency increased to twice daily during high-wind season",
      notes: "Wind speed recorded at 35km/h the previous evening. Weather monitoring alerts to be added for scaffold crews.",
    },
    {
      title: "Minor injury — hand laceration during rebar cutting",
      description: "Worker sustained a 4cm laceration to left palm while handling freshly cut rebar. Worker was wearing standard gloves but not cut-resistant gloves required for rebar handling. First aid administered on site.",
      classification: "minor_injury" as HSEIncidentClassification,
      root_cause: "ppe_failure" as HSEIncidentRootCause,
      location: "Rebar Yard, Ground Floor",
      reported_by: "Foreman Emeka Obi",
      persons_involved: "Labourer Musa Abdullahi (ID: WK-0342)",
      injuries_description: "4cm laceration to left palm. First aid applied. Worker referred to site clinic. Returned to light duties after 1 day.",
      lost_time_days: "1",
      corrective_actions: "1. Worker treated and cleared by site nurse\n2. Cut-resistant gloves issued immediately\n3. Rebar handling crew briefed on mandatory PPE",
      preventive_actions: "PPE compliance audit for all cutting operations. Cut-resistant gloves added to mandatory issue list for rebar crews.",
      notes: "Worker's PPE checklist showed standard gloves only. Supervisor counselled on PPE verification before task start.",
    },
  ];

  function devFillIncident() {
    const s = INC_SAMPLES[incDevIdx % INC_SAMPLES.length];
    incDevIdx++;
    incidentForm = {
      ...defaultIncidentForm(),
      project: incidentForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      title: s.title,
      description: s.description,
      classification: s.classification,
      root_cause: s.root_cause,
      location: s.location,
      reported_by: s.reported_by,
      persons_involved: s.persons_involved,
      injuries_description: s.injuries_description,
      lost_time_days: s.lost_time_days,
      corrective_actions: s.corrective_actions,
      preventive_actions: s.preventive_actions,
      notes: s.notes,
    };
  }

  let permitDevIdx = 0;
  const PERMIT_SAMPLES = [
    {
      permit_type: "working_at_heights" as HSEPermitType,
      title: "Rooftop waterproofing — Block A Levels 14-16",
      description: "Permit for waterproofing membrane installation on rooftop areas of Block A. Workers will be operating at heights exceeding 40m with fall protection required at all times.",
      location: "Block A, Rooftop (Levels 14-16)",
      task_description: "Installation of bituminous waterproofing membrane on exposed roof deck. Includes primer application, torch-on membrane laying, and overlap sealing.",
      hazards_identified: "1. Fall from height (40m+)\n2. Hot work (torch application)\n3. Fume inhalation from bitumen primer\n4. Burns from hot membrane application",
      mitigations: "1. Full body harness with twin lanyard anchored to certified anchor points\n2. Fire extinguisher on standby, fire watch for 30min after hot work\n3. RPE (half-face respirator with organic vapour cartridge)\n4. Heat-resistant gloves and long-sleeve coveralls",
      required_ppe: "Safety helmet, full body harness, twin lanyard, safety boots, heat-resistant gloves, safety goggles, RPE (organic vapour)",
      requested_by: "Engr. Tunde Bakare",
      notes: "Weather check required before each shift. No work if wind speed exceeds 40km/h.",
    },
    {
      permit_type: "electrical_isolation" as HSEPermitType,
      title: "Main switchboard energisation — Basement B1",
      description: "Permit for initial energisation of the main LV switchboard in Basement B1. Requires full electrical isolation verification and lock-out/tag-out compliance before live testing.",
      location: "Basement B1, Electrical Room ER-01",
      task_description: "Lock-out/tag-out verification, insulation resistance testing, phase rotation check, and initial switchboard energisation under controlled conditions.",
      hazards_identified: "1. Electrocution (415V 3-phase)\n2. Arc flash\n3. Incorrect phase rotation causing equipment damage\n4. Residual stored energy in capacitor banks",
      mitigations: "1. Lock-out/tag-out protocol strictly enforced\n2. Arc-rated PPE (Category 2 minimum)\n3. Phase rotation meter verification before energisation\n4. Capacitor discharge verification with volt meter",
      required_ppe: "Arc flash suit (Cat 2), insulated gloves (Class 0), face shield, safety boots (EH rated), insulated tools",
      requested_by: "Engr. Kola Adesanya",
      notes: "Only qualified electricians with valid LOTO certification. Emergency de-energisation procedure posted at switchboard.",
    },
  ];

  function devFillPermit() {
    const s = PERMIT_SAMPLES[permitDevIdx % PERMIT_SAMPLES.length];
    permitDevIdx++;
    permitForm = {
      ...defaultPermitForm(),
      project: permitForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      permit_type: s.permit_type,
      title: s.title,
      description: s.description,
      location: s.location,
      task_description: s.task_description,
      hazards_identified: s.hazards_identified,
      mitigations: s.mitigations,
      required_ppe: s.required_ppe,
      requested_by: s.requested_by,
      notes: s.notes,
    };
  }

  let tbtDevIdx = 0;
  const TBT_SAMPLES = [
    {
      topic: "Proper Ladder Placement & 3-Point Contact",
      description: "Refresher on safe ladder use following two near-misses this month involving unstable ladder setups on uneven ground.",
      conducted_by: "Safety Officer Amina Yusuf",
      location: "Site Assembly Area, Block A",
      attendees_count: "24",
      attendees_names: "All Block A day shift workers (roster attached)",
      key_points: "1. 4:1 rule — base 1m out for every 4m height\n2. Always maintain 3-point contact (2 hands + 1 foot or 2 feet + 1 hand)\n3. Never place ladders on loose materials or uneven ground\n4. Secure top of ladder to prevent lateral movement\n5. Do not carry tools while climbing — use a tool belt or hoist line",
      follow_up_actions: "Supervisor to inspect all ladder setups before use for the next 2 weeks. Report non-compliance immediately.",
      notes: "Two near-misses reported on 18 Mar and 21 Mar. Both involved ladders on unpacked soil near excavation edges.",
    },
    {
      topic: "Heat Stress Prevention for Outdoor Workers",
      description: "Mandatory briefing ahead of dry season — temperatures expected to exceed 38°C. Covers hydration, rest cycles, and heat illness recognition.",
      conducted_by: "Site Nurse Florence Eze",
      location: "Canteen Area",
      attendees_count: "45",
      attendees_names: "All outdoor crews — earthmoving, scaffolding, concrete, and steel fixing teams",
      key_points: "1. Drink 250ml water every 20 minutes during outdoor work\n2. Mandatory 15-minute shade breaks every 2 hours between 11am–3pm\n3. Recognise heat exhaustion signs: dizziness, nausea, heavy sweating, rapid pulse\n4. If symptoms appear — stop work, move to shade, cool with wet cloth, report to supervisor\n5. Never remove PPE due to heat — report if PPE is causing overheating",
      follow_up_actions: "Water stations to be set up at every 50m on active work fronts. Cooling towels issued to outdoor crews.",
      notes: "Last year 3 workers treated for heat exhaustion in April. Proactive briefing to prevent recurrence.",
    },
  ];

  function devFillTBT() {
    const s = TBT_SAMPLES[tbtDevIdx % TBT_SAMPLES.length];
    tbtDevIdx++;
    tbtForm = {
      ...defaultTBTForm(),
      project: tbtForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      topic: s.topic,
      description: s.description,
      conducted_by: s.conducted_by,
      location: s.location,
      attendees_count: s.attendees_count,
      attendees_names: s.attendees_names,
      key_points: s.key_points,
      follow_up_actions: s.follow_up_actions,
      notes: s.notes,
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchDashboard() {
    dashLoading = true;
    try { dashboard = await api.get<HSEDashboard>("/projects/hse/dashboard/"); } catch { dashboard = null; }
    dashLoading = false;
  }

  async function fetchProjects() {
    if (projects.length > 0) return;
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" });
      projects = res.results;
    } catch { /* noop */ }
  }

  async function fetchIncidents() {
    incidentsLoading = true;
    try {
      const params: Record<string, string> = { page: String(incidentsPage), page_size: String(pageSize) };
      if (incidentsSearch) params.search = incidentsSearch;
      if (incidentsClassFilter) params.classification = incidentsClassFilter;
      if (incidentsStatusFilter) params.status = incidentsStatusFilter;
      const res = await api.get<PaginatedResponse<HSEIncidentListItem>>("/projects/hse/incidents/", params);
      incidents = res.results;
      incidentsTotal = res.count;
    } catch { incidents = []; incidentsTotal = 0; }
    incidentsLoading = false;
  }

  async function fetchPermits() {
    permitsLoading = true;
    try {
      const params: Record<string, string> = { page: String(permitsPage), page_size: String(pageSize) };
      if (permitsSearch) params.search = permitsSearch;
      if (permitsTypeFilter) params.permit_type = permitsTypeFilter;
      if (permitsStatusFilter) params.status = permitsStatusFilter;
      const res = await api.get<PaginatedResponse<HSEPermitListItem>>("/projects/hse/permits/", params);
      permits = res.results;
      permitsTotal = res.count;
    } catch { permits = []; permitsTotal = 0; }
    permitsLoading = false;
  }

  async function fetchTBTs() {
    tbtsLoading = true;
    try {
      const params: Record<string, string> = { page: String(tbtsPage), page_size: String(pageSize) };
      if (tbtsSearch) params.search = tbtsSearch;
      const res = await api.get<PaginatedResponse<HSEToolboxTalkListItem>>("/projects/hse/toolbox-talks/", params);
      tbts = res.results;
      tbtsTotal = res.count;
    } catch { tbts = []; tbtsTotal = 0; }
    tbtsLoading = false;
  }

  // Tab-driven loading
  $effect(() => { if (activeTab === "dashboard") fetchDashboard(); });
  $effect(() => { if (activeTab === "incidents") { void incidentsSearch; void incidentsClassFilter; void incidentsStatusFilter; void incidentsPage; fetchIncidents(); fetchProjects(); } });
  $effect(() => { if (activeTab === "permits") { void permitsSearch; void permitsTypeFilter; void permitsStatusFilter; void permitsPage; fetchPermits(); fetchProjects(); } });
  $effect(() => { if (activeTab === "toolbox_talks") { void tbtsSearch; void tbtsPage; fetchTBTs(); fetchProjects(); } });

  // Load dashboard on mount
  $effect(() => { fetchDashboard(); });

  // ── Search ────────────────────────────────────────────────────────────
  function onIncSearch(e: Event) { incidentsSearchInput = (e.target as HTMLInputElement).value; if (incSearchTimeout) clearTimeout(incSearchTimeout); incSearchTimeout = setTimeout(() => { incidentsSearch = incidentsSearchInput.trim(); incidentsPage = 1; }, 250); }
  function onPermitSearch(e: Event) { permitsSearchInput = (e.target as HTMLInputElement).value; if (permitSearchTimeout) clearTimeout(permitSearchTimeout); permitSearchTimeout = setTimeout(() => { permitsSearch = permitsSearchInput.trim(); permitsPage = 1; }, 250); }
  function onTBTSearch(e: Event) { tbtsSearchInput = (e.target as HTMLInputElement).value; if (tbtSearchTimeout) clearTimeout(tbtSearchTimeout); tbtSearchTimeout = setTimeout(() => { tbtsSearch = tbtsSearchInput.trim(); tbtsPage = 1; }, 250); }

  // ── Detail Drawers ────────────────────────────────────────────────────
  async function openIncidentDetail(id: number) { incidentDetailOpen = true; incidentDetailLoading = true; try { incidentDetail = await api.get<HSEIncidentDetail>(`/projects/hse/incidents/${id}/`); } catch { incidentDetail = null; } incidentDetailLoading = false; }
  async function openPermitDetail(id: number) { permitDetailOpen = true; permitDetailLoading = true; try { permitDetail = await api.get<HSEPermitDetail>(`/projects/hse/permits/${id}/`); } catch { permitDetail = null; } permitDetailLoading = false; }
  async function openTBTDetail(id: number) { tbtDetailOpen = true; tbtDetailLoading = true; try { tbtDetail = await api.get<HSEToolboxTalkDetail>(`/projects/hse/toolbox-talks/${id}/`); } catch { tbtDetail = null; } tbtDetailLoading = false; }

  // ── Save ──────────────────────────────────────────────────────────────
  async function saveIncident(e: Event) {
    e.preventDefault();
    if (!incidentForm.title.trim() || !incidentForm.project) { toast.error("Validation", "Title and project are required."); return; }
    incidentSaving = true;
    try {
      await api.post("/projects/hse/incidents/", {
        ...incidentForm,
        project: Number(incidentForm.project),
        root_cause: incidentForm.root_cause || null,
        incident_time: incidentForm.incident_time || null,
        lost_time_days: Number(incidentForm.lost_time_days) || 0,
      });
      toast.success("Incident reported", `"${incidentForm.title}" logged.`);
      incidentCreateOpen = false;
      incidentForm = defaultIncidentForm();
      await fetchIncidents();
      dashboard = null;
      fetchDashboard();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { incidentSaving = false; }
  }

  async function savePermit(e: Event) {
    e.preventDefault();
    if (!permitForm.title.trim() || !permitForm.project) { toast.error("Validation", "Title and project are required."); return; }
    permitSaving = true;
    try {
      await api.post("/projects/hse/permits/", {
        ...permitForm,
        project: Number(permitForm.project),
        valid_from: permitForm.valid_from || null,
        valid_until: permitForm.valid_until || null,
      });
      toast.success("Permit created", `"${permitForm.title}" created.`);
      permitCreateOpen = false;
      permitForm = defaultPermitForm();
      await fetchPermits();
      dashboard = null;
      fetchDashboard();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { permitSaving = false; }
  }

  async function saveTBT(e: Event) {
    e.preventDefault();
    if (!tbtForm.topic.trim() || !tbtForm.project) { toast.error("Validation", "Topic and project are required."); return; }
    tbtSaving = true;
    try {
      await api.post("/projects/hse/toolbox-talks/", {
        ...tbtForm,
        project: Number(tbtForm.project),
        attendees_count: Number(tbtForm.attendees_count) || 0,
      });
      toast.success("TBT recorded", `"${tbtForm.topic}" saved.`);
      tbtCreateOpen = false;
      tbtForm = defaultTBTForm();
      await fetchTBTs();
      dashboard = null;
      fetchDashboard();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { tbtSaving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtDateTime(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  function totalPages(count: number): number { return Math.max(1, Math.ceil(count / pageSize)); }

  function classificationColor(c: string): string {
    switch (c) {
      case "near_miss": return "bg-blue-100 text-blue-800";
      case "first_aid": return "bg-yellow-100 text-yellow-800";
      case "minor_injury": return "bg-orange-100 text-orange-800";
      case "major_accident": return "bg-red-100 text-red-800";
      case "fatality": return "bg-red-200 text-red-900";
      case "environmental": return "bg-emerald-100 text-emerald-800";
      case "property_damage": return "bg-neutral-100 text-neutral-700";
      default: return "bg-neutral-100 text-neutral-600";
    }
  }

  function permitStatusColor(s: string): string {
    switch (s) {
      case "active": return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case "expired": return "bg-red-100 text-red-800 border-red-200";
      case "revoked": return "bg-red-100 text-red-800 border-red-200";
      case "suspended": return "bg-amber-100 text-amber-800 border-amber-200";
      case "pending_approval": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      default: return "bg-neutral-100 text-neutral-600 border-neutral-200";
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "dashboard", label: "Command Center" },
    { key: "permits", label: "Permits to Work" },
    { key: "incidents", label: "Incidents & Near-Misses" },
    { key: "toolbox_talks", label: "Toolbox Talks" },
  ];

  useAutoRefresh(["HSEIncident", "HSEPermit"], fetchIncidents);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Health, Safety & Environment</h1>
      <p class="mt-1 text-sm text-neutral-500">Safety compliance, permits, incident reporting, and daily briefings.</p>
    </div>
  </div>

  <!-- Tab Bar -->
  <div class="border-b border-neutral-200">
    <nav class="-mb-px flex gap-6">
      {#each tabs as tab}
        <button
          class="whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700'}"
          onclick={() => (activeTab = tab.key)}
        >
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>

  <!-- ═══════════ DASHBOARD ═══════════ -->
  {#if activeTab === "dashboard"}
    {#if dashLoading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if dashboard}
      <!-- Safe Days Hero -->
      <div class="rounded-2xl bg-linear-to-br from-emerald-600 to-emerald-800 p-6 text-white shadow-lg">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-emerald-200">Safe Days Since Last Incident</p>
            <p class="mt-2 text-5xl font-bold tabular-nums">{dashboard.safe_days}</p>
            <p class="mt-1 text-sm text-emerald-200">consecutive days</p>
          </div>
          <div class="text-right space-y-2">
            <div class="rounded-lg bg-white/10 backdrop-blur-sm px-4 py-2">
              <p class="text-xs text-emerald-200">Lost Time Injuries</p>
              <p class="text-lg font-bold tabular-nums">{dashboard.lost_time_injuries}</p>
            </div>
            <div class="rounded-lg bg-white/10 backdrop-blur-sm px-4 py-2">
              <p class="text-xs text-emerald-200">Total Lost Days</p>
              <p class="text-lg font-bold tabular-nums">{dashboard.total_lost_days}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI Cards -->
      <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Open Incidents</p>
          <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{dashboard.open_incidents}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Incidents</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{dashboard.total_incidents}</p>
        </div>
        <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Active Permits</p>
          <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{dashboard.active_permits}</p>
        </div>
        {#if dashboard.expired_permits > 0}
          <div class="rounded-xl border-2 border-red-300 bg-red-50 p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Expired Permits</p>
            <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{dashboard.expired_permits}</p>
          </div>
        {:else}
          <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Pending Approval</p>
            <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{dashboard.pending_permits}</p>
          </div>
        {/if}
        <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Toolbox Talks</p>
          <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{dashboard.total_tbts}</p>
        </div>
        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">TBTs This Month</p>
          <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{dashboard.tbts_this_month}</p>
        </div>
      </div>

      <!-- Incident Classification Breakdown -->
      {#if dashboard.classification_breakdown.length > 0}
        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">Incident Classification Breakdown</h3>
          <div class="space-y-3">
            {#each dashboard.classification_breakdown as item}
              {@const maxCount = Math.max(...dashboard!.classification_breakdown.map(d => d.count))}
              <div class="flex items-center gap-3">
                <p class="w-44 text-sm text-neutral-700 truncate">{item.label}</p>
                <div class="flex-1 h-6 bg-neutral-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all {item.classification === 'major_accident' || item.classification === 'fatality' ? 'bg-red-500' : item.classification === 'near_miss' ? 'bg-blue-500' : 'bg-amber-500'}"
                    style="width: {maxCount > 0 ? (item.count / maxCount) * 100 : 0}%"></div>
                </div>
                <span class="text-sm font-semibold text-neutral-900 w-8 text-right tabular-nums">{item.count}</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    {/if}

  <!-- ═══════════ PERMITS ═══════════ -->
  {:else if activeTab === "permits"}
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={permitsSearchInput} oninput={onPermitSearch} placeholder="Search permits..." class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={permitsTypeFilter} onchange={() => (permitsPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Types</option>
          <option value="working_at_heights">Working at Heights</option>
          <option value="hot_work">Hot Work</option>
          <option value="excavation">Excavation</option>
          <option value="electrical_isolation">Electrical Isolation</option>
          <option value="confined_space">Confined Space</option>
          <option value="lifting_operations">Lifting Operations</option>
          <option value="demolition">Demolition</option>
          <option value="other">Other</option>
        </select>
        <select bind:value={permitsStatusFilter} onchange={() => (permitsPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="pending_approval">Pending Approval</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="expired">Expired</option>
          <option value="closed">Closed</option>
          <option value="revoked">Revoked</option>
        </select>
      </div>
      <button onclick={() => { permitForm = defaultPermitForm(); permitCreateOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Permit</button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if permitsLoading}
        <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
      {:else if permits.length === 0}
        <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No permits found.</p></div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[900px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Permit #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Valid Until</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Requested By</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each permits as permit}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openPermitDetail(permit.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{permit.permit_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900 max-w-[220px] truncate">{permit.title}</td>
                  <td class="px-4 py-3 text-xs font-medium text-neutral-600">{permit.permit_type_display}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{permit.project_name}</td>
                  <td class="px-4 py-3"><span class="inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold {permitStatusColor(permit.status)}">{permit.status_display}</span></td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDateTime(permit.valid_until)}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{permit.requested_by || "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{(permitsPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(permitsPage * pageSize, permitsTotal)}</span> of <span class="font-semibold text-neutral-700">{permitsTotal}</span></p>
          <div class="flex items-center gap-2">
            <button onclick={() => (permitsPage = Math.max(1, permitsPage - 1))} disabled={permitsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {permitsPage} of {totalPages(permitsTotal)}</span>
            <button onclick={() => (permitsPage = Math.min(totalPages(permitsTotal), permitsPage + 1))} disabled={permitsPage >= totalPages(permitsTotal)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>

  <!-- ═══════════ INCIDENTS ═══════════ -->
  {:else if activeTab === "incidents"}
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={incidentsSearchInput} oninput={onIncSearch} placeholder="Search incidents..." class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={incidentsClassFilter} onchange={() => (incidentsPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Classifications</option>
          <option value="near_miss">Near Miss</option>
          <option value="first_aid">First Aid</option>
          <option value="minor_injury">Minor Injury</option>
          <option value="major_accident">Major Accident</option>
          <option value="fatality">Fatality</option>
          <option value="environmental">Environmental</option>
          <option value="property_damage">Property Damage</option>
        </select>
        <select bind:value={incidentsStatusFilter} onchange={() => (incidentsPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="reported">Reported</option>
          <option value="investigating">Investigating</option>
          <option value="corrective_action">Corrective Action</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <button onclick={() => { incidentForm = defaultIncidentForm(); incidentCreateOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Report Incident</button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if incidentsLoading}
        <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
      {:else if incidents.length === 0}
        <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No incidents found.</p></div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[950px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Incident #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Classification</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Lost Days</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Reported By</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each incidents as inc}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openIncidentDetail(inc.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{inc.incident_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900 max-w-[220px] truncate">{inc.title}</td>
                  <td class="px-4 py-3"><span class="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full {classificationColor(inc.classification)}">{inc.classification_display}</span></td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{inc.project_name}</td>
                  <td class="px-4 py-3"><StatusBadge status={inc.status} /></td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(inc.incident_date)}</td>
                  <td class="px-4 py-3 text-center text-sm font-semibold tabular-nums {inc.lost_time_days > 0 ? 'text-red-600' : 'text-neutral-400'}">{inc.lost_time_days}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{inc.reported_by || "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{(incidentsPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(incidentsPage * pageSize, incidentsTotal)}</span> of <span class="font-semibold text-neutral-700">{incidentsTotal}</span></p>
          <div class="flex items-center gap-2">
            <button onclick={() => (incidentsPage = Math.max(1, incidentsPage - 1))} disabled={incidentsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {incidentsPage} of {totalPages(incidentsTotal)}</span>
            <button onclick={() => (incidentsPage = Math.min(totalPages(incidentsTotal), incidentsPage + 1))} disabled={incidentsPage >= totalPages(incidentsTotal)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>

  <!-- ═══════════ TOOLBOX TALKS ═══════════ -->
  {:else if activeTab === "toolbox_talks"}
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={tbtsSearchInput} oninput={onTBTSearch} placeholder="Search toolbox talks..." class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
      </div>
      <button onclick={() => { tbtForm = defaultTBTForm(); tbtCreateOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Record TBT</button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if tbtsLoading}
        <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
      {:else if tbts.length === 0}
        <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No toolbox talks recorded.</p></div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[800px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">TBT #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Topic</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Conducted By</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Attendees</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Location</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each tbts as tbt}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openTBTDetail(tbt.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{tbt.tbt_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900 max-w-[240px] truncate">{tbt.topic}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{tbt.project_name}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{tbt.conducted_by || "--"}</td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(tbt.conducted_date)}</td>
                  <td class="px-4 py-3 text-center text-sm font-semibold tabular-nums text-neutral-700">{tbt.attendees_count}</td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{tbt.location || "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{(tbtsPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(tbtsPage * pageSize, tbtsTotal)}</span> of <span class="font-semibold text-neutral-700">{tbtsTotal}</span></p>
          <div class="flex items-center gap-2">
            <button onclick={() => (tbtsPage = Math.max(1, tbtsPage - 1))} disabled={tbtsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {tbtsPage} of {totalPages(tbtsTotal)}</span>
            <button onclick={() => (tbtsPage = Math.min(totalPages(tbtsTotal), tbtsPage + 1))} disabled={tbtsPage >= totalPages(tbtsTotal)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- ═══════════ INCIDENT DETAIL DRAWER ═══════════ -->
<DrawerShell open={incidentDetailOpen} title={incidentDetail?.incident_number ?? "Incident"} subtitle={incidentDetail?.title ?? ""} width="max-w-xl" onclose={() => (incidentDetailOpen = false)}>
  {#if incidentDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if incidentDetail}
    <div class="p-6 space-y-5">
      <div class="rounded-lg p-3 {incidentDetail.classification === 'major_accident' || incidentDetail.classification === 'fatality' ? 'bg-red-50 border border-red-200' : incidentDetail.classification === 'near_miss' ? 'bg-blue-50 border border-blue-200' : 'bg-amber-50 border border-amber-200'}">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold rounded-full px-2 py-0.5 {classificationColor(incidentDetail.classification)}">{incidentDetail.classification_display}</span>
          <StatusBadge status={incidentDetail.status} />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{incidentDetail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Date</p><p class="text-sm text-neutral-900">{fmtDate(incidentDetail.incident_date)}{incidentDetail.incident_time ? ` at ${incidentDetail.incident_time}` : ""}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{incidentDetail.location || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Root Cause</p><p class="text-sm text-neutral-900">{incidentDetail.root_cause_display || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Reported By</p><p class="text-sm text-neutral-900">{incidentDetail.reported_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Lost Time Days</p><p class="text-sm font-semibold {incidentDetail.lost_time_days > 0 ? 'text-red-600' : 'text-neutral-900'}">{incidentDetail.lost_time_days}</p></div>
      </div>
      {#if incidentDetail.description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.description}</p></div>{/if}
      {#if incidentDetail.persons_involved}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Persons Involved</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.persons_involved}</p></div>{/if}
      {#if incidentDetail.injuries_description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Injuries</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.injuries_description}</p></div>{/if}
      {#if incidentDetail.witness_statements}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Witness Statements</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.witness_statements}</p></div>{/if}
      {#if incidentDetail.corrective_actions}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Corrective Actions</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.corrective_actions}</p></div>{/if}
      {#if incidentDetail.preventive_actions}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Preventive Actions</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.preventive_actions}</p></div>{/if}
      {#if incidentDetail.requires_regulatory_report}<div class="rounded-lg bg-amber-50 border border-amber-200 p-3"><p class="text-xs font-semibold text-amber-800">Requires Regulatory Report</p></div>{/if}
      {#if incidentDetail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{incidentDetail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ INCIDENT CREATE DRAWER ═══════════ -->
<DrawerShell open={incidentCreateOpen} title="Report Incident" subtitle="Log a safety incident or near-miss" width="max-w-xl" onclose={() => (incidentCreateOpen = false)}>
  <form onsubmit={saveIncident} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={incidentForm.title} placeholder="e.g. Near miss — unsecured scaffold" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={incidentForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Classification</span><select bind:value={incidentForm.classification} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="near_miss">Near Miss</option><option value="first_aid">First Aid</option><option value="minor_injury">Minor Injury</option><option value="major_accident">Major Accident</option><option value="fatality">Fatality</option><option value="environmental">Environmental</option><option value="property_damage">Property Damage</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Date</span><DateInput bind:value={incidentForm.incident_date} /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={incidentForm.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Root Cause</span><select bind:value={incidentForm.root_cause} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Not determined</option><option value="human_error">Human Error</option><option value="equipment_failure">Equipment Failure</option><option value="unsafe_conditions">Unsafe Conditions</option><option value="lack_of_training">Lack of Training</option><option value="ppe_failure">PPE Failure</option><option value="weather">Weather</option><option value="procedural">Procedural</option><option value="other">Other</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Reported By</span><input bind:value={incidentForm.reported_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={incidentForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Persons Involved</span><textarea bind:value={incidentForm.persons_involved} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Lost Time Days</span><input type="number" min="0" bind:value={incidentForm.lost_time_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label class="flex items-center gap-2 pt-5"><input type="checkbox" bind:checked={incidentForm.requires_regulatory_report} class="rounded" /><span class="text-xs font-medium text-neutral-600">Requires Regulatory Report</span></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Corrective Actions</span><textarea bind:value={incidentForm.corrective_actions} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={incidentForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (incidentCreateOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillIncident} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={incidentSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{incidentSaving ? "Saving..." : "Report Incident"}</button>
    </div>
  </form>
</DrawerShell>

<!-- ═══════════ PERMIT DETAIL DRAWER ═══════════ -->
<DrawerShell open={permitDetailOpen} title={permitDetail?.permit_number ?? "Permit"} subtitle={permitDetail?.title ?? ""} width="max-w-xl" onclose={() => (permitDetailOpen = false)}>
  {#if permitDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if permitDetail}
    <div class="p-6 space-y-5">
      <div class="rounded-lg p-3 border {permitStatusColor(permitDetail.status)}">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold">{permitDetail.permit_type_display}</span>
          <span class="text-xs font-semibold">{permitDetail.status_display}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{permitDetail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{permitDetail.location || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Valid From</p><p class="text-sm text-neutral-900">{fmtDateTime(permitDetail.valid_from)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Valid Until</p><p class="text-sm text-neutral-900">{fmtDateTime(permitDetail.valid_until)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Requested By</p><p class="text-sm text-neutral-900">{permitDetail.requested_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Approved By</p><p class="text-sm text-neutral-900">{permitDetail.approved_by || "--"}</p></div>
      </div>
      {#if permitDetail.task_description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Task Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{permitDetail.task_description}</p></div>{/if}
      {#if permitDetail.hazards_identified}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Hazards Identified</p><p class="text-sm text-neutral-700 whitespace-pre-line font-medium">{permitDetail.hazards_identified}</p></div>{/if}
      {#if permitDetail.mitigations}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Mitigations</p><p class="text-sm text-neutral-700 whitespace-pre-line">{permitDetail.mitigations}</p></div>{/if}
      {#if permitDetail.required_ppe}<div class="rounded-lg bg-amber-50 border border-amber-200 p-3"><p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700 mb-1">Required PPE</p><p class="text-sm text-amber-900 whitespace-pre-line font-medium">{permitDetail.required_ppe}</p></div>{/if}
      {#if permitDetail.site_supervisor_signoff}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Supervisor Sign-off</p><p class="text-sm text-neutral-900">{permitDetail.site_supervisor_signoff} — {fmtDateTime(permitDetail.site_supervisor_signoff_date)}</p></div>{/if}
      {#if permitDetail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{permitDetail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ PERMIT CREATE DRAWER ═══════════ -->
<DrawerShell open={permitCreateOpen} title="New Permit to Work" subtitle="Request clearance for a high-risk task" width="max-w-xl" onclose={() => (permitCreateOpen = false)}>
  <form onsubmit={savePermit} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={permitForm.title} placeholder="e.g. Rooftop waterproofing — Block A" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={permitForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Permit Type</span><select bind:value={permitForm.permit_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="working_at_heights">Working at Heights</option><option value="hot_work">Hot Work</option><option value="excavation">Excavation</option><option value="electrical_isolation">Electrical Isolation</option><option value="confined_space">Confined Space</option><option value="lifting_operations">Lifting Operations</option><option value="demolition">Demolition</option><option value="other">Other</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={permitForm.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Requested By</span><input bind:value={permitForm.requested_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Task Description</span><textarea bind:value={permitForm.task_description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Hazards Identified</span><textarea bind:value={permitForm.hazards_identified} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Mitigations</span><textarea bind:value={permitForm.mitigations} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Required PPE</span><textarea bind:value={permitForm.required_ppe} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={permitForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (permitCreateOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillPermit} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={permitSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{permitSaving ? "Saving..." : "Create Permit"}</button>
    </div>
  </form>
</DrawerShell>

<!-- ═══════════ TBT DETAIL DRAWER ═══════════ -->
<DrawerShell open={tbtDetailOpen} title={tbtDetail?.tbt_number ?? "TBT"} subtitle={tbtDetail?.topic ?? ""} width="max-w-xl" onclose={() => (tbtDetailOpen = false)}>
  {#if tbtDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if tbtDetail}
    <div class="p-6 space-y-5">
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{tbtDetail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Date</p><p class="text-sm text-neutral-900">{fmtDate(tbtDetail.conducted_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Conducted By</p><p class="text-sm text-neutral-900">{tbtDetail.conducted_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{tbtDetail.location || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Shift</p><p class="text-sm text-neutral-900 capitalize">{tbtDetail.shift}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Attendees</p><p class="text-sm font-semibold text-neutral-900">{tbtDetail.attendees_count}</p></div>
      </div>
      {#if tbtDetail.description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{tbtDetail.description}</p></div>{/if}
      {#if tbtDetail.key_points}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Key Points</p><p class="text-sm text-neutral-700 whitespace-pre-line font-medium">{tbtDetail.key_points}</p></div>{/if}
      {#if tbtDetail.attendees_names}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Attendees</p><p class="text-sm text-neutral-700 whitespace-pre-line">{tbtDetail.attendees_names}</p></div>{/if}
      {#if tbtDetail.follow_up_actions}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Follow-up Actions</p><p class="text-sm text-neutral-700 whitespace-pre-line">{tbtDetail.follow_up_actions}</p></div>{/if}
      {#if tbtDetail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{tbtDetail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ TBT CREATE DRAWER ═══════════ -->
<DrawerShell open={tbtCreateOpen} title="Record Toolbox Talk" subtitle="Log a safety briefing session" width="max-w-xl" onclose={() => (tbtCreateOpen = false)}>
  <form onsubmit={saveTBT} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Topic *</span><input bind:value={tbtForm.topic} placeholder="e.g. Heat Stress Prevention" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={tbtForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Date</span><DateInput bind:value={tbtForm.conducted_date} /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Conducted By</span><input bind:value={tbtForm.conducted_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={tbtForm.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Attendees Count</span><input type="number" min="0" bind:value={tbtForm.attendees_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={tbtForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Key Points</span><textarea bind:value={tbtForm.key_points} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Attendees Names</span><textarea bind:value={tbtForm.attendees_names} rows="2" placeholder="Comma or line-separated" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Follow-up Actions</span><textarea bind:value={tbtForm.follow_up_actions} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={tbtForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (tbtCreateOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillTBT} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={tbtSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{tbtSaving ? "Saving..." : "Record TBT"}</button>
    </div>
  </form>
</DrawerShell>
