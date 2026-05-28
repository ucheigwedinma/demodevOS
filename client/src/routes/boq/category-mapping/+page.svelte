<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface Mapping { id: number; boq_category: string; template_phase: number; template_phase_name: string; template_name: string; default_production_rate: string | null; split_threshold: string | null; sort_order: number; }
  interface PhaseOption { id: number; name: string; template_name: string; }

  let loading = $state(true);
  let mappings = $state<Mapping[]>([]);
  let phaseOptions = $state<PhaseOption[]>([]);

  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let form = $state({
    boq_category: "",
    template_phase: "",
    default_production_rate: "",
    split_threshold: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const categories = [
    "Excavation", "Concrete", "Blockwork", "Structural Steel", "Roofing",
    "Plastering", "Painting", "Electrical", "Plumbing", "HVAC",
    "Tiling", "Glazing", "Waterproofing", "Landscaping", "MEP",
    "Finishing", "Formwork", "Reinforcement", "Piling", "Demolition",
  ];

  async function loadData() {
    loading = true;
    try {
      const [mapRes, phaseRes] = await Promise.all([
        api.get<{ results: Mapping[] }>("/boq-category-mapping/", { page_size: "100" }),
        api.get<{ results: { id: number; name: string; template: number }[] }>("/settings/project-templates/phases/", { page_size: "200" }),
      ]);
      mappings = mapRes.results;

      // Build phase options with template name
      const tmplRes = await api.get<{ results: { id: number; name: string }[] }>("/settings/project-templates/", { page_size: "50" });
      const tmplMap = new Map(tmplRes.results.map(t => [t.id, t.name]));
      phaseOptions = phaseRes.results.map(p => ({
        id: p.id,
        name: p.name,
        template_name: tmplMap.get(p.template) || "Unknown",
      }));
    } catch { toast.error("Load failed", "Could not load category mappings."); }
    finally { loading = false; }
  }

  function openCreate() {
    editingId = null;
    form = { boq_category: "", template_phase: "", default_production_rate: "", split_threshold: "" };
    showModal = true;
  }

  function openEdit(m: Mapping) {
    editingId = m.id;
    form = {
      boq_category: m.boq_category,
      template_phase: String(m.template_phase),
      default_production_rate: m.default_production_rate || "",
      split_threshold: m.split_threshold || "",
    };
    showModal = true;
  }

  async function save() {
    if (!form.boq_category.trim() || !form.template_phase) {
      toast.error("Missing fields", "Category and template phase are required.");
      return;
    }
    saving = true;
    try {
      const payload = {
        boq_category: form.boq_category.trim(),
        template_phase: Number(form.template_phase),
        default_production_rate: form.default_production_rate ? Number(form.default_production_rate) : null,
        split_threshold: form.split_threshold ? Number(form.split_threshold) : null,
      };
      if (editingId) {
        await api.patch(`/boq-category-mapping/${editingId}/`, payload);
        toast.success("Updated", `Mapping for "${form.boq_category}" saved.`);
      } else {
        await api.post("/boq-category-mapping/", payload);
        toast.success("Created", `Mapping for "${form.boq_category}" added.`);
      }
      showModal = false;
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not save mapping.");
    } finally { saving = false; }
  }

  async function deleteMapping(id: number) {
    if (!confirm("Delete this mapping?")) return;
    try {
      await api.delete(`/boq-category-mapping/${id}/`);
      toast.success("Deleted", "Mapping removed.");
      await loadData();
    } catch { toast.error("Failed", "Could not delete mapping."); }
  }

  function devFill() {
    const idx = Math.floor(Math.random() * categories.length);
    form.boq_category = categories[idx];
    if (phaseOptions.length > 0) form.template_phase = String(phaseOptions[Math.floor(Math.random() * phaseOptions.length)].id);
    form.default_production_rate = String(Math.floor(Math.random() * 20 + 5));
    form.split_threshold = String(Math.floor(Math.random() * 500 + 100));
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>Category Mapping | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Category Mapping</h1>
      <p class="mt-1 text-sm text-neutral-500">Map BOQ categories to planning templates. This drives the auto-generation engine (Route B).</p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800">+ New Mapping</button>
  </div>

  <!-- How it works -->
  <div class="rounded-xl border border-indigo-200 bg-indigo-50/50 p-5" style="backdrop-filter: blur(12px)">
    <h3 class="text-[10px] font-semibold text-indigo-500 uppercase tracking-widest mb-2">How It Works</h3>
    <div class="flex flex-wrap items-center gap-2 text-xs text-indigo-700">
      <span class="rounded-full border border-indigo-200 bg-white px-3 py-1 font-semibold">BOQ Category</span>
      <svg class="h-4 w-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
      <span class="rounded-full border border-indigo-200 bg-white px-3 py-1 font-semibold">Template Phase</span>
      <svg class="h-4 w-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
      <span class="rounded-full border border-indigo-200 bg-white px-3 py-1 font-semibold">Activities + Tasks</span>
      <svg class="h-4 w-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
      <span class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 font-semibold text-emerald-700">Auto-Generated WBS</span>
    </div>
    <p class="mt-2 text-[10px] text-indigo-500">When "Generate from BOQ" is used, items with category "Concrete" will map to the phase you define here, inheriting all its activities, task templates, and dependencies.</p>
  </div>

  {#if loading}
    <p class="py-20 text-center text-sm text-neutral-400">Loading...</p>
  {:else}

    <!-- KPIs -->
    <div class="grid grid-cols-3 gap-3">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total Mappings</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{mappings.length}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Categories Covered</p>
        <p class="mt-1 text-2xl font-bold text-emerald-700 tabular-nums">{new Set(mappings.map(m => m.boq_category)).size}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Templates Used</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{new Set(mappings.map(m => m.template_name)).size}</p>
      </div>
    </div>

    <!-- Mapping Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Mapping Rules</h3>
      </div>
      {#if mappings.length === 0}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-500">No mappings defined yet. Create your first mapping to enable BOQ-driven plan generation.</p>
          <button onclick={openCreate} class="mt-3 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800">Create First Mapping</button>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">BOQ Category</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Template</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Phase</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Production Rate</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Split Threshold</th>
                <th class="px-5 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each mappings as m}
                <tr class="hover:bg-neutral-50">
                  <td class="px-5 py-3">
                    <span class="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-xs font-semibold text-neutral-700">{m.boq_category}</span>
                  </td>
                  <td class="px-5 py-3 text-neutral-600">{m.template_name}</td>
                  <td class="px-5 py-3 font-medium text-neutral-900">{m.template_phase_name}</td>
                  <td class="px-5 py-3 text-center tabular-nums text-neutral-600">{m.default_production_rate ? `${m.default_production_rate}/day` : "—"}</td>
                  <td class="px-5 py-3 text-center tabular-nums text-neutral-600">{m.split_threshold || "—"}</td>
                  <td class="px-5 py-3 text-right">
                    <div class="flex items-center justify-end gap-1">
                      <button onclick={() => openEdit(m)} class="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900" title="Edit">
                        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" /></svg>
                      </button>
                      <button onclick={() => deleteMapping(m.id)} class="rounded-md p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-500" title="Delete">
                        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- Create/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">{editingId ? "Edit Mapping" : "New Category Mapping"}</h2>

      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">BOQ Category *</span>
          <div class="relative">
            <input list="cat-suggestions" bind:value={form.boq_category} placeholder="e.g. Concrete, Excavation" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            <datalist id="cat-suggestions">
              {#each categories as cat}<option value={cat}></option>{/each}
            </datalist>
          </div>
        </label>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Template Phase *</span>
          <select bind:value={form.template_phase} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select phase...</option>
            {#each phaseOptions as p}
              <option value={String(p.id)}>{p.template_name} → {p.name}</option>
            {/each}
          </select>
          <p class="mt-1 text-[10px] text-neutral-400">All activities and task templates from this phase will be used to generate the WBS.</p>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Production Rate (units/day)</span>
            <input type="number" step="0.01" bind:value={form.default_production_rate} placeholder="e.g. 10" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Split Threshold (qty)</span>
            <input type="number" step="1" bind:value={form.split_threshold} placeholder="e.g. 200" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={save} disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : editingId ? "Save Changes" : "Create Mapping"}</button>
      </div>
    </div>
  </div>
{/if}
