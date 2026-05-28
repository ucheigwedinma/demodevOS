<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface Blueprint {
    id: number; name: string; description: string; status: string; status_display: string;
    source_template: number | null; project: number | null;
    projected_duration_days: number; projected_total_cost: number;
    phase_count: number; created_by_name: string; created_at: string; updated_at: string;
  }

  interface TemplateListItem { id: number; name: string; template_type_display: string; phase_count: number; }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-amber-50 text-amber-700 border-amber-200",
    review: "bg-blue-50 text-blue-700 border-blue-200",
    committed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    archived: "bg-neutral-100 text-neutral-400 border-neutral-200",
  };

  let loading = $state(true);
  let blueprints = $state<Blueprint[]>([]);
  let templates = $state<TemplateListItem[]>([]);
  let statusFilter = $state("");
  let search = $state("");

  // Create modal
  let showCreateModal = $state(false);
  let createMode = $state<"custom" | "template" | "boq" | "merge" | null>(null);
  let selectedTemplateId = $state<number | null>(null);
  let selectedBomId = $state<number | null>(null);
  let boms = $state<{ id: number; bom_number: string; name: string }[]>([]);
  let newName = $state("");
  let newDescription = $state("");
  let creating = $state(false);

  const filtered = $derived.by(() => {
    let list = blueprints;
    if (statusFilter) list = list.filter(b => b.status === statusFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(b => b.name.toLowerCase().includes(q) || b.description.toLowerCase().includes(q));
    }
    return list;
  });

  const draftCount = $derived(blueprints.filter(b => b.status === "draft").length);
  const committedCount = $derived(blueprints.filter(b => b.status === "committed").length);

  function fmt(n: number): string { return `₦${Math.round(n).toLocaleString()}`; }
  function fmtM(n: number): string { return n >= 1_000_000 ? `₦${(n / 1_000_000).toFixed(1)}M` : fmt(n); }

  async function loadBlueprints() {
    loading = true;
    try {
      const [bpRes, tmplRes, bomRes] = await Promise.all([
        api.get<{ results: Blueprint[] }>("/projects/blueprints/", { page_size: "100" }),
        api.get<{ results: TemplateListItem[] }>("/settings/project-templates/", { page_size: "50", is_active: "true" }),
        api.get<{ results: { id: number; bom_number: string; name: string }[] }>("/bom/", { page_size: "100" }),
      ]);
      blueprints = bpRes.results;
      templates = tmplRes.results;
      boms = bomRes.results;
    } catch { toast.error("Load failed", "Could not load blueprints."); }
    finally { loading = false; }
  }

  // Multi-BOQ merge
  let selectedBomIds = $state<number[]>([]);

  function toggleBomSelection(id: number) {
    if (selectedBomIds.includes(id)) selectedBomIds = selectedBomIds.filter(x => x !== id);
    else selectedBomIds = [...selectedBomIds, id];
  }

  function openCreate(mode: "custom" | "template" | "boq" | "merge") {
    createMode = mode;
    selectedTemplateId = templates.length > 0 ? templates[0].id : null;
    selectedBomId = boms.length > 0 ? boms[0].id : null;
    selectedBomIds = [];
    newName = "";
    newDescription = "";
    showCreateModal = true;
  }

  async function createBlueprint() {
    creating = true;
    try {
      if (createMode === "boq" && selectedBomId) {
        const result = await api.post<{ blueprint_id: number; blueprint_name: string }>("/projects/blueprints/generate-from-boq/", {
          bom_id: selectedBomId,
        });
        toast.success("Blueprint generated", `"${result.blueprint_name}" created from BOQ with ${(result as any).tasks_created} tasks.`);
        showCreateModal = false;
        await loadBlueprints();
        return;
      }

      if (createMode === "merge" && selectedBomIds.length >= 2) {
        const result = await api.post<{ blueprint_id: number; blueprint_name: string; boms_merged: number }>("/projects/blueprints/merge-from-boqs/", {
          bom_ids: selectedBomIds,
          name: newName.trim() || undefined,
        });
        toast.success("Blueprint merged", `"${result.blueprint_name}" created from ${result.boms_merged} BOMs with ${(result as any).tasks_created} tasks.`);
        showCreateModal = false;
        await loadBlueprints();
        return;
      }

      if (!newName.trim()) { toast.error("Missing data", "Blueprint name is required."); return; }

      const bp = await api.post<Blueprint>("/projects/blueprints/", {
        name: newName.trim(),
        description: newDescription.trim(),
        status: "draft",
      });

      if (createMode === "template" && selectedTemplateId) {
        await api.post(`/projects/blueprints/${bp.id}/seed-from-template/`, {
          template_id: selectedTemplateId,
        });
        toast.success("Blueprint created", `"${newName}" has been seeded from the template.`);
      } else {
        toast.success("Blueprint created", `"${newName}" is ready for planning.`);
      }

      showCreateModal = false;
      await loadBlueprints();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Create failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Create failed", "Could not create blueprint.");
    } finally { creating = false; }
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillBlueprint() {
    const names = [
      "Abuja Solar Farm Phase 2 — Execution Plan",
      "Lagos Mixed-Use Tower — Pre-Construction Blueprint",
      "Port Harcourt Residential Estate — Foundation to Handover",
      "Kano Industrial Warehouse Complex — Fast-Track Build",
      "Lekki Smart Apartments — Standard Delivery Plan",
      "Victoria Island Office Tower — Economy Build Strategy",
    ];
    const descriptions = [
      "Complete execution blueprint covering site preparation, structural works, MEP installation, and commissioning. Includes BoQ, resource allocation, and risk mitigation strategy.",
      "Pre-construction planning document with phased procurement, contractor mobilization, and regulatory compliance checkpoints.",
      "Full lifecycle plan from foundation through finishing and handover. Weather-adjusted schedule for rainy season mitigation.",
      "Compressed timeline blueprint with parallel execution tracks and overtime provisions. Higher risk tolerance for accelerated delivery.",
      "Standard delivery plan with balanced cost, timeline, and quality controls. Suitable for repeat deployment across similar projects.",
      "Cost-optimized blueprint with phased procurement and smaller crew sizes. Extended timeline to minimize capital expenditure peaks.",
    ];
    const idx = Math.floor(Math.random() * names.length);
    newName = names[idx];
    newDescription = descriptions[idx];
  }

  async function commitBlueprint(id: number) {
    try {
      const result = await api.post<{ project_id?: number; error?: string }>(`/projects/blueprints/${id}/commit/`, {});
      if (result?.error) {
        toast.error("Commit failed", result.error);
        return;
      }
      toast.success("Blueprint committed", "Project has been created from the blueprint.");
      await loadBlueprints();
      if (result.project_id) goto(`/projects/${result.project_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = (err.data?.detail as string)
          || (err.data?.error as string)
          || Object.values(err.fieldErrors).flat().join(" ")
          || "Could not commit blueprint.";
        toast.error("Commit failed", detail);
      } else {
        toast.error("Commit failed", "Could not commit blueprint.");
      }
    }
  }

  async function deleteBlueprint(id: number) {
    try {
      await api.delete(`/projects/blueprints/${id}/`);
      toast.success("Deleted", "Blueprint has been removed.");
      await loadBlueprints();
    } catch { toast.error("Delete failed", "Could not delete blueprint."); }
  }

  onMount(() => { loadBlueprints(); });
</script>

<svelte:head><title>Blueprints | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Projects</p>
      <h1 class="mt-2 text-xl font-bold text-neutral-900">Project Blueprints</h1>
      <p class="mt-1 text-sm text-neutral-500">Authored project plans — the single source of truth for execution.</p>
    </div>
    <div class="flex gap-2">
      <button onclick={() => openCreate("merge")} class="rounded-lg border border-violet-200 bg-violet-50 px-4 py-2.5 text-sm font-medium text-violet-700 hover:bg-violet-100">
        Merge BOQs
      </button>
      <button onclick={() => openCreate("boq")} class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100">
        Generate from BOQ
      </button>
      <button onclick={() => openCreate("template")} class="rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
        Create from Template
      </button>
      <button onclick={() => openCreate("custom")} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800">
        Create Custom
      </button>
    </div>
  </div>

  <!-- Stats + Filters -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
    <div class="flex gap-3">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{draftCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Drafts</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-600 tabular-nums">{committedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Committed</p>
      </div>
    </div>
    <div class="flex-1 relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input bind:value={search} class="w-full rounded-lg border border-neutral-200 bg-white pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search blueprints..." />
    </div>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="review">Under Review</option>
      <option value="committed">Committed</option>
      <option value="archived">Archived</option>
    </select>
  </div>

  <!-- Blueprint Cards -->
  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading blueprints...</div>
  {:else if filtered.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <p class="text-sm text-neutral-500">{search || statusFilter ? "No blueprints match your filters." : "No blueprints yet. Create your first project plan."}</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each filtered as bp (bp.id)}
        <div class="rounded-xl border border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-md">
          <!-- Header -->
          <div class="flex items-start justify-between gap-2 mb-3">
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-bold text-neutral-900 truncate">{bp.name}</h3>
              {#if bp.description}
                <p class="text-xs text-neutral-500 mt-0.5 line-clamp-2">{bp.description}</p>
              {/if}
            </div>
            <span class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[bp.status] || STATUS_COLORS.draft}">
              {bp.status_display}
            </span>
          </div>

          <!-- Metrics -->
          <div class="grid grid-cols-3 gap-2 mb-3">
            <div class="rounded-lg bg-neutral-50 p-2 text-center">
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{bp.phase_count}</p>
              <p class="text-[8px] font-semibold text-neutral-400 uppercase">Phases</p>
            </div>
            <div class="rounded-lg bg-neutral-50 p-2 text-center">
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{bp.projected_duration_days || "—"}<span class="text-[8px] font-normal text-neutral-400">{bp.projected_duration_days ? "d" : ""}</span></p>
              <p class="text-[8px] font-semibold text-neutral-400 uppercase">Duration</p>
            </div>
            <div class="rounded-lg bg-neutral-50 p-2 text-center">
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{bp.projected_total_cost > 0 ? fmtM(bp.projected_total_cost) : "—"}</p>
              <p class="text-[8px] font-semibold text-neutral-400 uppercase">Budget</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between pt-3 border-t border-neutral-100">
            <div class="text-[10px] text-neutral-400">
              {bp.created_by_name ? `By ${bp.created_by_name}` : ""} &middot; {new Date(bp.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
              {#if bp.project}
                <span class="ml-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">Project #{bp.project}</span>
              {/if}
            </div>
            <div class="flex gap-1">
              {#if bp.status === "draft"}
                <button onclick={() => goto(`/project-planning?blueprint=${bp.id}`)} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800">Build / Edit</button>
                <button onclick={() => commitBlueprint(bp.id)} class="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-emerald-700">Commit</button>
                <button onclick={() => deleteBlueprint(bp.id)} class="rounded-md border border-neutral-200 px-2 py-1 text-neutral-400 hover:text-red-500 hover:border-red-200 transition-colors" title="Delete">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                </button>
              {:else if bp.status === "committed" && bp.project}
                <button onclick={() => goto(`/projects/${bp.project}`)} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800">View Project</button>
                <button onclick={() => goto(`/project-planning?blueprint=${bp.id}`)} class="rounded-md border border-neutral-200 px-2.5 py-1 text-[10px] font-medium text-neutral-600 hover:bg-neutral-50">Edit Plan</button>
              {:else}
                <button onclick={() => goto(`/project-planning?blueprint=${bp.id}`)} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800">Open</button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Create Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="relative w-full max-w-md rounded-xl bg-white shadow-2xl p-6">
      <button onclick={() => (showCreateModal = false)} class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>

      <h3 class="text-base font-semibold text-neutral-900 mb-4">
        {createMode === "template" ? "Create from Template" : createMode === "boq" ? "Generate from BOQ" : createMode === "merge" ? "Merge Multiple BOQs" : "Create Custom Blueprint"}
      </h3>

      <div class="space-y-4">
        {#if createMode !== "boq"}
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Blueprint Name</span>
            <input bind:value={newName} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Abuja Solar Phase 2 Plan" />
          </label>

          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Description</span>
            <textarea bind:value={newDescription} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Brief description of this plan"></textarea>
          </label>
        {/if}

        {#if createMode === "template"}
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Base Template</span>
            <select bind:value={selectedTemplateId} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each templates as tmpl}
                <option value={tmpl.id}>{tmpl.name} ({tmpl.template_type_display}) — {tmpl.phase_count} phases</option>
              {/each}
            </select>
            <p class="mt-1 text-[10px] text-neutral-400">Template data will be copied into the blueprint. You can edit everything after.</p>
          </label>
        {:else if createMode === "boq"}
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Source Bill of Materials</span>
            <select bind:value={selectedBomId} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each boms as bom}
                <option value={bom.id}>{bom.bom_number} — {bom.name}</option>
              {/each}
            </select>
            <p class="mt-1 text-[10px] text-neutral-400">The engine will map BOQ categories to templates, calculate durations from quantities, and auto-generate the WBS.</p>
          </label>
          <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
            <p class="text-xs text-emerald-700 font-medium">Route B: BOQ-Driven Planning</p>
            <p class="mt-1 text-[10px] text-emerald-600">BOQ items → category mapping → template expansion → duration calculation → auto-generated blueprint. Name and structure are derived automatically.</p>
          </div>
        {:else if createMode === "merge"}
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Blueprint Name (optional)</span>
            <input bind:value={newName} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Auto-generated if left empty" />
          </label>
          <div>
            <span class="mb-1.5 block text-xs font-medium text-neutral-700">Select BOMs to Merge (min 2)</span>
            <div class="max-h-48 overflow-y-auto rounded-lg border border-neutral-200 divide-y divide-neutral-50">
              {#each boms as bom}
                <label class="flex items-center gap-3 px-3 py-2.5 hover:bg-neutral-50 cursor-pointer">
                  <input type="checkbox" checked={selectedBomIds.includes(bom.id)} onchange={() => toggleBomSelection(bom.id)} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-neutral-900 truncate">{bom.name}</p>
                    <p class="text-[10px] text-neutral-400">{bom.bom_number}</p>
                  </div>
                </label>
              {/each}
            </div>
            <p class="mt-1 text-[10px] text-neutral-400">{selectedBomIds.length} selected — {selectedBomIds.length >= 2 ? "ready to merge" : "select at least 2"}</p>
          </div>
          <div class="rounded-lg border border-violet-200 bg-violet-50 p-3">
            <p class="text-xs text-violet-700 font-medium">Multi-BOQ Merge</p>
            <p class="mt-1 text-[10px] text-violet-600">Combines Structural + Architectural + MEP (or any combination) into a single unified blueprint with cross-phase dependencies.</p>
          </div>
        {:else}
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-xs text-neutral-500">You'll start with an empty plan. Use the Project Planner to build the WBS, dependencies, schedule, and cost projections.</p>
          </div>
        {/if}
      </div>

      <div class="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-neutral-100">
        {#if isDev}
          <button type="button" onclick={devFillBlueprint} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
        {/if}
        <button onclick={() => (showCreateModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createBlueprint} disabled={creating} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
          {creating ? "Creating..." : "Create Blueprint"}
        </button>
      </div>
    </div>
  </div>
{/if}
