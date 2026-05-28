<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    RiskCategory,
    RiskCategoryType,
    RiskMitigationRule,
    RiskSeverity,
    RiskScoreMatrix,
    RoleListItem,
    PaginatedResponse,
  } from "$lib/types";

  type Tab = "categories" | "mitigation" | "matrix";
  let activeTab = $state<Tab>("categories");

  const PAGE_SIZE_OPTIONS = [10, 20, 50];

  // Risk Categories
  let categories = $state<RiskCategory[]>([]);
  let loadingCategories = $state(true);
  let showCategoryForm = $state(false);
  let editingCategoryId = $state<number | null>(null);
  let categoryForm = $state({
    name: "",
    category_type: "financial" as RiskCategoryType,
    description: "",
    is_active: true,
  });
  let categorySearch = $state("");
  let categoryTypeFilter = $state("");
  let categoryStatusFilter = $state("");
  let categorySort = $state("name_asc");
  let categoryPage = $state(1);
  let categoryPageSize = $state(10);

  // Mitigation Rules
  let mitigationRules = $state<RiskMitigationRule[]>([]);
  let loadingRules = $state(true);
  let showRuleForm = $state(false);
  let editingRuleId = $state<number | null>(null);
  let ruleForm = $state({
    risk_category: 0,
    severity: "medium" as RiskSeverity,
    assign_to_role: null as number | null,
    escalation_required: false,
    response_time_hours: null as number | null,
    is_active: true,
  });
  let ruleSearch = $state("");
  let ruleCategoryFilter = $state("");
  let ruleSeverityFilter = $state("");
  let ruleStatusFilter = $state("");
  let ruleEscalationFilter = $state("");
  let ruleSort = $state("category_asc");
  let rulePage = $state(1);
  let rulePageSize = $state(10);

  // Score Matrix
  let matrix = $state<RiskScoreMatrix | null>(null);
  let loadingMatrix = $state(true);
  let editingMatrix = $state(false);
  let matrixForm = $state({
    likelihood: {} as Record<string, number>,
    impact: {} as Record<string, number>,
    thresholds: {} as Record<string, number>,
  });

  // Roles (for mitigation rule dropdown)
  let roles = $state<RoleListItem[]>([]);

  const categoryTypeOptions: { value: RiskCategoryType; label: string }[] = [
    { value: "financial", label: "Financial" },
    { value: "regulatory", label: "Regulatory" },
    { value: "construction", label: "Construction" },
    { value: "market", label: "Market" },
    { value: "operational", label: "Operational" },
    { value: "environmental", label: "Environmental" },
    { value: "legal", label: "Legal" },
    { value: "technical", label: "Technical" },
  ];

  const severityOptions: { value: RiskSeverity; label: string; color: string }[] = [
    { value: "low", label: "Low", color: "bg-green-100 text-green-800" },
    { value: "medium", label: "Medium", color: "bg-yellow-100 text-yellow-800" },
    { value: "high", label: "High", color: "bg-orange-100 text-orange-800" },
    { value: "critical", label: "Critical", color: "bg-red-100 text-red-800" },
  ];

  function getCategoryTypeColor(type: RiskCategoryType): string {
    const colors: Record<RiskCategoryType, string> = {
      financial: "bg-blue-100 text-blue-800",
      regulatory: "bg-purple-100 text-purple-800",
      construction: "bg-orange-100 text-orange-800",
      market: "bg-green-100 text-green-800",
      operational: "bg-yellow-100 text-yellow-800",
      environmental: "bg-emerald-100 text-emerald-800",
      legal: "bg-pink-100 text-pink-800",
      technical: "bg-cyan-100 text-cyan-800",
    };
    return colors[type] || "bg-neutral-100 text-neutral-800";
  }

  function getSeverityColor(severity: RiskSeverity): string {
    return severityOptions.find(s => s.value === severity)?.color || "bg-neutral-100 text-neutral-800";
  }

  function severityRank(severity: RiskSeverity): number {
    const rank: Record<RiskSeverity, number> = {
      low: 1,
      medium: 2,
      high: 3,
      critical: 4,
    };
    return rank[severity] ?? 0;
  }

  function dateKey(value: string | null | undefined): number {
    if (!value) return 0;
    const timestamp = Date.parse(value);
    return Number.isNaN(timestamp) ? 0 : timestamp;
  }

  const filteredCategories = $derived.by(() => {
    let rows = categories.filter((cat) => {
      if (categoryTypeFilter && cat.category_type !== categoryTypeFilter) return false;
      if (categoryStatusFilter === "active" && !cat.is_active) return false;
      if (categoryStatusFilter === "inactive" && cat.is_active) return false;
      if (!categorySearch.trim()) return true;
      const needle = categorySearch.trim().toLowerCase();
      const haystack = `${cat.name} ${cat.category_type_display} ${cat.description}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (categorySort === "name_desc") return b.name.localeCompare(a.name);
      if (categorySort === "type_asc") return a.category_type_display.localeCompare(b.category_type_display);
      if (categorySort === "status_asc") return Number(b.is_active) - Number(a.is_active);
      if (categorySort === "newest") return dateKey(b.created_at) - dateKey(a.created_at);
      return a.name.localeCompare(b.name);
    });

    return rows;
  });

  const categoryTotalPages = $derived(Math.max(1, Math.ceil(filteredCategories.length / categoryPageSize)));
  const categoryStart = $derived(filteredCategories.length === 0 ? 0 : (categoryPage - 1) * categoryPageSize + 1);
  const categoryEnd = $derived(Math.min(filteredCategories.length, categoryPage * categoryPageSize));
  const categoryPageRows = $derived(filteredCategories.slice(categoryStart - 1, categoryEnd));

  $effect(() => {
    if (categoryPage > categoryTotalPages) categoryPage = categoryTotalPages;
    if (categoryPage < 1) categoryPage = 1;
  });

  const filteredRules = $derived.by(() => {
    let rows = mitigationRules.filter((rule) => {
      if (ruleCategoryFilter && String(rule.risk_category) !== ruleCategoryFilter) return false;
      if (ruleSeverityFilter && rule.severity !== ruleSeverityFilter) return false;
      if (ruleStatusFilter === "active" && !rule.is_active) return false;
      if (ruleStatusFilter === "inactive" && rule.is_active) return false;
      if (ruleEscalationFilter === "yes" && !rule.escalation_required) return false;
      if (ruleEscalationFilter === "no" && rule.escalation_required) return false;
      if (!ruleSearch.trim()) return true;
      const needle = ruleSearch.trim().toLowerCase();
      const haystack =
        `${rule.risk_category_name} ${rule.risk_category_type_display} ${rule.severity_display} ${rule.assign_to_role_name || ""}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (ruleSort === "newest") return dateKey(b.created_at) - dateKey(a.created_at);
      if (ruleSort === "severity_desc") return severityRank(b.severity) - severityRank(a.severity);
      if (ruleSort === "response_asc") return (a.response_time_hours ?? Number.MAX_SAFE_INTEGER) - (b.response_time_hours ?? Number.MAX_SAFE_INTEGER);
      if (ruleSort === "response_desc") return (b.response_time_hours ?? -1) - (a.response_time_hours ?? -1);
      return a.risk_category_name.localeCompare(b.risk_category_name);
    });

    return rows;
  });

  const ruleTotalPages = $derived(Math.max(1, Math.ceil(filteredRules.length / rulePageSize)));
  const ruleStart = $derived(filteredRules.length === 0 ? 0 : (rulePage - 1) * rulePageSize + 1);
  const ruleEnd = $derived(Math.min(filteredRules.length, rulePage * rulePageSize));
  const rulePageRows = $derived(filteredRules.slice(ruleStart - 1, ruleEnd));

  $effect(() => {
    if (rulePage > ruleTotalPages) rulePage = ruleTotalPages;
    if (rulePage < 1) rulePage = 1;
  });

  onMount(async () => {
    await Promise.all([loadCategories(), loadRules(), loadMatrix(), loadRoles()]);
  });

  // --- Categories ---
  async function loadCategories() {
    loadingCategories = true;
    try {
      const res = await api.get<PaginatedResponse<RiskCategory>>("/settings/risk-categories/", { page_size: "100" });
      categories = res.results;
    } catch {
      toast.error("Error", "Could not load risk categories");
    } finally {
      loadingCategories = false;
    }
  }

  function resetCategoryForm() {
    categoryForm = { name: "", category_type: "financial", description: "", is_active: true };
    editingCategoryId = null;
    showCategoryForm = false;
  }

  function editCategory(cat: RiskCategory) {
    editingCategoryId = cat.id;
    categoryForm = {
      name: cat.name,
      category_type: cat.category_type,
      description: cat.description,
      is_active: cat.is_active,
    };
    showCategoryForm = true;
  }

  async function saveCategory() {
    if (!categoryForm.name.trim()) {
      toast.error("Validation Error", "Category name is required");
      return;
    }

    try {
      if (editingCategoryId) {
        await api.patch(`/settings/risk-categories/${editingCategoryId}/`, categoryForm);
        toast.success("Updated", "Risk category updated");
      } else {
        await api.post("/settings/risk-categories/", categoryForm);
        toast.success("Created", "Risk category created");
      }
      resetCategoryForm();
      await loadCategories();
    } catch (err: any) {
      toast.error("Error", err.response?.data?.detail || "Could not save category");
    }
  }

  async function deleteCategory(id: number, name: string) {
    if (!confirm(`Delete risk category "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/settings/risk-categories/${id}/`);
      toast.success("Deleted", "Risk category deleted");
      await loadCategories();
    } catch {
      toast.error("Error", "Could not delete category. It may have associated rules.");
    }
  }

  // --- Mitigation Rules ---
  async function loadRules() {
    loadingRules = true;
    try {
      const res = await api.get<PaginatedResponse<RiskMitigationRule>>("/settings/risk-mitigation-rules/", { page_size: "100" });
      mitigationRules = res.results;
    } catch {
      toast.error("Error", "Could not load mitigation rules");
    } finally {
      loadingRules = false;
    }
  }

  async function loadRoles() {
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", { page_size: "100" });
      roles = res.results;
    } catch {
      // Non-critical
    }
  }

  function resetRuleForm() {
    ruleForm = { risk_category: 0, severity: "medium", assign_to_role: null, escalation_required: false, response_time_hours: null, is_active: true };
    editingRuleId = null;
    showRuleForm = false;
  }

  function editRule(rule: RiskMitigationRule) {
    editingRuleId = rule.id;
    ruleForm = {
      risk_category: rule.risk_category,
      severity: rule.severity,
      assign_to_role: rule.assign_to_role,
      escalation_required: rule.escalation_required,
      response_time_hours: rule.response_time_hours,
      is_active: rule.is_active,
    };
    showRuleForm = true;
  }

  async function saveRule() {
    if (!ruleForm.risk_category) {
      toast.error("Validation Error", "Risk category is required");
      return;
    }

    try {
      const payload: any = { ...ruleForm };
      if (!payload.assign_to_role) payload.assign_to_role = null;
      if (!payload.response_time_hours) payload.response_time_hours = null;

      if (editingRuleId) {
        await api.patch(`/settings/risk-mitigation-rules/${editingRuleId}/`, payload);
        toast.success("Updated", "Mitigation rule updated");
      } else {
        await api.post("/settings/risk-mitigation-rules/", payload);
        toast.success("Created", "Mitigation rule created");
      }
      resetRuleForm();
      await loadRules();
    } catch (err: any) {
      toast.error("Error", err.response?.data?.detail || "Could not save rule");
    }
  }

  async function deleteRule(id: number) {
    if (!confirm("Delete this mitigation rule? This cannot be undone.")) return;
    try {
      await api.delete(`/settings/risk-mitigation-rules/${id}/`);
      toast.success("Deleted", "Mitigation rule deleted");
      await loadRules();
    } catch {
      toast.error("Error", "Could not delete mitigation rule");
    }
  }

  // --- Score Matrix ---
  async function loadMatrix() {
    loadingMatrix = true;
    try {
      matrix = await api.get<RiskScoreMatrix>("/settings/risk-score-matrix/");
      syncMatrixForm();
    } catch {
      toast.error("Error", "Could not load risk score matrix");
    } finally {
      loadingMatrix = false;
    }
  }

  function syncMatrixForm() {
    if (!matrix) return;
    matrixForm = {
      likelihood: { ...matrix.matrix_config.likelihood },
      impact: { ...matrix.matrix_config.impact },
      thresholds: { ...matrix.matrix_config.thresholds },
    };
  }

  async function saveMatrix() {
    try {
      matrix = await api.patch<RiskScoreMatrix>("/settings/risk-score-matrix/", {
        matrix_config: matrixForm,
      });
      toast.success("Updated", "Risk score matrix updated");
      editingMatrix = false;
      syncMatrixForm();
    } catch (err: any) {
      toast.error("Error", err.response?.data?.detail || "Could not save matrix");
    }
  }

  const scaleLabels: Record<string, string> = {
    very_low: "Very Low",
    low: "Low",
    medium: "Medium",
    high: "High",
    very_high: "Very High",
  };

  const thresholdLabels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
  };

  function getThresholdColor(key: string): string {
    const colors: Record<string, string> = {
      low: "text-green-700 bg-green-50 border-green-200",
      medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
      high: "text-orange-700 bg-orange-50 border-orange-200",
      critical: "text-red-700 bg-red-50 border-red-200",
    };
    return colors[key] || "";
  }
</script>

<div class="max-w-6xl">
  <div class="mb-8">
    <a
      href="/settings/project-governance"
      class="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-800 mb-4"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to governance
    </a>
    <h1 class="text-2xl font-bold text-neutral-800 mb-2">Risk Framework</h1>
    <p class="text-sm text-neutral-500">
      Manage risk categories, mitigation rules, and scoring configuration.
    </p>
  </div>

  <!-- Tabs -->
  <div class="flex items-center gap-1 mb-6 border-b border-neutral-200">
    {#each [
      { key: "categories" as Tab, label: "Risk Categories", count: categories.length },
      { key: "mitigation" as Tab, label: "Mitigation Rules", count: mitigationRules.length },
      { key: "matrix" as Tab, label: "Score Matrix", count: null },
    ] as tab}
      <button
        onclick={() => (activeTab = tab.key)}
        class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px {activeTab === tab.key
          ? 'border-neutral-800 text-neutral-800'
          : 'border-transparent text-neutral-500 hover:text-neutral-700'}"
      >
        {tab.label}
        {#if tab.count !== null}
          <span class="ml-1.5 text-xs text-neutral-400">({tab.count})</span>
        {/if}
      </button>
    {/each}
  </div>

  <!-- Risk Categories Tab -->
  {#if activeTab === "categories"}
    <div class="space-y-4">
      <div class="flex items-center justify-end">
        <button
          onclick={() => { resetCategoryForm(); showCategoryForm = true; }}
          class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
        >
          + New Category
        </button>
      </div>

      {#if showCategoryForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-base font-semibold text-neutral-800 mb-4">
            {editingCategoryId ? "Edit Category" : "New Risk Category"}
          </h3>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="cat-name" class="block text-sm font-medium text-neutral-700 mb-1.5">
                  Name <span class="text-red-500">*</span>
                </label>
                <input
                  id="cat-name"
                  type="text"
                  bind:value={categoryForm.name}
                  placeholder="e.g., Market Volatility"
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                />
              </div>
              <div>
                <label for="cat-type" class="block text-sm font-medium text-neutral-700 mb-1.5">
                  Category Type <span class="text-red-500">*</span>
                </label>
                <select
                  id="cat-type"
                  bind:value={categoryForm.category_type}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  {#each categoryTypeOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            </div>
            <div>
              <label for="cat-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
              <textarea
                id="cat-desc"
                bind:value={categoryForm.description}
                rows="2"
                placeholder="Describe this risk category..."
                class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
              ></textarea>
            </div>
            <div>
              <label class="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  bind:checked={categoryForm.is_active}
                  class="w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
                />
                <span class="text-sm font-medium text-neutral-800">Active</span>
              </label>
            </div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                onclick={resetCategoryForm}
                class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onclick={saveCategory}
                class="px-5 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
              >
                {editingCategoryId ? "Save Changes" : "Create Category"}
              </button>
            </div>
          </div>
        </div>
      {/if}

      {#if loadingCategories}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        </div>
      {:else if categories.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <svg class="w-12 h-12 text-neutral-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
          <p class="text-sm text-neutral-500">No risk categories defined.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div class="border-b border-neutral-200 bg-neutral-50/50 px-4 py-4">
            <div class="grid grid-cols-1 gap-3 lg:grid-cols-5">
              <input
                type="text"
                bind:value={categorySearch}
                oninput={() => (categoryPage = 1)}
                placeholder="Search name, type, description..."
                class="lg:col-span-2 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              />
              <select
                bind:value={categoryTypeFilter}
                onchange={() => (categoryPage = 1)}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Types</option>
                {#each categoryTypeOptions as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
              <select
                bind:value={categoryStatusFilter}
                onchange={() => (categoryPage = 1)}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
              <div class="grid grid-cols-2 gap-2">
                <select
                  bind:value={categorySort}
                  onchange={() => (categoryPage = 1)}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  <option value="name_asc">Name A-Z</option>
                  <option value="name_desc">Name Z-A</option>
                  <option value="type_asc">Type</option>
                  <option value="status_asc">Status</option>
                  <option value="newest">Newest</option>
                </select>
                <select
                  bind:value={categoryPageSize}
                  onchange={() => (categoryPage = 1)}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  {#each PAGE_SIZE_OPTIONS as size}
                    <option value={size}>{size} / page</option>
                  {/each}
                </select>
              </div>
            </div>
          </div>

          {#if filteredCategories.length === 0}
            <div class="p-12 text-center">
              <p class="text-sm text-neutral-500">No categories match current filters.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="w-full min-w-[900px]">
                <thead>
                  <tr class="border-b border-neutral-200 bg-neutral-50">
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Name</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Type</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Description</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Status</th>
                    <th class="text-right px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-200">
                  {#each categoryPageRows as cat}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-6 py-4">
                        <span class="text-sm font-medium text-neutral-800">{cat.name}</span>
                      </td>
                      <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getCategoryTypeColor(cat.category_type)}">
                          {cat.category_type_display}
                        </span>
                      </td>
                      <td class="px-6 py-4">
                        <span class="text-sm text-neutral-600 line-clamp-1">{cat.description || "—"}</span>
                      </td>
                      <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {cat.is_active ? 'bg-green-100 text-green-800' : 'bg-neutral-100 text-neutral-600'}">
                          {cat.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-3">
                          <button
                            onclick={() => editCategory(cat)}
                            class="text-sm font-medium text-neutral-700 hover:text-neutral-800 transition-colors"
                          >
                            Edit
                          </button>
                          <button
                            onclick={() => deleteCategory(cat.id, cat.name)}
                            class="text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
              <p class="text-xs text-neutral-500">Showing {categoryStart}-{categoryEnd} of {filteredCategories.length}</p>
              <div class="flex items-center gap-2">
                <button
                  onclick={() => (categoryPage = Math.max(1, categoryPage - 1))}
                  disabled={categoryPage === 1}
                  class="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
                >
                  Previous
                </button>
                <span class="text-xs text-neutral-600">Page {categoryPage} of {categoryTotalPages}</span>
                <button
                  onclick={() => (categoryPage = Math.min(categoryTotalPages, categoryPage + 1))}
                  disabled={categoryPage === categoryTotalPages}
                  class="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Mitigation Rules Tab -->
  {#if activeTab === "mitigation"}
    <div class="space-y-4">
      <div class="flex items-center justify-end">
        <button
          onclick={() => { resetRuleForm(); showRuleForm = true; }}
          class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
        >
          + New Rule
        </button>
      </div>

      {#if showRuleForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-base font-semibold text-neutral-800 mb-4">
            {editingRuleId ? "Edit Mitigation Rule" : "New Mitigation Rule"}
          </h3>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="rule-cat" class="block text-sm font-medium text-neutral-700 mb-1.5">
                  Risk Category <span class="text-red-500">*</span>
                </label>
                <select
                  id="rule-cat"
                  bind:value={ruleForm.risk_category}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  <option value={0}>Select category...</option>
                  {#each categories.filter(c => c.is_active) as cat}
                    <option value={cat.id}>{cat.name} ({cat.category_type_display})</option>
                  {/each}
                </select>
              </div>
              <div>
                <label for="rule-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">
                  Severity <span class="text-red-500">*</span>
                </label>
                <select
                  id="rule-severity"
                  bind:value={ruleForm.severity}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  {#each severityOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="rule-role" class="block text-sm font-medium text-neutral-700 mb-1.5">Assign to Role</label>
                <select
                  id="rule-role"
                  bind:value={ruleForm.assign_to_role}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  <option value={null}>None</option>
                  {#each roles as role}
                    <option value={role.id}>{role.name}</option>
                  {/each}
                </select>
              </div>
              <div>
                <label for="rule-response" class="block text-sm font-medium text-neutral-700 mb-1.5">Response Time (hours)</label>
                <input
                  id="rule-response"
                  type="number"
                  min="1"
                  bind:value={ruleForm.response_time_hours}
                  placeholder="e.g., 24"
                  class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                />
              </div>
            </div>
            <div class="flex items-center gap-6">
              <label class="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  bind:checked={ruleForm.escalation_required}
                  class="w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
                />
                <span class="text-sm font-medium text-neutral-800">Escalation required</span>
              </label>
              <label class="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  bind:checked={ruleForm.is_active}
                  class="w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
                />
                <span class="text-sm font-medium text-neutral-800">Active</span>
              </label>
            </div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                onclick={resetRuleForm}
                class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onclick={saveRule}
                class="px-5 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
              >
                {editingRuleId ? "Save Changes" : "Create Rule"}
              </button>
            </div>
          </div>
        </div>
      {/if}

      {#if loadingRules}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        </div>
      {:else if mitigationRules.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <svg class="w-12 h-12 text-neutral-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
          </svg>
          <p class="text-sm text-neutral-500">No mitigation rules defined.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div class="border-b border-neutral-200 bg-neutral-50/50 px-4 py-4">
            <div class="grid grid-cols-1 gap-3 lg:grid-cols-6">
              <input
                type="text"
                bind:value={ruleSearch}
                oninput={() => (rulePage = 1)}
                placeholder="Search category, role, severity..."
                class="lg:col-span-2 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              />
              <select
                bind:value={ruleCategoryFilter}
                onchange={() => (rulePage = 1)}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Categories</option>
                {#each categories as cat}
                  <option value={String(cat.id)}>{cat.name}</option>
                {/each}
              </select>
              <select
                bind:value={ruleSeverityFilter}
                onchange={() => (rulePage = 1)}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Severities</option>
                {#each severityOptions as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
              <select
                bind:value={ruleStatusFilter}
                onchange={() => (rulePage = 1)}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
              <div class="grid grid-cols-3 gap-2">
                <select
                  bind:value={ruleEscalationFilter}
                  onchange={() => (rulePage = 1)}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  <option value="">Escalation</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
                <select
                  bind:value={ruleSort}
                  onchange={() => (rulePage = 1)}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  <option value="category_asc">Category</option>
                  <option value="severity_desc">Severity</option>
                  <option value="response_asc">Response Low</option>
                  <option value="response_desc">Response High</option>
                  <option value="newest">Newest</option>
                </select>
                <select
                  bind:value={rulePageSize}
                  onchange={() => (rulePage = 1)}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                >
                  {#each PAGE_SIZE_OPTIONS as size}
                    <option value={size}>{size} / page</option>
                  {/each}
                </select>
              </div>
            </div>
          </div>

          {#if filteredRules.length === 0}
            <div class="p-12 text-center">
              <p class="text-sm text-neutral-500">No mitigation rules match current filters.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="w-full min-w-[1100px]">
                <thead>
                  <tr class="border-b border-neutral-200 bg-neutral-50">
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Risk Category</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Severity</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Assigned Role</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Response</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Escalation</th>
                    <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Status</th>
                    <th class="text-right px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-200">
                  {#each rulePageRows as rule}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-6 py-4">
                        <div>
                          <span class="text-sm font-medium text-neutral-800">{rule.risk_category_name}</span>
                          <p class="text-xs text-neutral-500">{rule.risk_category_type_display}</p>
                        </div>
                      </td>
                      <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getSeverityColor(rule.severity)}">
                          {rule.severity_display}
                        </span>
                      </td>
                      <td class="px-6 py-4">
                        <span class="text-sm text-neutral-700">{rule.assign_to_role_name || "—"}</span>
                      </td>
                      <td class="px-6 py-4">
                        <span class="text-sm text-neutral-700">{rule.response_time_hours ? `${rule.response_time_hours}h` : "—"}</span>
                      </td>
                      <td class="px-6 py-4">
                        {#if rule.escalation_required}
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">Yes</span>
                        {:else}
                          <span class="text-xs text-neutral-400">No</span>
                        {/if}
                      </td>
                      <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {rule.is_active ? 'bg-green-100 text-green-800' : 'bg-neutral-100 text-neutral-600'}">
                          {rule.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-3">
                          <button
                            onclick={() => editRule(rule)}
                            class="text-sm font-medium text-neutral-700 hover:text-neutral-800 transition-colors"
                          >
                            Edit
                          </button>
                          <button
                            onclick={() => deleteRule(rule.id)}
                            class="text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
              <p class="text-xs text-neutral-500">Showing {ruleStart}-{ruleEnd} of {filteredRules.length}</p>
              <div class="flex items-center gap-2">
                <button
                  onclick={() => (rulePage = Math.max(1, rulePage - 1))}
                  disabled={rulePage === 1}
                  class="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
                >
                  Previous
                </button>
                <span class="text-xs text-neutral-600">Page {rulePage} of {ruleTotalPages}</span>
                <button
                  onclick={() => (rulePage = Math.min(ruleTotalPages, rulePage + 1))}
                  disabled={rulePage === ruleTotalPages}
                  class="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Score Matrix Tab -->
  {#if activeTab === "matrix"}
    {#if loadingMatrix}
      <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if matrix}
      <div class="space-y-6">
        <div class="flex items-center justify-end">
          {#if !editingMatrix}
            <button
              onclick={() => { syncMatrixForm(); editingMatrix = true; }}
              class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Edit Matrix
            </button>
          {/if}
        </div>

        <!-- Likelihood Scale -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-base font-semibold text-neutral-800 mb-4">Likelihood Scale</h3>
          <p class="text-sm text-neutral-500 mb-4">Define numerical values for likelihood levels (higher = more likely).</p>
          <div class="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {#each Object.entries(editingMatrix ? matrixForm.likelihood : matrix.matrix_config.likelihood) as [key, value]}
              <div class="text-center">
                <p class="text-xs font-medium text-neutral-500 mb-1.5 uppercase">{scaleLabels[key] || key}</p>
                {#if editingMatrix}
                  <input
                    type="number"
                    min="1"
                    max="10"
                    bind:value={matrixForm.likelihood[key]}
                    class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-center text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                  />
                {:else}
                  <div class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-neutral-100 text-sm font-bold text-neutral-800">
                    {value}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        <!-- Impact Scale -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-base font-semibold text-neutral-800 mb-4">Impact Scale</h3>
          <p class="text-sm text-neutral-500 mb-4">Define numerical values for impact levels (higher = more severe).</p>
          <div class="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {#each Object.entries(editingMatrix ? matrixForm.impact : matrix.matrix_config.impact) as [key, value]}
              <div class="text-center">
                <p class="text-xs font-medium text-neutral-500 mb-1.5 uppercase">{scaleLabels[key] || key}</p>
                {#if editingMatrix}
                  <input
                    type="number"
                    min="1"
                    max="10"
                    bind:value={matrixForm.impact[key]}
                    class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-center text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                  />
                {:else}
                  <div class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-neutral-100 text-sm font-bold text-neutral-800">
                    {value}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        <!-- Thresholds -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-base font-semibold text-neutral-800 mb-4">Risk Score Thresholds</h3>
          <p class="text-sm text-neutral-500 mb-4">
            Risk score = Likelihood x Impact. Define score thresholds for each risk level.
          </p>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {#each Object.entries(editingMatrix ? matrixForm.thresholds : matrix.matrix_config.thresholds) as [key, value]}
              <div class="border rounded-lg p-4 {getThresholdColor(key)}">
                <p class="text-xs font-semibold uppercase mb-2">{thresholdLabels[key] || key}</p>
                {#if editingMatrix}
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-neutral-500">&le;</span>
                    <input
                      type="number"
                      min="1"
                      bind:value={matrixForm.thresholds[key]}
                      class="w-full rounded border border-neutral-300 bg-white px-2 py-1.5 text-sm text-center text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                    />
                  </div>
                {:else}
                  <p class="text-2xl font-bold">&le; {value}</p>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        {#if editingMatrix}
          <div class="flex items-center justify-end gap-3">
            <button
              onclick={() => { editingMatrix = false; syncMatrixForm(); }}
              class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onclick={saveMatrix}
              class="px-5 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
            >
              Save Matrix
            </button>
          </div>
        {/if}

        {#if matrix.updated_at}
          <p class="text-xs text-neutral-400 text-right">
            Last updated: {new Date(matrix.updated_at).toLocaleString()}
          </p>
        {/if}
      </div>
    {/if}
  {/if}
</div>
