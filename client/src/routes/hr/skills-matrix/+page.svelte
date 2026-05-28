<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { SkillListItem, SkillCategory, SkillProficiency, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<SkillListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterCategory = $state("");
  let filterProficiency = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({ employee: "", name: "", category: "technical" as SkillCategory, proficiency: "beginner" as SkillProficiency, years_experience: "0", is_primary: false, verified: false, verified_by: "", verified_date: "", notes: "" });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const categoryLabels: Record<SkillCategory, string> = { technical: "Technical", management: "Management", soft: "Soft Skill", domain: "Domain Knowledge", regulatory: "Regulatory" };
  const proficiencyLabels: Record<SkillProficiency, string> = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced", expert: "Expert" };
  const proficiencyBadge: Record<SkillProficiency, string> = { beginner: "bg-neutral-100 text-neutral-500", intermediate: "bg-neutral-200 text-neutral-600", advanced: "bg-neutral-700 text-white", expert: "bg-neutral-900 text-white" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterCategory) params.category = filterCategory;
      if (filterProficiency) params.proficiency = filterProficiency;
      const res = await api.get<PaginatedResponse<SkillListItem>>("/hr/skills/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", name: "", category: "technical", proficiency: "beginner", years_experience: "0", is_primary: false, verified: false, verified_by: "", verified_date: "", notes: "" }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: SkillListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/skills/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.name = d.name;
      form.category = d.category;
      form.proficiency = d.proficiency;
      form.years_experience = String(d.years_experience);
      form.is_primary = d.is_primary;
      form.verified = d.verified;
      form.verified_by = String(d.verified_by ?? "");
      form.verified_date = d.verified_date ?? "";
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { name: form.name, category: form.category, proficiency: form.proficiency, years_experience: Number(form.years_experience) || 0, is_primary: form.is_primary, verified: form.verified, notes: form.notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.verified_by) payload.verified_by = Number(form.verified_by);
      if (form.verified_date) payload.verified_date = form.verified_date;
      if (isEditing) { await api.patch(`/hr/skills/${editingId}/`, payload); toast.success("Skill updated"); }
      else { await api.post("/hr/skills/", payload); toast.success("Skill created"); }
      showSlideOver = false; resetForm(); fetchItems();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const message = err.fieldErrors.non_field_errors?.[0] ?? Object.values(err.fieldErrors)[0]?.[0] ?? "Please fix the highlighted fields and try again.";
        toast.error("Validation error", message);
      }
      else toast.error("Failed to save");
    } finally { saving = false; }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(v: string) { searchQuery = v; clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300); }
  function goToPage(p: number) { if (p >= 1 && p <= totalPages) { currentPage = p; fetchItems(); } }
  function fieldError(f: string): string { return fieldErrors[f]?.[0] ?? ""; }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Skills Matrix</h1>
      <p class="mt-1 text-sm text-neutral-500">Track workforce skills, proficiencies, and capabilities</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Skill
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search skills..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterCategory} onchange={(e) => { filterCategory = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Categories</option>
      {#each Object.entries(categoryLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterProficiency} onchange={(e) => { filterProficiency = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Levels</option>
      {#each Object.entries(proficiencyLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterCategory || filterProficiency ? "No skills match your filters" : "No skills recorded yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Skill</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Category</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Experience</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Primary</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Verified</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Proficiency</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{categoryLabels[item.category] ?? item.category}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.years_experience} yr{Number(item.years_experience) !== 1 ? "s" : ""}</td>
              <td class="px-5 py-3.5 text-center">{#if item.is_primary}<span class="inline-block w-2 h-2 rounded-full bg-neutral-900"></span>{:else}<span class="inline-block w-2 h-2 rounded-full bg-neutral-200"></span>{/if}</td>
              <td class="px-5 py-3.5 text-center">{#if item.verified}<span class="text-neutral-900">&#10003;</span>{:else}<span class="text-neutral-300">&mdash;</span>{/if}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {proficiencyBadge[item.proficiency]}">{proficiencyLabels[item.proficiency]}</span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} skill{totalCount !== 1 ? "s" : ""}</span>
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

{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Skill" : "New Skill"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="sk-name" class="block text-sm font-medium text-neutral-700 mb-1">Skill Name <span class="text-red-500">*</span></label>
          <input id="sk-name" type="text" bind:value={form.name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('name') ? 'border-red-400' : ''}" />
          {#if fieldError("name")}<p class="text-xs text-red-500 mt-1">{fieldError("name")}</p>{/if}
        </div>
        {#if !isEditing}
          <div>
            <label for="sk-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="sk-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="sk-cat" class="block text-sm font-medium text-neutral-700 mb-1">Category</label>
            <select id="sk-cat" bind:value={form.category} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(categoryLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="sk-prof" class="block text-sm font-medium text-neutral-700 mb-1">Proficiency</label>
            <select id="sk-prof" bind:value={form.proficiency} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(proficiencyLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div>
          <label for="sk-exp" class="block text-sm font-medium text-neutral-700 mb-1">Years of Experience</label>
          <input id="sk-exp" type="number" step="0.5" min="0" bind:value={form.years_experience} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.is_primary} class="rounded border-neutral-300" />
            Primary Skill
          </label>
          <label class="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.verified} class="rounded border-neutral-300" />
            Verified
          </label>
        </div>
        {#if form.verified}
          <div>
            <label for="sk-vdate" class="block text-sm font-medium text-neutral-700 mb-1">Verification Date</label>
            <DateInput id="sk-vdate" bind:value={form.verified_date} />
          </div>
        {/if}
        <div>
          <label for="sk-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="sk-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>
