<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CompanyProfile,
    DocumentAutomationSettings,
    DocumentGenerationKind,
    DocumentGenerationRecord,
    DocumentGenerationResult,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  type SelectItem = { id: number; label: string };

  let loading = $state(true);
  let saving = $state(false);
  let loadingHistory = $state(false);

  let company = $state<CompanyProfile | null>(null);
  let automationSettings = $state<DocumentAutomationSettings | null>(null);

  let projects = $state<SelectItem[]>([]);
  let lands = $state<SelectItem[]>([]);
  let units = $state<SelectItem[]>([]);
  let clients = $state<SelectItem[]>([]);
  let vendors = $state<SelectItem[]>([]);

  let history = $state<DocumentGenerationRecord[]>([]);
  let historyPage = $state(1);
  let historyPageSize = $state(10);
  let historyTotal = $state(0);
  let historyKindFilter = $state("");
  let historySearch = $state("");

  let form = $state({
    generation_kind: "contract" as DocumentGenerationKind,
    title: "",
    summary: "",
    body: "",
    template_code: "",
    variables_json: "{}",
    project_code: "",
    contract_value: "0.00",
    project: "",
    land: "",
    unit: "",
    client: "",
    vendor: "",
  });

  let lastGenerated = $state<DocumentGenerationResult | null>(null);

  const historyTotalPages = $derived(Math.max(1, Math.ceil(historyTotal / historyPageSize)));

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  function toSelectItems<T>(
    rows: T[],
    idGetter: (row: T) => number,
    labelBuilder: (row: T) => string,
  ): SelectItem[] {
    return rows
      .map((row) => ({ id: Number(idGetter(row)), label: labelBuilder(row) }))
      .filter((row) => Number.isFinite(row.id))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  function parseNullableId(value: string): number | null {
    if (!value) return null;
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }

  async function fetchAllPages<T>(endpoint: string, params: Record<string, string> = {}): Promise<T[]> {
    const all: T[] = [];
    let page = 1;
    while (page <= 40) {
      const response = await api.get<PaginatedResponse<T>>(endpoint, {
        ...params,
        page: String(page),
      });
      all.push(...response.results);
      if (!response.next) break;
      page += 1;
    }
    return all;
  }

  async function loadLookups() {
    const [
      settingsResponse,
      projectsResponse,
      landsResponse,
      unitsResponse,
      clientsResponse,
      vendorsResponse,
      companyProfile,
    ] = await Promise.all([
      api.get<DocumentAutomationSettings>("/settings/document-automation/"),
      fetchAllPages<ProjectListItem>("/projects/", { page_size: "200", ordering: "name" }),
      fetchAllPages<{ id: number; name: string }>("/properties/", { page_size: "200", ordering: "name" }),
      fetchAllPages<{ id: number; unit_number: string; property_name?: string }>("/properties/units/", {
        page_size: "200",
      }),
      fetchAllPages<{ id: number; name: string }>("/finance/customers/", { page_size: "200", ordering: "name" }),
      fetchAllPages<{ id: number; name: string }>("/procurement/vendors/", { page_size: "200", ordering: "name" }),
      api.get<CompanyProfile>("/settings/company-profile/"),
    ]);

    automationSettings = settingsResponse;
    projects = toSelectItems(projectsResponse, (row) => row.id, (row) => String(row.name ?? `Project ${row.id}`));
    lands = toSelectItems(landsResponse, (row) => row.id, (row) => String(row.name ?? `Property ${row.id}`));
    units = toSelectItems(unitsResponse, (row) => row.id, (row) => {
      const unitNumber = String(row.unit_number ?? `Unit ${row.id}`);
      const propertyName = String(row.property_name ?? "").trim();
      return propertyName ? `${unitNumber} (${propertyName})` : unitNumber;
    });
    clients = toSelectItems(clientsResponse, (row) => row.id, (row) => String(row.name ?? `Client ${row.id}`));
    vendors = toSelectItems(vendorsResponse, (row) => row.id, (row) => String(row.name ?? `Vendor ${row.id}`));
    company = companyProfile;

    if (!form.template_code && settingsResponse.default_generation_template_code) {
      form.template_code = settingsResponse.default_generation_template_code;
    }
  }

  async function loadHistory() {
    loadingHistory = true;
    try {
      const params: Record<string, string> = {
        page: String(historyPage),
        page_size: String(historyPageSize),
        ordering: "-created_at",
      };
      if (historyKindFilter) params.generation_kind = historyKindFilter;
      if (historySearch.trim()) params.search = historySearch.trim();
      const response = await api.get<PaginatedResponse<DocumentGenerationRecord>>("/documents/control/generation/", params);
      history = response.results;
      historyTotal = response.count;
    } catch (error) {
      history = [];
      historyTotal = 0;
      toast.error("Load failed", parseApiError(error, "Could not load generation history."));
    }
    loadingHistory = false;
  }

  function formatDate(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function goHistoryPage(nextPage: number) {
    if (nextPage < 1 || nextPage > historyTotalPages) return;
    historyPage = nextPage;
    void loadHistory();
  }

  async function handleGenerate() {
    if (!form.title.trim()) {
      toast.error("Validation error", "Title is required.");
      return;
    }

    let variables: Record<string, unknown>;
    try {
      const parsed = JSON.parse(form.variables_json || "{}");
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        variables = parsed as Record<string, unknown>;
      } else {
        toast.error("Validation error", "Variables JSON must be a JSON object.");
        return;
      }
    } catch {
      toast.error("Validation error", "Variables JSON is invalid.");
      return;
    }

    saving = true;
    try {
      const payload = {
        generation_kind: form.generation_kind,
        title: form.title.trim(),
        summary: form.summary,
        body: form.body,
        template_code: form.template_code,
        variables,
        project_code: form.project_code,
        contract_value: form.contract_value || "0.00",
        project: parseNullableId(form.project),
        land: parseNullableId(form.land),
        unit: parseNullableId(form.unit),
        client: parseNullableId(form.client),
        vendor: parseNullableId(form.vendor),
      };
      const result = await api.post<DocumentGenerationResult>("/documents/control/generation/generate/", payload);
      lastGenerated = result;
      toast.success("Generated", `${result.document.document_number} was generated and added to repository.`);
      await loadHistory();
    } catch (error) {
      toast.error("Generation failed", parseApiError(error, "Could not generate branded document."));
    }
    saving = false;
  }

  onMount(async () => {
    loading = true;
    try {
      await loadLookups();
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load generator setup data."));
    }
    await loadHistory();
    loading = false;
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Document Generator</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Generate contracts, invoices, and reports. Policy defaults come from Settings, so users only run operational actions here.
    </p>
  </div>

  {#if loading}
    <div class="py-16 text-center">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Branding & Policy Source</h2>
          <p class="mt-1 text-xs text-neutral-500">Branding uses organization profile. Generation defaults are managed in Settings.</p>
        </div>
        <a
          href="/settings/document-automation"
          class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
        >
          Open Document Automation Settings
        </a>
      </div>

      <div class="mt-4 grid gap-3 md:grid-cols-3">
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <div class="text-xs uppercase tracking-wider text-neutral-500">Organization</div>
          <div class="mt-1 text-sm font-semibold text-neutral-900">{company?.trading_name || company?.name || "--"}</div>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <div class="text-xs uppercase tracking-wider text-neutral-500">Default Owner Role</div>
          <div class="mt-1 text-sm font-semibold text-neutral-900">{automationSettings?.default_generation_owner_role_name || "Not set"}</div>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <div class="text-xs uppercase tracking-wider text-neutral-500">Default Retention Policy</div>
          <div class="mt-1 text-sm font-semibold text-neutral-900">{automationSettings?.default_generation_retention_policy_name || "Not set"}</div>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Generate Document</h2>
      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Type</label>
          <select bind:value={form.generation_kind} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="contract">Contract</option>
            <option value="invoice">Invoice</option>
            <option value="report">Report</option>
          </select>
        </div>
        <div class="xl:col-span-3">
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Title</label>
          <input bind:value={form.title} type="text" placeholder="Document title" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
        <div class="xl:col-span-2">
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Summary</label>
          <input bind:value={form.summary} type="text" placeholder="Short summary" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Template Code</label>
          <input bind:value={form.template_code} type="text" placeholder="Default applied if empty" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Project Code Segment</label>
          <input bind:value={form.project_code} type="text" placeholder="e.g. LUA" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
        <div class="md:col-span-2 xl:col-span-4">
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Body</label>
          <textarea bind:value={form.body} rows="5" placeholder="Main document body..." class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
        <div class="md:col-span-2 xl:col-span-4">
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Variables JSON</label>
          <textarea bind:value={form.variables_json} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 font-mono text-xs" />
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Project</label>
          <select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">None</option>
            {#each projects as option}
              <option value={String(option.id)}>{option.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Land / Property</label>
          <select bind:value={form.land} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">None</option>
            {#each lands as option}
              <option value={String(option.id)}>{option.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Unit</label>
          <select bind:value={form.unit} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">None</option>
            {#each units as option}
              <option value={String(option.id)}>{option.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Vendor</label>
          <select bind:value={form.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">None</option>
            {#each vendors as option}
              <option value={String(option.id)}>{option.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Client</label>
          <select bind:value={form.client} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">None</option>
            {#each clients as option}
              <option value={String(option.id)}>{option.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Contract Value</label>
          <input bind:value={form.contract_value} type="text" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </div>
      </div>

      <div class="mt-5 flex items-center gap-2">
        <button
          type="button"
          onclick={handleGenerate}
          disabled={saving}
          class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Generating..." : "Generate Document"}
        </button>
      </div>
    </div>

    {#if lastGenerated}
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-emerald-900">Latest Generated Output</h2>
        <div class="mt-2 text-sm text-emerald-900">
          {lastGenerated.document.document_number} — {lastGenerated.document.title}
        </div>
        <a
          href={`/documents/${lastGenerated.document.id}`}
          class="mt-2 inline-block text-sm font-semibold text-emerald-800 underline"
        >
          Open Document
        </a>
      </div>
    {/if}

    <div class="rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Generation History</h2>
      </div>
      <div class="grid gap-3 border-b border-neutral-200 px-5 py-4 md:grid-cols-3">
        <input
          type="text"
          bind:value={historySearch}
          placeholder="Search title, template, document..."
          class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
        />
        <select bind:value={historyKindFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
          <option value="">All kinds</option>
          <option value="contract">Contract</option>
          <option value="invoice">Invoice</option>
          <option value="report">Report</option>
        </select>
        <button
          type="button"
          onclick={() => {
            historyPage = 1;
            void loadHistory();
          }}
          class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700"
        >
          Apply Filters
        </button>
      </div>
      {#if loadingHistory}
        <div class="py-14 text-center">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if history.length === 0}
        <div class="py-14 text-center text-sm text-neutral-400">No generated documents yet.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[900px] w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Kind</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Template</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Document</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Created</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each history as row}
                <tr>
                  <td class="px-5 py-3.5 font-medium text-neutral-900">{row.title}</td>
                  <td class="px-5 py-3.5 text-neutral-700">{row.generation_kind}</td>
                  <td class="px-5 py-3.5 text-neutral-600">{row.template_code || "default"}</td>
                  <td class="px-5 py-3.5 text-neutral-700">
                    {#if row.document}
                      <a href={`/documents/${row.document}`} class="underline">{row.document_number || `#${row.document}`}</a>
                    {:else}
                      --
                    {/if}
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600">{formatDate(row.created_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-3 text-xs text-neutral-500">
        <div>
          Showing {(historyTotal === 0 ? 0 : (historyPage - 1) * historyPageSize + 1)}-{Math.min(historyPage * historyPageSize, historyTotal)} of {historyTotal}
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            onclick={() => goHistoryPage(historyPage - 1)}
            disabled={historyPage <= 1}
            class="rounded border border-neutral-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-45"
          >
            Prev
          </button>
          <span>Page {historyPage} / {historyTotalPages}</span>
          <button
            type="button"
            onclick={() => goHistoryPage(historyPage + 1)}
            disabled={historyPage >= historyTotalPages}
            class="rounded border border-neutral-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-45"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>
