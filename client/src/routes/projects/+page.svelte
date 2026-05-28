<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { strToU8, zipSync } from "fflate";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { statusRegistry } from "$lib/stores/statusRegistry.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    PaginatedResponse,
    ProjectListItem,
    ProjectType,
    PropertyListItem,
  } from "$lib/types";

  type SortField =
    | "name"
    | "status"
    | "risk_rating"
    | "start_date"
    | "target_end_date"
    | "created_at";

  type ExportFormat = "csv" | "xlsx" | "pdf";

  let showExportMenu = $state(false);

  let projects = $state<ProjectListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let pageSize = $state(25);
  let loading = $state(true);

  let searchInput = $state("");
  let searchQuery = $state("");
  let statusFilter = $state("");
  let propertyFilter = $state("");
  let typeFilter = $state("");
  let riskFilter = $state("");

  let sortField = $state<SortField>("created_at");
  let sortDirection = $state<"asc" | "desc">("desc");

  let properties = $state<PropertyListItem[]>([]);
  let exporting = $state<"" | ExportFormat>("");

  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let fetchToken = 0;

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  const hasActiveFilters = $derived(
    Boolean(searchQuery || statusFilter || propertyFilter || typeFilter || riskFilter)
  );

  const ordering = $derived(
    sortDirection === "desc" ? `-${sortField}` : sortField
  );

  const visiblePages = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 7;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i += 1) {
      pages.push(i);
    }
    return pages;
  });


  const projectTypeLabels: Record<ProjectType, string> = {
    residential: "Residential",
    mixed_use: "Mixed-Use",
    commercial: "Commercial",
    infrastructure: "Infrastructure",
  };

  const statusCounts = $derived.by(() => {
    const counts = { planning: 0, in_progress: 0, on_hold: 0, completed: 0 };
    for (const project of projects) {
      if (project.status in counts) counts[project.status as keyof typeof counts] += 1;
    }
    return counts;
  });

  const currentPageBudget = $derived.by(() => {
    let total = 0;
    for (const project of projects) {
      if (!project.budget) continue;
      const parsed = Number(project.budget);
      if (Number.isFinite(parsed)) total += parsed;
    }
    return total;
  });

  function buildQueryParams(page = currentPage, size = pageSize): Record<string, string> {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(size),
      ordering,
    };

    if (searchQuery) params.search = searchQuery;
    if (statusFilter) params.status = statusFilter;
    if (propertyFilter) params.property = propertyFilter;
    if (typeFilter) params.project_type = typeFilter;
    if (riskFilter) params.risk_rating = riskFilter;

    return params;
  }

  async function fetchProjects() {
    loading = true;
    const token = ++fetchToken;

    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", buildQueryParams());
      if (token !== fetchToken) return;

      projects = res.results;
      totalCount = res.count;

      if (currentPage > Math.max(1, Math.ceil(res.count / pageSize))) {
        currentPage = 1;
      }
    } catch (err) {
      console.error("[projects/list] fetchProjects failed:", err);
      if (token !== fetchToken) return;
      projects = [];
      totalCount = 0;
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", {
        page_size: "200",
        ordering: "name",
      });
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  async function fetchAllProjectsForExport(): Promise<ProjectListItem[]> {
    const rows: ProjectListItem[] = [];
    let page = 1;
    const exportPageSize = 200;

    while (true) {
      const res = await api.get<PaginatedResponse<ProjectListItem>>(
        "/projects/",
        buildQueryParams(page, exportPageSize),
      );
      rows.push(...res.results);
      if (!res.next || res.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim();
      currentPage = 1;
    }, 300);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    statusFilter = "";
    propertyFilter = "";
    typeFilter = "";
    riskFilter = "";
    sortField = "created_at";
    sortDirection = "desc";
    currentPage = 1;
  }

  function fmtDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function daysUntil(value: string | null): number | null {
    if (!value) return null;
    const diff = new Date(value).getTime() - Date.now();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  function toggleSort(field: SortField) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDirection = "asc";
    }
    currentPage = 1;
  }

  function isSorted(field: SortField): boolean {
    return sortField === field;
  }

  function sortIconClass(field: SortField): string {
    if (!isSorted(field)) return "text-neutral-300";
    return "text-neutral-700";
  }

  type ExportRow = {
    "Project": string;
    "Type": string;
    "Units": number | "";
    "Property": string;
    "Status": string;
    "Risk": string;
    "Progress %": number;
    "Budget": number | "";
    "Start Date": string;
    "Target End": string;
    "Manager": string;
  };

  function toExportRows(rows: ProjectListItem[]): ExportRow[] {
    return rows.map((project) => {
      const budgetNumber = project.budget ? Number(project.budget) : NaN;
      return {
        "Project": project.name,
        "Type": projectTypeLabels[project.project_type],
        "Units": project.number_of_units ?? "",
        "Property": project.property_name ?? "Unlinked property",
        "Status": statusRegistry.get(project.status).label,
        "Risk": project.risk_rating,
        "Progress %": Number(project.progress ?? 0),
        "Budget": Number.isFinite(budgetNumber) ? budgetNumber : "",
        "Start Date": project.start_date ?? "",
        "Target End": project.target_end_date ?? "",
        "Manager": project.project_manager || "",
      };
    });
  }

  function triggerDownload(filename: string, blob: Blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function filenamePrefix(): string {
    const now = new Date();
    const stamp = now.toISOString().slice(0, 10);
    return `projects-${stamp}`;
  }

  function exportCsv(rows: ExportRow[]) {
    const headers = Object.keys(rows[0] ?? {
      "Project": "",
      "Type": "",
      "Property": "",
      "Status": "",
      "Risk": "",
      "Progress %": "",
      "Budget": "",
      "Start Date": "",
      "Target End": "",
      "Manager": "",
    });

    const escape = (value: unknown): string => {
      const text = String(value ?? "");
      if (/[",\n]/.test(text)) {
        return `"${text.replace(/"/g, '""')}"`;
      }
      return text;
    };

    const lines = [headers.join(",")];
    for (const row of rows) {
      lines.push(headers.map((header) => escape(row[header as keyof ExportRow])).join(","));
    }

    const csv = `\uFEFF${lines.join("\n")}`;
    triggerDownload(`${filenamePrefix()}.csv`, new Blob([csv], { type: "text/csv;charset=utf-8;" }));
  }

  function xmlEscape(value: string): string {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function columnLetter(index: number): string {
    let n = index;
    let out = "";
    while (n > 0) {
      const rem = (n - 1) % 26;
      out = String.fromCharCode(65 + rem) + out;
      n = Math.floor((n - 1) / 26);
    }
    return out;
  }

  function exportXlsx(rows: ExportRow[]) {
    const headers = Object.keys(rows[0] ?? {
      "Project": "",
      "Type": "",
      "Property": "",
      "Status": "",
      "Risk": "",
      "Progress %": "",
      "Budget": "",
      "Start Date": "",
      "Target End": "",
      "Manager": "",
    });

    const sheetRows: Array<Array<string | number>> = [
      headers,
      ...rows.map((row) => headers.map((header) => row[header as keyof ExportRow] ?? "")),
    ];

    const rowXml = sheetRows
      .map((values, rowIndex) => {
        const cells = values
          .map((value, colIndex) => {
            const ref = `${columnLetter(colIndex + 1)}${rowIndex + 1}`;
            if (typeof value === "number" && Number.isFinite(value)) {
              return `<c r="${ref}"><v>${value}</v></c>`;
            }
            return `<c r="${ref}" t="inlineStr"><is><t>${xmlEscape(String(value ?? ""))}</t></is></c>`;
          })
          .join("");
        return `<row r="${rowIndex + 1}">${cells}</row>`;
      })
      .join("");

    const worksheet =
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
      `<sheetData>${rowXml}</sheetData>` +
      `</worksheet>`;

    const workbook =
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
      `<sheets><sheet name="Projects" sheetId="1" r:id="rId1"/></sheets>` +
      `</workbook>`;

    const contentTypes =
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
      `<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>` +
      `</Types>`;

    const rels =
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
      `</Relationships>`;

    const workbookRels =
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>` +
      `</Relationships>`;

    const zipped = zipSync(
      {
        "[Content_Types].xml": strToU8(contentTypes),
        "_rels/.rels": strToU8(rels),
        "xl/workbook.xml": strToU8(workbook),
        "xl/_rels/workbook.xml.rels": strToU8(workbookRels),
        "xl/worksheets/sheet1.xml": strToU8(worksheet),
      },
      { level: 6 },
    );
    const xlsxBytes = new Uint8Array(zipped.byteLength);
    xlsxBytes.set(zipped);

    triggerDownload(
      `${filenamePrefix()}.xlsx`,
      new Blob([xlsxBytes.buffer], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      }),
    );
  }

  async function exportPdf(rows: ExportRow[]) {
    const [{ jsPDF }, autoTableModule] = await Promise.all([
      import("jspdf"),
      import("jspdf-autotable"),
    ]);

    const autoTable = autoTableModule.default;

    const doc = new jsPDF({
      orientation: "landscape",
      unit: "pt",
      format: "a4",
    });

    doc.setFontSize(14);
    doc.text("Projects Overview", 30, 30);
    doc.setFontSize(9);
    doc.setTextColor(110);
    doc.text(`Generated on ${new Date().toLocaleString()}`, 30, 46);

    const headers = [
      "Project",
      "Type",
      "Property",
      "Status",
      "Risk",
      "Progress %",
      "Budget",
      "Start",
      "Target End",
      "Manager",
    ];

    const body = rows.map((row) => [
      row["Project"],
      row["Type"],
      row["Property"],
      row["Status"],
      row["Risk"],
      row["Progress %"],
      row["Budget"],
      row["Start Date"],
      row["Target End"],
      row["Manager"],
    ]);

    autoTable(doc, {
      startY: 58,
      head: [headers],
      body,
      theme: "grid",
      styles: {
        fontSize: 8,
        cellPadding: 5,
      },
      headStyles: {
        fillColor: [17, 24, 39],
        textColor: 255,
        fontStyle: "bold",
      },
      alternateRowStyles: {
        fillColor: [249, 250, 251],
      },
      margin: { left: 20, right: 20 },
    });

    doc.save(`${filenamePrefix()}.pdf`);
  }

  async function handleExport(format: ExportFormat) {
    if (exporting) return;
    exporting = format;

    try {
      const rows = await fetchAllProjectsForExport();
      const exportRows = toExportRows(rows);

      if (format === "csv") {
        exportCsv(exportRows);
      } else if (format === "xlsx") {
        exportXlsx(exportRows);
      } else {
        await exportPdf(exportRows);
      }

      toast.success("Export ready", `${rows.length} project records exported as ${format.toUpperCase()}`);
    } catch {
      toast.error("Export failed", "Could not generate project export file.");
    } finally {
      exporting = "";
    }
  }

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void propertyFilter;
    void typeFilter;
    void riskFilter;
    void sortField;
    void sortDirection;
    void currentPage;
    void pageSize;
    fetchProjects();
  });

  $effect(() => {
    fetchProperties();
  });

  const live = useLiveKpis(
    ["Project", "WorkPackage", "VariationOrder"],
    fetchProjects,
    { debounceMs: 3000 },
  );
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Projects</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-900">Overview</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Portfolio-level project register with live filtering, sorting, and export-ready views.
      </p>
    </div>

    <div class="flex items-center gap-2">
      <!-- Export dropdown -->
      <div class="relative">
        <button
          onclick={() => (showExportMenu = !showExportMenu)}
          disabled={Boolean(exporting)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
        >
          {#if exporting}
            <div class="h-3.5 w-3.5 animate-spin rounded-full border border-neutral-300 border-t-neutral-600"></div>
            Exporting...
          {:else}
            <svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Export
            <svg class="h-3.5 w-3.5 text-neutral-400 transition-transform {showExportMenu ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          {/if}
        </button>

        {#if showExportMenu}
          <div class="absolute right-0 z-20 mt-2 w-44 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-lg">
            <button
              class="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors"
              onclick={() => { showExportMenu = false; handleExport("csv"); }}
            >
              <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
              Export as CSV
            </button>
            <button
              class="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors border-t border-neutral-100"
              onclick={() => { showExportMenu = false; handleExport("xlsx"); }}
            >
              <svg class="w-4 h-4 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 13.125c0-.621.504-1.125 1.125-1.125h7.5" />
              </svg>
              Export as XLSX
            </button>
            <button
              class="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors border-t border-neutral-100"
              onclick={() => { showExportMenu = false; handleExport("pdf"); }}
            >
              <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
              Export as PDF
            </button>
          </div>
          <button
            class="fixed inset-0 z-10 cursor-default"
            onclick={() => (showExportMenu = false)}
            tabindex="-1"
            aria-label="Close export menu"
          ></button>
        {/if}
      </div>

    </div>
  </div>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4 sm:p-5">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input
          type="text"
          placeholder="Search name, manager, location..."
          value={searchInput}
          oninput={onSearchInput}
          class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />

        <select
          bind:value={statusFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Statuses</option>
          <option value="planning">Planning</option>
          <option value="in_progress">In Progress</option>
          <option value="on_hold">On Hold</option>
          <option value="completed">Completed</option>
        </select>

        <select
          bind:value={typeFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Types</option>
          <option value="residential">Residential</option>
          <option value="mixed_use">Mixed-Use</option>
          <option value="commercial">Commercial</option>
          <option value="infrastructure">Infrastructure</option>
        </select>

        <select
          bind:value={riskFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Risk Levels</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <select
          bind:value={propertyFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Properties</option>
          {#each properties as property}
            <option value={String(property.id)}>{property.name}</option>
          {/each}
        </select>

        <select
          value={String(pageSize)}
          onchange={(e) => {
            pageSize = Number((e.target as HTMLSelectElement).value);
            currentPage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="10">10 / page</option>
          <option value="25">25 / page</option>
          <option value="50">50 / page</option>
          <option value="100">100 / page</option>
        </select>

        {#if hasActiveFilters}
          <button
            onclick={resetFilters}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          >
            Reset Filters
          </button>
        {/if}

      </div>

      {#if !loading && projects.length > 0}
        <div class="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <div class="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-600">Planning</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{statusCounts.planning}</p>
          </div>
          <div class="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-600">In Progress</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{statusCounts.in_progress}</p>
          </div>
          <div class="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-600">On Hold</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{statusCounts.on_hold}</p>
          </div>
          <div class="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-600">Completed</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{statusCounts.completed}</p>
          </div>
          <div class="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-600">Total Project Budget</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">
              {currency.formatCompact(currentPageBudget)}
            </p>
          </div>
        </div>
      {/if}
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-24">
        <div class="h-7 w-7 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if projects.length === 0}
      <div class="py-24 text-center">
        <p class="text-sm text-neutral-400">No projects found for this filter set.</p>
        <a href="/projects/blueprints" class="mt-3 inline-block text-sm font-medium text-neutral-900 hover:underline">
          Start with a Blueprint &rarr;
        </a>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full min-w-[1060px] text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/80">
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("name")}>
                  Project
                  <svg class="h-3.5 w-3.5 {sortIconClass('name')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("name") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Property</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("status")}>
                  Status
                  <svg class="h-3.5 w-3.5 {sortIconClass('status')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("status") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("risk_rating")}>
                  Risk
                  <svg class="h-3.5 w-3.5 {sortIconClass('risk_rating')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("risk_rating") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("start_date")}>
                  Start
                  <svg class="h-3.5 w-3.5 {sortIconClass('start_date')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("start_date") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("target_end_date")}>
                  Target End
                  <svg class="h-3.5 w-3.5 {sortIconClass('target_end_date')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("target_end_date") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
            </tr>
          </thead>

          <tbody class="divide-y divide-neutral-100">
            {#each projects as project (project.id)}
              {@const due = daysUntil(project.target_end_date)}
              <tr
                class="cursor-pointer bg-white transition-colors hover:bg-neutral-50"
                onclick={() => goto(`/projects/${project.id}`)}
              >
                <td class="px-5 py-4">
                  <div>
                    <p class="font-semibold text-neutral-900">{project.name}</p>
                    <p class="mt-0.5 text-xs text-neutral-500">{project.location || project.spv_entity || "No location"}</p>
                  </div>
                </td>

                <td class="px-5 py-4">
                  <span class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {projectTypeLabels[project.project_type]}
                  </span>
                </td>

                <td class="px-5 py-4 text-neutral-600">{project.property_name ?? "Unlinked property"}</td>

                <td class="px-5 py-4">
                  <StatusBadge status={project.status} />
                </td>

                <td class="px-5 py-4">
                  <StatusBadge status={project.risk_rating} />
                </td>

                <td class="px-5 py-4">
                  <div class="flex items-center gap-2">
                    <div class="h-2 w-24 overflow-hidden rounded-full bg-neutral-100">
                      <div
                        class="h-2 rounded-full {project.progress >= 80 ? 'bg-emerald-500' : project.progress >= 50 ? 'bg-blue-600' : 'bg-amber-500'}"
                        style="width: {Math.min(Math.max(project.progress, 0), 100)}%"
                      ></div>
                    </div>
                    <span class="text-xs font-medium text-neutral-600 tabular-nums">{project.progress}%</span>
                  </div>
                </td>

                <td class="px-5 py-4 text-neutral-600">{fmtDate(project.start_date)}</td>

                <td class="px-5 py-4">
                  <p class="text-neutral-600">{fmtDate(project.target_end_date)}</p>
                  {#if due !== null}
                    <p class="mt-0.5 text-[11px] font-medium {due < 0 ? 'text-rose-600' : due <= 14 ? 'text-amber-600' : 'text-neutral-400'}">
                      {#if due < 0}
                        {Math.abs(due)}d overdue
                      {:else}
                        {due}d left
                      {/if}
                    </p>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex flex-col gap-3 border-t border-neutral-200 px-5 py-3.5 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-neutral-500">
          Showing {startItem}-{endItem} of {totalCount} projects
        </p>

        <div class="flex items-center justify-between gap-3 sm:justify-end">
          <p class="text-sm text-neutral-500">Page {currentPage} of {totalPages}</p>
          <div class="flex items-center gap-1">
            <button
              onclick={() => (currentPage = Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Prev
            </button>

            {#each visiblePages as page}
              <button
                onclick={() => (currentPage = page)}
                class="min-w-8 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {page === currentPage ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
              >
                {page}
              </button>
            {/each}

            <button
              onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    {/if}
  </section>
</div>
