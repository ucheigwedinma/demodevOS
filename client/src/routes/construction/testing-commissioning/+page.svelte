<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    CommissioningPlanListItem,
    CommissioningPlanDetail,
    TCSystemType,
    TCDashboard,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── Tab ────────────────────────────────────────────────────────────────
  type Tab = "dashboard" | "plans" | "punch_list";
  let activeTab = $state<Tab>("dashboard");

  // ── Dashboard ─────────────────────────────────────────────────────────
  let dashboard = $state<TCDashboard | null>(null);
  let dashLoading = $state(true);

  // ── Plans ─────────────────────────────────────────────────────────────
  let plans = $state<CommissioningPlanListItem[]>([]);
  let plansLoading = $state(true);
  let plansTotal = $state(0);
  let plansPage = $state(1);
  let plansSearch = $state("");
  let plansSearchInput = $state("");
  let plansSystemFilter = $state("");
  let plansStatusFilter = $state("");
  let planSearchTimeout: ReturnType<typeof setTimeout> | undefined;
  const pageSize = 15;

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<CommissioningPlanDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"tests" | "punch">("tests");

  // Create drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());
  let testRows = $state<{ test_description: string; reference_standard: string; required_value: string }[]>([]);

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      name: "",
      system_type: "other" as TCSystemType,
      description: "",
      witness_required: false,
      witness_name: "",
      target_date: "",
      notes: "",
    };
  }

  function addTestRow() { testRows = [...testRows, { test_description: "", reference_standard: "", required_value: "" }]; }
  function removeTestRow(idx: number) { testRows = testRows.filter((_, i) => i !== idx); }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const SAMPLES = [
    {
      name: "Electrical Systems — Block A",
      system_type: "electrical" as TCSystemType,
      description: "Full electrical commissioning for Block A including LV switchboard, distribution boards, lighting, power outlets, and emergency systems.",
      witness_required: true,
      witness_name: "Client Rep — Engr. Bola Adeyemo",
      target_date: "2026-04-15",
      tests: [
        { test_description: "LV Switchboard insulation resistance", reference_standard: "BS 7671", required_value: "> 1.0 MΩ" },
        { test_description: "Earth continuity — main earth bar to DB", reference_standard: "BS 7671 Reg 612.2", required_value: "< 1.0 Ω" },
        { test_description: "Phase rotation verification", reference_standard: "Utility sync spec", required_value: "L1-L2-L3" },
        { test_description: "RCD trip time — 30mA Type A", reference_standard: "BS EN 61008", required_value: "< 300ms" },
        { test_description: "Emergency lighting duration test", reference_standard: "BS 5266-1", required_value: "≥ 3 hours" },
        { test_description: "Generator auto-start on mains failure", reference_standard: "Project spec GEN-01", required_value: "< 10 seconds" },
      ],
    },
    {
      name: "Fire Protection Systems — All Blocks",
      system_type: "fire" as TCSystemType,
      description: "Fire alarm, sprinkler, smoke detection, and emergency evacuation systems commissioning across all blocks.",
      witness_required: true,
      witness_name: "Fire Safety Consultant — Chief Okoro",
      target_date: "2026-04-20",
      tests: [
        { test_description: "Smoke detector response time", reference_standard: "BS 5839-1", required_value: "< 30 seconds" },
        { test_description: "Fire alarm audibility — all zones", reference_standard: "BS 5839-1", required_value: "≥ 65 dBA" },
        { test_description: "Sprinkler flow test — Zone 1", reference_standard: "BS EN 12845", required_value: "≥ 60 L/min per head" },
        { test_description: "Fire pump auto-start on pressure drop", reference_standard: "NFPA 20", required_value: "< 10 seconds" },
        { test_description: "Emergency exit signage illumination", reference_standard: "BS 5266-1", required_value: "≥ 1 lux on escape route" },
      ],
    },
  ];

  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form = {
      ...defaultForm(),
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      name: s.name,
      system_type: s.system_type,
      description: s.description,
      witness_required: s.witness_required,
      witness_name: s.witness_name,
      target_date: s.target_date,
    };
    testRows = s.tests.map(t => ({ ...t }));
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchDashboard() {
    dashLoading = true;
    try { dashboard = await api.get<TCDashboard>("/projects/commissioning-plans/dashboard/"); } catch { dashboard = null; }
    dashLoading = false;
  }

  async function fetchPlans() {
    plansLoading = true;
    try {
      const params: Record<string, string> = { page: String(plansPage), page_size: String(pageSize) };
      if (plansSearch) params.search = plansSearch;
      if (plansSystemFilter) params.system_type = plansSystemFilter;
      if (plansStatusFilter) params.status = plansStatusFilter;
      const [res, projs] = await Promise.all([
        api.get<PaginatedResponse<CommissioningPlanListItem>>("/projects/commissioning-plans/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      plans = res.results;
      plansTotal = res.count;
      if (projs) projects = projs.results;
    } catch { plans = []; plansTotal = 0; }
    plansLoading = false;
  }

  $effect(() => { if (activeTab === "dashboard") fetchDashboard(); });
  $effect(() => { if (activeTab === "plans") { void plansSearch; void plansSystemFilter; void plansStatusFilter; void plansPage; fetchPlans(); } });

  // Load dashboard on mount
  $effect(() => { fetchDashboard(); });

  function onPlanSearch(e: Event) {
    plansSearchInput = (e.target as HTMLInputElement).value;
    if (planSearchTimeout) clearTimeout(planSearchTimeout);
    planSearchTimeout = setTimeout(() => { plansSearch = plansSearchInput.trim(); plansPage = 1; }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "tests";
    try { detail = await api.get<CommissioningPlanDetail>(`/projects/commissioning-plans/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function savePlan(e: Event) {
    e.preventDefault();
    if (!form.name.trim() || !form.project) { toast.error("Validation", "Name and project are required."); return; }
    saving = true;
    try {
      const created = await api.post<CommissioningPlanListItem>("/projects/commissioning-plans/", {
        ...form,
        project: Number(form.project),
        target_date: form.target_date || null,
      });
      // Create test records (non-blocking — plan is already saved)
      let testErrors = 0;
      for (let i = 0; i < testRows.length; i++) {
        const row = testRows[i];
        if (!row.test_description.trim()) continue;
        try {
          await api.post(`/projects/commissioning-plans/${created.id}/tests/`, {
            sort_order: i,
            test_description: row.test_description,
            reference_standard: row.reference_standard,
            required_value: row.required_value,
          });
        } catch { testErrors++; }
      }
      if (testErrors > 0) {
        toast.success("Plan created", `"${form.name}" saved, but ${testErrors} test(s) failed to save.`);
      } else {
        toast.success("Commissioning plan created", `"${form.name}" saved with ${testRows.filter(r => r.test_description.trim()).length} tests.`);
      }
      createOpen = false;
      form = defaultForm();
      testRows = [];
      await fetchPlans();
      dashboard = null;
      fetchDashboard();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  const plansTotalPages = $derived(Math.max(1, Math.ceil(plansTotal / pageSize)));

  function resultColor(r: string): string {
    switch (r) {
      case "pass": return "bg-emerald-100 text-emerald-800";
      case "fail": return "bg-red-100 text-red-800";
      case "retest": return "bg-amber-100 text-amber-800";
      case "pending": return "bg-neutral-100 text-neutral-600";
      default: return "bg-neutral-100 text-neutral-400";
    }
  }

  function punchPriorityColor(p: string): string {
    switch (p) {
      case "critical": return "bg-red-100 text-red-800";
      case "major": return "bg-amber-100 text-amber-800";
      case "minor": return "bg-neutral-100 text-neutral-600";
      default: return "bg-neutral-100 text-neutral-600";
    }
  }

  function progressPct(plan: CommissioningPlanListItem): number {
    if (plan.test_count === 0) return 0;
    return Math.round((plan.pass_count / plan.test_count) * 100);
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "dashboard", label: "Status HUD" },
    { key: "plans", label: "Commissioning Plans" },
  ];
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Testing & Commissioning</h1>
      <p class="mt-1 text-sm text-neutral-500">Prove every system works before handover — test sheets, punch lists, and certification.</p>
    </div>
  </div>

  <!-- Tab Bar -->
  <div class="border-b border-neutral-200">
    <nav class="-mb-px flex gap-6">
      {#each tabs as tab}
        <button class="whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700'}" onclick={() => (activeTab = tab.key)}>{tab.label}</button>
      {/each}
    </nav>
  </div>

  <!-- ═══════════ DASHBOARD ═══════════ -->
  {#if activeTab === "dashboard"}
    {#if dashLoading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if dashboard}
      <!-- Go/No-Go Hero -->
      <div class="rounded-2xl p-6 shadow-lg {dashboard.go_no_go ? 'bg-linear-to-br from-emerald-600 to-emerald-800' : 'bg-linear-to-br from-red-600 to-red-800'} text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider {dashboard.go_no_go ? 'text-emerald-200' : 'text-red-200'}">System Status</p>
            <p class="mt-2 text-4xl font-bold">{dashboard.go_no_go ? "GO" : "NO-GO"}</p>
            <p class="mt-1 text-sm {dashboard.go_no_go ? 'text-emerald-200' : 'text-red-200'}">
              {dashboard.go_no_go ? "All mandatory tests passed — ready for handover" : "Outstanding failures or pending tests remain"}
            </p>
          </div>
          <div class="text-right space-y-2">
            <div class="rounded-lg bg-white/10 backdrop-blur-sm px-4 py-2">
              <p class="text-xs {dashboard.go_no_go ? 'text-emerald-200' : 'text-red-200'}">Pass Rate</p>
              <p class="text-2xl font-bold tabular-nums">{dashboard.pass_rate}%</p>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI Cards -->
      <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Plans</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{dashboard.total_plans}</p>
        </div>
        <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Tests Passed</p>
          <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{dashboard.passed_tests} / {dashboard.total_tests}</p>
        </div>
        <div class="rounded-xl border border-red-100 bg-red-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Tests Failed</p>
          <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{dashboard.failed_tests}</p>
        </div>
        <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Open Punch Items</p>
          <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{dashboard.open_punch_items}</p>
          {#if dashboard.critical_punch_items > 0}
            <p class="mt-0.5 text-xs text-red-600 font-semibold">{dashboard.critical_punch_items} critical</p>
          {/if}
        </div>
        <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Certified</p>
          <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{dashboard.plans_certified}</p>
        </div>
      </div>
    {/if}

  <!-- ═══════════ PLANS ═══════════ -->
  {:else if activeTab === "plans"}
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={plansSearchInput} oninput={onPlanSearch} placeholder="Search plans..." class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={plansSystemFilter} onchange={() => (plansPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Systems</option>
          <option value="electrical">Electrical</option>
          <option value="mechanical">Mechanical / HVAC</option>
          <option value="plumbing">Plumbing</option>
          <option value="fire">Fire Protection</option>
          <option value="elevator">Elevator</option>
          <option value="security">Security</option>
          <option value="bms">BMS</option>
          <option value="solar">Solar</option>
          <option value="structural">Structural</option>
          <option value="other">Other</option>
        </select>
        <select bind:value={plansStatusFilter} onchange={() => (plansPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="ready">Ready</option>
          <option value="in_progress">In Progress</option>
          <option value="passed">Passed</option>
          <option value="failed">Has Failures</option>
          <option value="certified">Certified</option>
        </select>
      </div>
      <button onclick={() => { form = defaultForm(); testRows = []; createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Plan</button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if plansLoading}
        <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
      {:else if plans.length === 0}
        <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No commissioning plans found.</p></div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[950px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Plan #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Name</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">System</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Tests</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Punch</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Target Date</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each plans as plan}
                {@const pct = progressPct(plan)}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(plan.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{plan.plan_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900 max-w-[220px] truncate">{plan.name}</td>
                  <td class="px-4 py-3 text-xs font-medium text-neutral-600">{plan.system_type_display}</td>
                  <td class="px-4 py-3"><StatusBadge status={plan.status} /></td>
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-2 bg-neutral-200 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all {plan.fail_count > 0 ? 'bg-red-500' : 'bg-emerald-500'}" style="width: {pct}%"></div>
                      </div>
                      <span class="text-xs font-semibold tabular-nums text-neutral-700 w-10 text-right">{pct}%</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="text-xs tabular-nums"><span class="text-emerald-600 font-semibold">{plan.pass_count}</span><span class="text-neutral-300">/</span><span class="text-neutral-600">{plan.test_count}</span></span>
                    {#if plan.fail_count > 0}<span class="ml-1 text-[10px] font-semibold text-red-600">{plan.fail_count}F</span>{/if}
                  </td>
                  <td class="px-4 py-3 text-center">
                    {#if plan.punch_count > 0}
                      <span class="text-xs font-semibold text-amber-600">{plan.punch_count}</span>
                    {:else}
                      <span class="text-xs text-neutral-400">--</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(plan.target_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{(plansPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(plansPage * pageSize, plansTotal)}</span> of <span class="font-semibold text-neutral-700">{plansTotal}</span></p>
          <div class="flex items-center gap-2">
            <button onclick={() => (plansPage = Math.max(1, plansPage - 1))} disabled={plansPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {plansPage} of {plansTotalPages}</span>
            <button onclick={() => (plansPage = Math.min(plansTotalPages, plansPage + 1))} disabled={plansPage >= plansTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- ═══════════ PLAN DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.plan_number ?? "Plan"} subtitle={detail?.name ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Status bar -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <StatusBadge status={detail.status} />
          <span class="text-xs font-medium text-neutral-600">{detail.system_type_display}</span>
        </div>
        {#if detail.witness_required}
          <span class="inline-flex items-center gap-1 text-xs font-semibold {detail.witness_present ? 'text-emerald-600' : 'text-amber-600'}">
            {detail.witness_present ? "Witness Present" : "Witness Required"}
            {#if detail.witness_name} — {detail.witness_name}{/if}
          </span>
        {/if}
      </div>

      <!-- Progress bar -->
      {#if detail.test_records}
      {@const totalTests = detail.test_records.length}
      {@const passedTests = detail.test_records.filter((t: { result: string; }) => t.result === "pass").length}
      {@const failedTests = detail.test_records.filter((t: { result: string; }) => t.result === "fail").length}
      {@const pct = totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0}
      <div class="rounded-lg border border-neutral-200 p-4">
        <div class="flex items-center justify-between mb-2">
          <p class="text-xs font-semibold text-neutral-600">Test Progress</p>
          <p class="text-sm font-bold tabular-nums {failedTests > 0 ? 'text-red-600' : 'text-emerald-600'}">{pct}%</p>
        </div>
        <div class="h-3 bg-neutral-200 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all {failedTests > 0 ? 'bg-red-500' : 'bg-emerald-500'}" style="width: {pct}%"></div>
        </div>
        <p class="mt-1 text-xs text-neutral-500">{passedTests} passed, {failedTests} failed, {totalTests - passedTests - failedTests} remaining</p>
      </div>
      {/if}

      <!-- Detail tabs -->
      <div class="border-b border-neutral-200">
        <nav class="-mb-px flex gap-4">
          <button class="border-b-2 px-1 pb-2 text-xs font-medium {detailTab === 'tests' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}" onclick={() => (detailTab = 'tests')}>Test Sheet ({detail.test_records.length})</button>
          <button class="border-b-2 px-1 pb-2 text-xs font-medium {detailTab === 'punch' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}" onclick={() => (detailTab = 'punch')}>Punch List ({detail.punch_items.length})</button>
        </nav>
      </div>

      {#if detailTab === "tests"}
        {#if detail.test_records.length === 0}
          <p class="text-sm text-neutral-500 text-center py-6">No tests defined yet.</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-neutral-50">
                <tr>
                  <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Test</th>
                  <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Standard</th>
                  <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Required</th>
                  <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actual</th>
                  <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Result</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each detail.test_records as test}
                  <tr class="{test.result === 'pass' ? 'bg-emerald-50/40' : test.result === 'fail' ? 'bg-red-50/40' : ''}">
                    <td class="px-3 py-2.5 text-xs text-neutral-900">{test.test_description}</td>
                    <td class="px-3 py-2.5 text-[11px] text-neutral-500">{test.reference_standard || "--"}</td>
                    <td class="px-3 py-2.5 text-center text-xs text-neutral-600">{test.required_value || "--"}</td>
                    <td class="px-3 py-2.5 text-center text-xs font-bold text-neutral-900">{test.actual_value || "--"}</td>
                    <td class="px-3 py-2.5 text-center">
                      <span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {resultColor(test.result)}">{test.result_display}</span>
                    </td>
                  </tr>
                  {#if test.fault_comment}
                    <tr class="bg-red-50/30">
                      <td colspan="5" class="px-3 py-1.5 text-[11px] text-red-700">Fault: {test.fault_comment}</td>
                    </tr>
                  {/if}
                  {#if test.retest_result}
                    <tr class="bg-amber-50/30">
                      <td colspan="5" class="px-3 py-1.5 text-[11px] text-amber-700">Retest ({fmtDate(test.retest_date)}): {test.retest_result_display} — {test.retest_notes}</td>
                    </tr>
                  {/if}
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      {:else}
        {#if detail.punch_items.length === 0}
          <p class="text-sm text-neutral-500 text-center py-6">No punch items. All clear.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.punch_items as punch}
              <div class="rounded-lg border {punch.priority === 'critical' ? 'border-red-200 bg-red-50/50' : 'border-neutral-200 bg-white'} p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-neutral-500">{punch.item_number}</span>
                    <span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {punchPriorityColor(punch.priority)}">{punch.priority_display}</span>
                  </div>
                  <StatusBadge status={punch.status} />
                </div>
                <p class="text-sm text-neutral-800">{punch.description}</p>
                {#if punch.corrective_action}
                  <p class="mt-1 text-xs text-neutral-600">Fix: {punch.corrective_action}</p>
                {/if}
                {#if punch.assigned_to}
                  <p class="mt-1 text-[11px] text-neutral-400">Assigned to: {punch.assigned_to}</p>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}

      {#if detail.description}
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.description}</p></div>
      {/if}
      {#if detail.notes}
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Commissioning Plan" subtitle="Define system tests for commissioning" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={savePlan} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Plan Name *</span><input bind:value={form.name} placeholder="e.g. Electrical Systems — Block A" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">System Type</span><select bind:value={form.system_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="electrical">Electrical</option><option value="mechanical">Mechanical / HVAC</option><option value="plumbing">Plumbing</option><option value="fire">Fire Protection</option><option value="elevator">Elevator</option><option value="security">Security</option><option value="bms">BMS</option><option value="solar">Solar</option><option value="structural">Structural</option><option value="other">Other</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Target Date</span><DateInput bind:value={form.target_date} /></label>
      <div class="space-y-2">
        <label class="flex items-center gap-2 pt-5"><input type="checkbox" bind:checked={form.witness_required} class="rounded" /><span class="text-xs font-medium text-neutral-600">Witness Required</span></label>
        {#if form.witness_required}
          <input bind:value={form.witness_name} placeholder="Witness name/role" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        {/if}
      </div>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <!-- Test Records -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-neutral-600">Test Sheet</span>
        <button type="button" onclick={addTestRow} class="rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200">+ Add Test</button>
      </div>
      {#if testRows.length > 0}
        <div class="space-y-2">
          {#each testRows as row, idx}
            <div class="rounded-lg border border-neutral-200 p-3 space-y-2 relative">
              <button type="button" onclick={() => removeTestRow(idx)} class="absolute top-2 right-2 text-neutral-400 hover:text-red-500 text-xs" aria-label="Remove">X</button>
              <input bind:value={row.test_description} placeholder="Test description (e.g. Insulation Resistance)" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
              <div class="grid grid-cols-2 gap-2">
                <input bind:value={row.reference_standard} placeholder="Reference standard" class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs" />
                <input bind:value={row.required_value} placeholder="Required value" class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs" />
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Plan"}</button>
    </div>
  </form>
</DrawerShell>
