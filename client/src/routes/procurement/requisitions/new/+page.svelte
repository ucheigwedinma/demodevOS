<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type {
    PurchaseRequisition,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let form = $state({
    title: "",
    requester: "",
    project: "",
    property: "",
    priority: "medium",
    required_date: "",
    budget_line_item: "",
    budget_code: "",
    cost_code: "",
    justification: "",
    notes: "",
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  type ReqForm = typeof form;
  const REQ_SAMPLES: ReqForm[] = [
    {
      title: "Ready-mix concrete — Block C foundations",
      requester: "David Mensah",
      project: "",
      property: "",
      priority: "high",
      required_date: new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "STRUCT-2026-004",
      cost_code: "",
      justification: "Foundation pour for Block C scheduled in two weeks. 380 m³ C40 concrete required per structural engineer's specification. Lead time from Lafarge is 7 working days — order must be placed this week to avoid programme delay.",
      notes: "Pump truck access via Gate 3 only. Coordinate with site logistics for 06:00 delivery slots.",
    },
    {
      title: "Structural steel — Level 12-15 framing",
      requester: "Priya Naidoo",
      project: "",
      property: "",
      priority: "urgent",
      required_date: new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "STRUCT-2026-007",
      cost_code: "",
      justification: "Tower crane standing time begins next Monday if steel is not on site. 42 tonnes of S355 universal beams and columns required for floors 12–15. Procurement delay will trigger VO for crane idle costs estimated at £8,500/day.",
      notes: "Mill certs and inspection release notes required before delivery acceptance. Contact QA team for sampling schedule.",
    },
    {
      title: "MEP ductwork — HVAC risers Block A",
      requester: "James Okafor",
      project: "",
      property: "",
      priority: "medium",
      required_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "MEP-2026-012",
      cost_code: "",
      justification: "First-fix HVAC installation on floors 5–10 commences in three weeks. Galvanised rectangular ductwork (1200×600 and 800×400 sections) plus fire dampers needed. Early order avoids clash with electrical rough-in programme.",
      notes: "Ductwork to be delivered in labelled bundles per floor level. Storage area allocated in basement car park zone D.",
    },
    {
      title: "Façade aluminium curtain wall panels",
      requester: "Amara Diallo",
      project: "",
      property: "",
      priority: "high",
      required_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "EXT-2026-003",
      cost_code: "",
      justification: "Building envelope programme requires curtain wall installation to begin on the north elevation by end of month. 240 unitised panels (1500×3600 mm) with double-glazed IGUs. Factory lead time is 4 weeks — order cutoff is this Friday.",
      notes: "Panels arrive on flatbed trucks — crane offload required. Verify tower crane radius covers north elevation laydown area.",
    },
  ];

  let reqDevIdx = 0;

  function devFillRequisition() {
    const sample = REQ_SAMPLES[reqDevIdx % REQ_SAMPLES.length];
    reqDevIdx++;
    form = {
      ...sample,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      property: form.property,
      budget_line_item: form.budget_line_item,
      cost_code: form.cost_code,
    };
  }
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200" });
      projects = res.results;
    } catch {
      projects = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  $effect(() => {
    fetchProjects();
    fetchProperties();
    Promise.all([
      fetchBudgetLineOptions().then((rows) => (budgetLines = rows)),
      fetchCostCodeOptions().then((rows) => (costCodes = rows)),
    ]);
  });

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        requester: form.requester,
        project: form.project ? Number(form.project) : null,
        property: form.property ? Number(form.property) : null,
        priority: form.priority,
        required_date: form.required_date || null,
        budget_line_item: form.budget_line_item ? Number(form.budget_line_item) : null,
        budget_code: form.budget_code,
        cost_code: form.cost_code,
        justification: form.justification,
        notes: form.notes,
      };
      const result = await api.post<PurchaseRequisition>("/procurement/requisitions/", payload);
      toast.success("Requisition created", `"${result.title}" has been added`);
      goto(`/procurement/requisitions/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the requisition");
      }
    }
    saving = false;
  }
</script>

<div class="max-w-2xl">
  <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "Requisitions", href: "/procurement/requisitions" }, { label: "New Requisition" }]} />
  <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">New Requisition</h1>

  <form onsubmit={handleSubmit} class="space-y-6">
    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
        <input
          bind:value={form.title}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Enter requisition title"
        />
        {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requester</span>
        <input
          bind:value={form.requester}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Name of requester"
        />
        {#if fieldError("requester")}<p class="mt-1 text-xs text-red-500">{fieldError("requester")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={form.project}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">Select a project</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        {#if fieldError("project")}<p class="mt-1 text-xs text-red-500">{fieldError("project")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={form.property}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each properties as property}
            <option value={String(property.id)}>{property.name}</option>
          {/each}
        </select>
        {#if fieldError("property")}<p class="mt-1 text-xs text-red-500">{fieldError("property")}</p>{/if}
      </label>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</span>
          <select
            bind:value={form.priority}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          {#if fieldError("priority")}<p class="mt-1 text-xs text-red-500">{fieldError("priority")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Required Date</span>
          <DateInput bind:value={form.required_date} />
          {#if fieldError("required_date")}<p class="mt-1 text-xs text-red-500">{fieldError("required_date")}</p>{/if}
        </label>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Line <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={form.budget_line_item}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">None</option>
            {#each budgetLines as line}
              <option value={String(line.id)}>{line.label}</option>
            {/each}
          </select>
          {#if fieldError("budget_line_item")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_line_item")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Code <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={form.cost_code}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">None</option>
            {#each costCodes as code}
              <option value={code.code}>{code.code} - {code.label}</option>
            {/each}
          </select>
          {#if fieldError("cost_code")}<p class="mt-1 text-xs text-red-500">{fieldError("cost_code")}</p>{/if}
        </label>
      </div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code <span class="text-neutral-400 font-normal">(optional)</span></span>
        <input
          bind:value={form.budget_code}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="e.g. DEPT-2024-001"
        />
        {#if fieldError("budget_code")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_code")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Justification</span>
        <textarea
          bind:value={form.justification}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Business justification for this purchase..."
        ></textarea>
        {#if fieldError("justification")}<p class="mt-1 text-xs text-red-500">{fieldError("justification")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
        <textarea
          bind:value={form.notes}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Additional notes..."
        ></textarea>
        {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
      </label>
    </div>

    <div class="flex gap-3">
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Create Requisition"}
      </button>
      {#if isDev}
        <button
          type="button"
          onclick={devFillRequisition}
          class="px-6 py-2.5 bg-orange-500 rounded-lg text-sm font-medium text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <a href="/procurement/requisitions" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
        Cancel
      </a>
    </div>
  </form>
</div>
