<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface MaterialItem { item: string; quantity: string; unit: string; essential: boolean; }
  interface QualityGate { check: string; is_required: boolean; }
  interface PhotoReq { description: string; is_mandatory: boolean; }

  interface TaskTemplate {
    id: number;
    name: string;
    description: string;
    assigned_role: string;
    priority: string;
    sort_order: number;
    reference_code: string;
    estimated_effort_hours: number | null;
    standard_duration_hours: number | null;
    complexity: string;
    category: string;
    crew_size: number | null;
    estimated_labor_cost: number | null;
    output_unit: string;
    equipment_type: string;
    is_milestone: boolean;
    status: string;
    required_materials: MaterialItem[];
    required_ppe: string[];
    quality_gates: QualityGate[];
    photo_requirements: PhotoReq[];
    sop_markdown: string;
    reviewer_role: string;
    predecessors: unknown[];
    definition_of_done: unknown[];
    tools_required: unknown[];
    activity: number | null;
  }

  const CATEGORIES = [
    { value: "", label: "All Categories" },
    { value: "electrical", label: "Electrical" },
    { value: "civil", label: "Civil" },
    { value: "mechanical", label: "Mechanical" },
    { value: "logistics", label: "Logistics" },
    { value: "legal_permits", label: "Legal / Permits" },
    { value: "finishing", label: "Finishing" },
    { value: "plumbing", label: "Plumbing" },
    { value: "safety", label: "Safety" },
    { value: "other", label: "Other" },
  ];

  const COMPLEXITY_COLORS: Record<string, string> = {
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    high: "bg-orange-50 text-orange-700 border-orange-200",
  };

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-500",
    active: "bg-emerald-50 text-emerald-700",
    archived: "bg-neutral-100 text-neutral-400",
  };

  let loading = $state(true);
  let templates = $state<TaskTemplate[]>([]);
  let search = $state("");
  let categoryFilter = $state("");
  let selectedId = $state<number | null>(null);
  let selectedTemplate = $state<TaskTemplate | null>(null);

  // Create/Edit drawer
  let showDrawer = $state(false);
  let drawerVisible = $state(false);
  let saving = $state(false);
  let form = $state(emptyForm());

  // Material row form
  let matItem = $state(""); let matQty = $state(""); let matUnit = $state(""); let matEssential = $state(true);
  // Quality gate row
  let qgCheck = $state(""); let qgRequired = $state(true);
  // Photo req row
  let photoDesc = $state(""); let photoMandatory = $state(true);
  // PPE row
  let ppeItem = $state("");

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const filtered = $derived.by(() => {
    let list = templates;
    if (categoryFilter) list = list.filter(t => t.category === categoryFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(t => t.name.toLowerCase().includes(q) || t.assigned_role.toLowerCase().includes(q) || t.category.toLowerCase().includes(q) || t.equipment_type.toLowerCase().includes(q));
    }
    return list;
  });

  function emptyForm() {
    return {
      name: "", description: "", assigned_role: "", priority: "medium", sort_order: "0",
      reference_code: "", estimated_effort_hours: "", standard_duration_hours: "",
      complexity: "medium", category: "", crew_size: "", estimated_labor_cost: "",
      output_unit: "", equipment_type: "", is_milestone: false, status: "active",
      reviewer_role: "", sop_markdown: "",
      required_materials: [] as MaterialItem[],
      required_ppe: [] as string[],
      quality_gates: [] as QualityGate[],
      photo_requirements: [] as PhotoReq[],
    };
  }

  function openCreate() {
    form = emptyForm();
    selectedId = null;
    showDrawer = true;
    requestAnimationFrame(() => { drawerVisible = true; });
  }

  function openEdit(t: TaskTemplate) {
    selectedId = t.id;
    form = {
      name: t.name, description: t.description, assigned_role: t.assigned_role,
      priority: t.priority, sort_order: String(t.sort_order), reference_code: t.reference_code,
      estimated_effort_hours: t.estimated_effort_hours ? String(t.estimated_effort_hours) : "",
      standard_duration_hours: t.standard_duration_hours ? String(t.standard_duration_hours) : "",
      complexity: t.complexity || "medium", category: t.category || "",
      crew_size: t.crew_size ? String(t.crew_size) : "",
      estimated_labor_cost: t.estimated_labor_cost ? String(t.estimated_labor_cost) : "",
      output_unit: t.output_unit || "", equipment_type: t.equipment_type || "",
      is_milestone: t.is_milestone, status: t.status || "active",
      reviewer_role: t.reviewer_role || "", sop_markdown: t.sop_markdown || "",
      required_materials: [...(t.required_materials || [])],
      required_ppe: [...(t.required_ppe || [])],
      quality_gates: [...(t.quality_gates || [])],
      photo_requirements: [...(t.photo_requirements || [])],
    };
    showDrawer = true;
    requestAnimationFrame(() => { drawerVisible = true; });
  }

  function closeDrawer() {
    drawerVisible = false;
    setTimeout(() => { showDrawer = false; }, 300);
  }

  async function loadTemplates() {
    loading = true;
    try {
      const res = await api.get<{ results: TaskTemplate[] }>("/settings/entity-templates/tasks/", { page_size: "500" });
      templates = res.results;
    } catch { toast.error("Load failed", "Could not load task templates."); }
    finally { loading = false; }
  }

  async function saveTemplate() {
    if (!form.name.trim()) { toast.error("Missing data", "Task name is required."); return; }
    saving = true;
    try {
      const payload = {
        ...form,
        sort_order: Number(form.sort_order) || 0,
        estimated_effort_hours: form.estimated_effort_hours ? Number(form.estimated_effort_hours) : null,
        standard_duration_hours: form.standard_duration_hours ? Number(form.standard_duration_hours) : null,
        crew_size: form.crew_size ? Number(form.crew_size) : null,
        estimated_labor_cost: form.estimated_labor_cost ? Number(form.estimated_labor_cost) : null,
      };
      if (selectedId) {
        await api.patch(`/settings/entity-templates/tasks/${selectedId}/`, payload);
        toast.success("Template updated", `"${form.name}" has been saved.`);
      } else {
        await api.post("/settings/entity-templates/tasks/", payload);
        toast.success("Template created", `"${form.name}" has been added to the library.`);
      }
      closeDrawer();
      await loadTemplates();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Save failed", "Could not save template.");
    } finally { saving = false; }
  }

  async function cloneTemplate(t: TaskTemplate) {
    try {
      const payload = { ...t, id: undefined, name: `${t.name} (Copy)`, status: "draft" };
      await api.post("/settings/entity-templates/tasks/", payload);
      toast.success("Cloned", `"${t.name}" has been cloned as a draft.`);
      await loadTemplates();
    } catch { toast.error("Clone failed", "Could not clone template."); }
  }

  function selectTemplate(t: TaskTemplate) {
    selectedTemplate = t;
  }

  function addMaterial() {
    if (!matItem.trim()) return;
    form.required_materials = [...form.required_materials, { item: matItem.trim(), quantity: matQty, unit: matUnit, essential: matEssential }];
    matItem = ""; matQty = ""; matUnit = ""; matEssential = true;
  }
  function removeMaterial(i: number) { form.required_materials = form.required_materials.filter((_, idx) => idx !== i); }
  function addQualityGate() { if (!qgCheck.trim()) return; form.quality_gates = [...form.quality_gates, { check: qgCheck.trim(), is_required: qgRequired }]; qgCheck = ""; qgRequired = true; }
  function removeQualityGate(i: number) { form.quality_gates = form.quality_gates.filter((_, idx) => idx !== i); }
  function addPhotoReq() { if (!photoDesc.trim()) return; form.photo_requirements = [...form.photo_requirements, { description: photoDesc.trim(), is_mandatory: photoMandatory }]; photoDesc = ""; photoMandatory = true; }
  function removePhotoReq(i: number) { form.photo_requirements = form.photo_requirements.filter((_, idx) => idx !== i); }
  function addPpe() { if (!ppeItem.trim()) return; form.required_ppe = [...form.required_ppe, ppeItem.trim()]; ppeItem = ""; }
  function removePpe(i: number) { form.required_ppe = form.required_ppe.filter((_, idx) => idx !== i); }

  function devFill() {
    const names = ["Battery Rack Assembly", "Inverter Installation", "DC Cable Routing", "Panel Mounting & Alignment", "Site Perimeter Fencing", "Concrete Foundation Pouring", "Rebar Tying & Placement", "Trench Excavation"];
    const cats = ["electrical", "electrical", "electrical", "mechanical", "civil", "civil", "civil", "civil"];
    const roles = ["Senior Electrician", "Electrical Technician", "Cable Technician", "Mechanical Fitter", "Civil Foreman", "Concrete Worker", "Steel Fixer", "Machine Operator"];
    const idx = Math.floor(Math.random() * names.length);
    form.name = names[idx];
    form.description = `Standard operating procedure for ${names[idx].toLowerCase()}. Follow all safety protocols and quality checkpoints.`;
    form.assigned_role = roles[idx];
    form.category = cats[idx];
    form.priority = "medium";
    form.complexity = ["low", "medium", "high"][Math.floor(Math.random() * 3)];
    form.standard_duration_hours = String(Math.floor(Math.random() * 16) + 2);
    form.estimated_effort_hours = String(Math.floor(Math.random() * 40) + 4);
    form.crew_size = String(Math.floor(Math.random() * 6) + 1);
    form.estimated_labor_cost = String(Math.floor(Math.random() * 200000) + 15000);
    form.output_unit = ["m²", "m³", "linear m", "units", "kg"][Math.floor(Math.random() * 5)];
    form.equipment_type = ["Excavator", "Tower Crane", "Concrete Pump", "Welding Machine", "Scaffolding"][Math.floor(Math.random() * 5)];
    form.status = "active";
    form.reviewer_role = "Site Engineer";
    form.sop_markdown = `## ${names[idx]}\n\n1. Verify materials are on-site\n2. Conduct toolbox talk\n3. Execute work per approved method statement\n4. Complete quality checklist\n5. Photograph completed work`;
    form.required_materials = [
      { item: "DC Cable (10mm)", quantity: "50", unit: "Meters", essential: true },
      { item: "Cable Ties (Pack)", quantity: "2", unit: "Packs", essential: false },
    ];
    form.required_ppe = ["Hard Hat", "Safety Boots", "High-Vis Vest", "Insulated Gloves"];
    form.quality_gates = [
      { check: "Voltage tested and within tolerance", is_required: true },
      { check: "Terminals torqued to spec", is_required: true },
      { check: "Visual inspection passed", is_required: false },
    ];
    form.photo_requirements = [
      { description: "Photo of completed installation", is_mandatory: true },
      { description: "Photo of label/serial number", is_mandatory: true },
    ];
  }

  $effect(() => { loadTemplates(); });
</script>

<svelte:head><title>Task Templates — Project Planner | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Task Template Library</h1>
      <p class="mt-1 text-sm text-neutral-500">Standardized task definitions that can be deployed into any project.</p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors shadow-sm">
      + New Template
    </button>
  </div>

  <!-- Filters -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
    <div class="flex-1 relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input bind:value={search} class="w-full rounded-lg border border-neutral-200 bg-white pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search by name, skill, or material..." />
    </div>
    <select bind:value={categoryFilter} class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      {#each CATEGORIES as cat}
        <option value={cat.value}>{cat.label}</option>
      {/each}
    </select>
    <span class="text-xs text-neutral-400 tabular-nums">{filtered.length} template(s)</span>
  </div>

  <!-- Template Grid -->
  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading templates...</div>
  {:else if filtered.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      {search || categoryFilter ? "No templates match your filters." : "No task templates yet. Click '+ New Template' to create your first SOP."}
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each filtered as tmpl (tmpl.id)}
        <div
          role="button"
          tabindex="0"
          onclick={() => { selectTemplate(tmpl); openEdit(tmpl); }}
          onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectTemplate(tmpl); openEdit(tmpl); } }}
          class="group rounded-xl border border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-md cursor-pointer"
        >
          <!-- Top row -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-bold text-neutral-900 truncate">{tmpl.name}</p>
              {#if tmpl.category}
                <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mt-0.5">{tmpl.category.replace("_", " ")}</p>
              {/if}
            </div>
            <span class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[tmpl.status] || STATUS_COLORS.draft}">
              {tmpl.status}
            </span>
          </div>

          {#if tmpl.description}
            <p class="mt-2 text-xs text-neutral-500 line-clamp-2">{tmpl.description}</p>
          {/if}

          <!-- Metrics row -->
          <div class="mt-3 flex flex-wrap gap-2">
            {#if tmpl.standard_duration_hours}
              <span class="rounded-md bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 tabular-nums">{tmpl.standard_duration_hours}h duration</span>
            {/if}
            {#if tmpl.estimated_effort_hours}
              <span class="rounded-md bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 tabular-nums">{tmpl.estimated_effort_hours}h effort</span>
            {/if}
            {#if tmpl.complexity}
              <span class="rounded-md border px-2 py-0.5 text-[10px] font-semibold {COMPLEXITY_COLORS[tmpl.complexity] || ''}">{tmpl.complexity}</span>
            {/if}
            {#if tmpl.is_milestone}
              <span class="rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 text-[10px] font-semibold">Milestone</span>
            {/if}
          </div>

          <!-- Bottom row -->
          <div class="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between">
            <div class="flex items-center gap-2 text-[10px] text-neutral-400">
              {#if tmpl.assigned_role}
                <span>{tmpl.assigned_role}</span>
              {/if}
              {#if tmpl.crew_size}
                <span>&middot; {tmpl.crew_size} crew</span>
              {/if}
              {#if tmpl.output_unit}
                <span>&middot; {tmpl.output_unit}</span>
              {/if}
            </div>
            <button
              onclick={(e) => { e.stopPropagation(); cloneTemplate(tmpl); }}
              class="rounded px-2 py-0.5 text-[10px] font-medium text-neutral-400 opacity-0 group-hover:opacity-100 hover:bg-neutral-100 hover:text-neutral-700 transition-all"
              title="Clone template"
            >
              Clone
            </button>
          </div>

          <!-- Material count badge -->
          {#if (tmpl.required_materials?.length || 0) > 0 || (tmpl.quality_gates?.length || 0) > 0}
            <div class="mt-2 flex gap-2">
              {#if tmpl.required_materials?.length}
                <span class="text-[9px] text-neutral-400">{tmpl.required_materials.length} material(s)</span>
              {/if}
              {#if tmpl.quality_gates?.length}
                <span class="text-[9px] text-neutral-400">{tmpl.quality_gates.length} quality gate(s)</span>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Task Template Drawer -->
{#if showDrawer}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity duration-300" style="opacity: {drawerVisible ? 1 : 0}" onclick={closeDrawer}></div>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white/95 backdrop-blur-xl shadow-2xl border-l border-neutral-200/60 transition-transform duration-300" style="transform: translateX({drawerVisible ? '0%' : '100%'})">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-base font-semibold text-neutral-900">{selectedId ? "Edit Template" : "New Task Template"}</h2>
      <button onclick={closeDrawer} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900 transition-colors" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- A. General Information -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">A — General Information</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="col-span-2 text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Task Name</span><input bind:value={form.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Battery Rack Assembly" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Standard Duration (hours)</span><input type="number" bind:value={form.standard_duration_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="6" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Complexity</span>
            <select bind:value={form.complexity} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Category</span>
            <select bind:value={form.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">None</option>
              {#each CATEGORIES.slice(1) as cat}<option value={cat.value}>{cat.label}</option>{/each}
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Status</span>
            <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option>
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Output Unit</span><input bind:value={form.output_unit} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="m², linear m, units" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Equipment Type</span><input bind:value={form.equipment_type} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Excavator, Crane" /></label>
        </div>
        <label class="block mt-3 text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Description / SOP</span>
          <textarea bind:value={form.sop_markdown} rows="5" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="## Procedure&#10;1. Verify materials...&#10;2. Conduct toolbox talk..."></textarea>
          <p class="mt-1 text-[10px] text-neutral-400">Supports Markdown formatting.</p>
        </label>
        <label class="flex items-center gap-3 mt-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50"><input type="checkbox" bind:checked={form.is_milestone} class="rounded border-neutral-300" /><span class="text-sm font-medium text-neutral-700">Mark as Project Milestone</span></label>
      </section>

      <!-- B. Resource & Skill Mapping -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">B — Resource & Skill Mapping</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Required Role</span><input bind:value={form.assigned_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Senior Electrician" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Reviewer Role</span><input bind:value={form.reviewer_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Site Engineer" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Crew Size</span><input type="number" bind:value={form.crew_size} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="3" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Est. Labour Cost (₦)</span><input type="number" bind:value={form.estimated_labor_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="45000" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Est. Man-Hours</span><input type="number" bind:value={form.estimated_effort_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="12" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Priority</span>
            <select bind:value={form.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
            </select>
          </label>
        </div>
      </section>

      <!-- C. Bill of Quantities -->
      <section class="rounded-xl border border-white/60 bg-white/70 p-4 shadow-sm" style="backdrop-filter: blur(8px)">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">C — Bill of Quantities (BoQ)</h3>
        {#if form.required_materials.length > 0}
          <div class="overflow-x-auto rounded-lg border border-neutral-200 mb-3">
            <table class="w-full text-xs">
              <thead><tr class="bg-neutral-50"><th class="px-3 py-1.5 text-left font-medium text-neutral-500">Material Item</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500 w-20">Qty</th><th class="px-3 py-1.5 text-left font-medium text-neutral-500 w-20">Unit</th><th class="px-3 py-1.5 text-center font-medium text-neutral-500 w-20">Essential?</th><th class="w-8"></th></tr></thead>
              <tbody class="divide-y divide-neutral-100">
                {#each form.required_materials as mat, i}
                  <tr><td class="px-3 py-1.5">{mat.item}</td><td class="px-3 py-1.5 text-right tabular-nums">{mat.quantity}</td><td class="px-3 py-1.5">{mat.unit}</td><td class="px-3 py-1.5 text-center"><span class="rounded-full px-1.5 py-0.5 text-[9px] font-semibold {mat.essential ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-400'}">{mat.essential ? "Yes" : "No"}</span></td><td class="px-1 py-1.5"><button onclick={() => removeMaterial(i)} class="text-neutral-300 hover:text-red-500">&times;</button></td></tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
        <div class="flex gap-2 items-end">
          <input bind:value={matItem} class="flex-2 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Item name" />
          <input bind:value={matQty} class="w-16 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Qty" />
          <input bind:value={matUnit} class="w-20 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Unit" />
          <label class="flex items-center gap-1 shrink-0"><input type="checkbox" bind:checked={matEssential} class="rounded border-neutral-300 w-3.5 h-3.5" /><span class="text-[10px] text-neutral-500">Req</span></label>
          <button onclick={addMaterial} class="shrink-0 rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800">Add</button>
        </div>
      </section>

      <!-- D. Quality & Compliance -->
      <section class="rounded-xl border border-white/60 bg-white/70 p-4 shadow-sm" style="backdrop-filter: blur(8px)">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">D — Quality & Compliance</h3>

        <!-- PPE -->
        <p class="text-xs font-medium text-neutral-600 mb-1.5">Safety Gear (PPE)</p>
        <div class="flex flex-wrap gap-1.5 mb-2">
          {#each form.required_ppe as ppe, i}
            <span class="inline-flex items-center gap-1 rounded-md bg-orange-50 border border-orange-200 px-2 py-0.5 text-[10px] font-medium text-orange-700">
              {ppe}<button onclick={() => removePpe(i)} class="text-orange-400 hover:text-red-500">&times;</button>
            </span>
          {/each}
        </div>
        <div class="flex gap-2 mb-4">
          <input bind:value={ppeItem} class="flex-1 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="e.g. Hard Hat" onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addPpe(); } }} />
          <button onclick={addPpe} class="shrink-0 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Add</button>
        </div>

        <!-- Quality Gates -->
        <p class="text-xs font-medium text-neutral-600 mb-1.5">Quality Gates</p>
        {#if form.quality_gates.length > 0}
          <div class="space-y-1 mb-2">
            {#each form.quality_gates as gate, i}
              <div class="flex items-center gap-2 rounded-lg bg-neutral-50 px-3 py-1.5">
                <span class="rounded-full px-1.5 py-0.5 text-[9px] font-semibold {gate.is_required ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-400'}">{gate.is_required ? "Required" : "Optional"}</span>
                <span class="text-xs text-neutral-700 flex-1">{gate.check}</span>
                <button onclick={() => removeQualityGate(i)} class="text-neutral-300 hover:text-red-500 text-xs">&times;</button>
              </div>
            {/each}
          </div>
        {/if}
        <div class="flex gap-2 mb-4">
          <input bind:value={qgCheck} class="flex-1 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="e.g. Voltage tested" onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addQualityGate(); } }} />
          <label class="flex items-center gap-1 shrink-0"><input type="checkbox" bind:checked={qgRequired} class="rounded border-neutral-300 w-3.5 h-3.5" /><span class="text-[10px] text-neutral-500">Req</span></label>
          <button onclick={addQualityGate} class="shrink-0 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Add</button>
        </div>

        <!-- Photo Requirements -->
        <p class="text-xs font-medium text-neutral-600 mb-1.5">Photo Requirements</p>
        {#if form.photo_requirements.length > 0}
          <div class="space-y-1 mb-2">
            {#each form.photo_requirements as photo, i}
              <div class="flex items-center gap-2 rounded-lg bg-neutral-50 px-3 py-1.5">
                <span class="rounded-full px-1.5 py-0.5 text-[9px] font-semibold {photo.is_mandatory ? 'bg-red-50 text-red-700' : 'bg-neutral-100 text-neutral-400'}">{photo.is_mandatory ? "Mandatory" : "Optional"}</span>
                <span class="text-xs text-neutral-700 flex-1">{photo.description}</span>
                <button onclick={() => removePhotoReq(i)} class="text-neutral-300 hover:text-red-500 text-xs">&times;</button>
              </div>
            {/each}
          </div>
        {/if}
        <div class="flex gap-2">
          <input bind:value={photoDesc} class="flex-1 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="e.g. Photo of completed wiring" onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addPhotoReq(); } }} />
          <label class="flex items-center gap-1 shrink-0"><input type="checkbox" bind:checked={photoMandatory} class="rounded border-neutral-300 w-3.5 h-3.5" /><span class="text-[10px] text-neutral-500">Req</span></label>
          <button onclick={addPhotoReq} class="shrink-0 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Add</button>
        </div>
      </section>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFill} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button onclick={closeDrawer} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button onclick={saveTemplate} disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : selectedId ? "Save Changes" : "Create Template"}</button>
    </div>
  </aside>
{/if}
