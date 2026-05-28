<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, ReportSavedView, ReportTemplateListItem } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type ChartType = "bar" | "line" | "donut";
  type PivotType = "employees" | "department" | "location" | "employment_type";

  type EmployeeColumnVisibility = {
    employee_code: boolean;
    employee_name: boolean;
    department: boolean;
    location: boolean;
    employment_type: boolean;
    status: boolean;
    job_title: boolean;
  };

  const departmentOptions = ["All Departments", "HR", "Finance", "Operations", "Projects"];
  const locationOptions = ["All Locations", "HQ", "Lagos", "Abuja", "Remote"];
  const employmentTypeOptions = ["All Types", "full_time", "part_time", "contract", "intern"];

  const defaultColumns: EmployeeColumnVisibility = {
    employee_code: true,
    employee_name: true,
    department: true,
    location: true,
    employment_type: true,
    status: true,
    job_title: true,
  };

  const columnLabels: Record<keyof EmployeeColumnVisibility, string> = {
    employee_code: "Employee ID",
    employee_name: "Employee",
    department: "Department",
    location: "Location",
    employment_type: "Employment Type",
    status: "Status",
    job_title: "Role",
  };

  const exampleViewNames = [
    "Finance Monthly Summary",
    "HR Attrition Dashboard",
    "Project Cost Tracker",
  ];

  let loading = $state(true);
  let saving = $state(false);
  let mutatingId = $state<number | null>(null);

  let views = $state<ReportSavedView[]>([]);
  let templates = $state<ReportTemplateListItem[]>([]);

  let form = $state({
    name: "",
    report_template: "",
    date_from: "",
    date_to: "",
    department: "All Departments",
    location: "All Locations",
    employment_type: "All Types",
    chart_type: "bar" as ChartType,
    pivot_mode: "employees" as PivotType,
    columns: { ...defaultColumns },
  });

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  function formatEmploymentType(value: string): string {
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function formatDateTime(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function readObject(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
  }

  function resetForm() {
    form = {
      name: "",
      report_template: form.report_template,
      date_from: "",
      date_to: "",
      department: "All Departments",
      location: "All Locations",
      employment_type: "All Types",
      chart_type: "bar",
      pivot_mode: "employees",
      columns: { ...defaultColumns },
    };
  }

  function parseViewSettings(view: ReportSavedView): { chartType: ChartType; pivotMode: PivotType } {
    const filters = readObject(view.filters);
    const settings = readObject(filters?.view_settings);

    const chartType = settings?.chart_type;
    const pivotMode = settings?.pivot_mode;

    return {
      chartType: chartType === "bar" || chartType === "line" || chartType === "donut" ? chartType : "bar",
      pivotMode:
        pivotMode === "employees" ||
        pivotMode === "department" ||
        pivotMode === "location" ||
        pivotMode === "employment_type"
          ? pivotMode
          : "employees",
    };
  }

  function parseVisibleColumns(view: ReportSavedView): string[] {
    const visibility = readObject(view.column_visibility);
    const employeeColumns = readObject(visibility?.employee_columns);
    if (!employeeColumns) return Object.values(columnLabels);

    const visible: string[] = [];
    for (const key of Object.keys(defaultColumns) as (keyof EmployeeColumnVisibility)[]) {
      const enabled = employeeColumns[key];
      if (typeof enabled !== "boolean" || enabled) {
        visible.push(columnLabels[key]);
      }
    }
    return visible;
  }

  function describeFilters(view: ReportSavedView): string {
    const filters = readObject(view.filters);
    if (!filters) return "No filters saved";

    const parts: string[] = [];
    if (typeof filters.date_from === "string") parts.push(`From ${filters.date_from}`);
    if (typeof filters.date_to === "string") parts.push(`To ${filters.date_to}`);
    if (typeof filters.department === "string") parts.push(`Dept: ${filters.department}`);
    if (typeof filters.location === "string") parts.push(`Location: ${filters.location}`);
    if (typeof filters.employment_type === "string") {
      parts.push(`Employment: ${formatEmploymentType(filters.employment_type)}`);
    }

    return parts.length ? parts.join(" | ") : "No filters saved";
  }

  async function loadSavedViewsPage() {
    loading = true;
    try {
      const [viewsPayload, templatesPayload] = await Promise.all([
        api.get<PaginatedResponse<ReportSavedView> | ReportSavedView[]>("/settings/report-saved-views/", {
          ordering: "name",
        }),
        api.get<PaginatedResponse<ReportTemplateListItem> | ReportTemplateListItem[]>("/settings/report-templates/", {
          ordering: "name",
          is_active: "true",
        }),
      ]);

      views = unwrapList(viewsPayload);
      templates = unwrapList(templatesPayload);

      if (!form.report_template && templates.length > 0) {
        form = {
          ...form,
          report_template: String(templates[0].id),
        };
      }
    } catch {
      views = [];
      templates = [];
      toast.error("Load failed", "Could not load saved views.");
    } finally {
      loading = false;
    }
  }

  async function createSavedView() {
    const name = form.name.trim();
    if (!name) {
      toast.error("Missing name", "Enter a view name.");
      return;
    }
    if (!form.report_template) {
      toast.error("Missing report", "Select a report template.");
      return;
    }

    const payloadFilters: Record<string, unknown> = {
      view_settings: {
        chart_type: form.chart_type,
        pivot_mode: form.pivot_mode,
      },
    };

    if (form.date_from) payloadFilters.date_from = form.date_from;
    if (form.date_to) payloadFilters.date_to = form.date_to;
    if (form.department !== "All Departments") payloadFilters.department = form.department;
    if (form.location !== "All Locations") payloadFilters.location = form.location;
    if (form.employment_type !== "All Types") payloadFilters.employment_type = form.employment_type;

    const payload = {
      name,
      report_template: Number(form.report_template),
      filters: payloadFilters,
      column_visibility: {
        employee_columns: form.columns,
      },
      rows_per_page: 25,
      is_default: views.length === 0,
      is_active: true,
    };

    saving = true;
    try {
      const created = await api.post<ReportSavedView>("/settings/report-saved-views/", payload);
      views = [...views, created].sort((a, b) => a.name.localeCompare(b.name));
      resetForm();
      toast.success("Saved", `${created.name} is now in My Views.`);
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.name?.length) {
        toast.error("Save failed", error.fieldErrors.name[0]);
      } else {
        toast.error("Save failed", "Could not create saved view.");
      }
    } finally {
      saving = false;
    }
  }

  async function deleteView(view: ReportSavedView) {
    mutatingId = view.id;
    try {
      await api.delete(`/settings/report-saved-views/${view.id}/`);
      views = views.filter((item) => item.id !== view.id);
      toast.success("Deleted", `${view.name} removed.`);
    } catch {
      toast.error("Delete failed", "Could not remove view.");
    } finally {
      mutatingId = null;
    }
  }

  async function setDefaultView(view: ReportSavedView) {
    mutatingId = view.id;
    try {
      const updated = await api.patch<ReportSavedView>(`/settings/report-saved-views/${view.id}/`, {
        is_default: true,
      });
      views = views.map((item) =>
        item.id === updated.id
          ? updated
          : {
              ...item,
              is_default: false,
            },
      );
      toast.success("Default updated", `${updated.name} is now your default view.`);
    } catch {
      toast.error("Update failed", "Could not set default view.");
    } finally {
      mutatingId = null;
    }
  }

  async function toggleActive(view: ReportSavedView) {
    mutatingId = view.id;
    try {
      const updated = await api.patch<ReportSavedView>(`/settings/report-saved-views/${view.id}/`, {
        is_active: !view.is_active,
      });
      views = views.map((item) => (item.id === updated.id ? updated : item));
      toast.success("Saved", `${updated.name} ${updated.is_active ? "activated" : "archived"}.`);
    } catch {
      toast.error("Update failed", "Could not update view status.");
    } finally {
      mutatingId = null;
    }
  }

  $effect(() => {
    void loadSavedViewsPage();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Saved Views</h1>
    <p class="mt-2 text-sm text-neutral-600">Save and reuse report configurations with filters, columns, and chart type.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Create View</h2>
      <span class="text-xs text-neutral-500">My Views</span>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <label class="text-xs font-medium text-neutral-600">
        View Name
        <input
          type="text"
          bind:value={form.name}
          placeholder="Finance Monthly Summary"
          class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800"
        />
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Report Template
        <select bind:value={form.report_template} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#each templates as template}
            <option value={String(template.id)}>{template.name}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Chart Type
        <select bind:value={form.chart_type} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          <option value="bar">Bar</option>
          <option value="line">Line</option>
          <option value="donut">Donut</option>
        </select>
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Pivot Mode
        <select bind:value={form.pivot_mode} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          <option value="employees">Employees</option>
          <option value="department">Department</option>
          <option value="location">Location</option>
          <option value="employment_type">Employment Type</option>
        </select>
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Date From
        <DateInput bind:value={form.date_from} />
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Date To
        <DateInput bind:value={form.date_to} />
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Department
        <select bind:value={form.department} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#each departmentOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs font-medium text-neutral-600">
        Location
        <select bind:value={form.location} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#each locationOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>
    </div>

    <div>
      <p class="text-xs font-medium text-neutral-600">Columns</p>
      <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {#each Object.keys(defaultColumns) as key}
          <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-700">
            <input
              type="checkbox"
              checked={form.columns[key as keyof EmployeeColumnVisibility]}
              onchange={(event) => {
                const target = event.currentTarget as HTMLInputElement;
                form = {
                  ...form,
                  columns: {
                    ...form.columns,
                    [key]: target.checked,
                  },
                };
              }}
              class="rounded border-neutral-300"
            />
            <span>{columnLabels[key as keyof EmployeeColumnVisibility]}</span>
          </label>
        {/each}
      </div>
    </div>

    <div class="flex justify-end">
      <button
        type="button"
        onclick={createSavedView}
        disabled={saving || templates.length === 0}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save View"}
      </button>
    </div>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">My Views</h2>

    {#if loading}
      <p class="mt-4 text-sm text-neutral-500">Loading views...</p>
    {:else if views.length === 0}
      <div class="mt-4 space-y-3">
        <p class="text-sm text-neutral-500">No saved views yet. Suggested starter names:</p>
        <div class="flex flex-wrap gap-2">
          {#each exampleViewNames as name}
            <span class="rounded-full border border-neutral-300 px-3 py-1 text-xs text-neutral-700">{name}</span>
          {/each}
        </div>
      </div>
    {:else}
      <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {#each views as view (view.id)}
          {@const settings = parseViewSettings(view)}
          {@const columns = parseVisibleColumns(view)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold text-neutral-900">{view.name}</h3>
                <p class="mt-1 text-sm text-neutral-600">{view.report_template_name}</p>
              </div>
              <div class="flex flex-wrap items-center gap-1">
                {#if view.is_default}
                  <span class="rounded-full bg-neutral-900 px-2 py-0.5 text-[11px] font-semibold text-white">Default</span>
                {/if}
                {#if !view.is_active}
                  <span class="rounded-full bg-neutral-200 px-2 py-0.5 text-[11px] font-semibold text-neutral-700">Archived</span>
                {/if}
              </div>
            </div>

            <div class="mt-3 space-y-2 text-xs text-neutral-600">
              <p><span class="font-semibold text-neutral-800">Filters:</span> {describeFilters(view)}</p>
              <p><span class="font-semibold text-neutral-800">Columns:</span> {columns.join(", ")}</p>
              <p><span class="font-semibold text-neutral-800">Chart Type:</span> {settings.chartType.toUpperCase()} | <span class="font-semibold text-neutral-800">Pivot:</span> {settings.pivotMode}</p>
              <p><span class="font-semibold text-neutral-800">Updated:</span> {formatDateTime(view.updated_at)}</p>
            </div>

            <div class="mt-4 flex flex-wrap items-center gap-2">
              <a
                href={`/reports/${view.report_template}?savedView=${view.id}`}
                class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
              >
                Open View
              </a>
              <button
                type="button"
                onclick={() => setDefaultView(view)}
                disabled={view.is_default || mutatingId === view.id}
                class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 disabled:opacity-60"
              >
                Set Default
              </button>
              <button
                type="button"
                onclick={() => toggleActive(view)}
                disabled={mutatingId === view.id}
                class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 disabled:opacity-60"
              >
                {view.is_active ? "Archive" : "Activate"}
              </button>
              <button
                type="button"
                onclick={() => deleteView(view)}
                disabled={mutatingId === view.id}
                class="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
              >
                Delete
              </button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>
