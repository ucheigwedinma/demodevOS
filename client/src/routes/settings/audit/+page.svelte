<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { AuditComplianceSettings, AuditLogEntry, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const LOG_PAGE_SIZE_OPTIONS = [10, 20, 50];

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<AuditComplianceSettings>>({});
  let auditLogs = $state<AuditLogEntry[]>([]);
  let logsLoading = $state(true);
  let logsSearch = $state("");
  let logsActionFilter = $state("");
  let logsModelFilter = $state("");
  let logsSort = $state("timestamp_desc");
  let logsPage = $state(1);
  let logsPageSize = $state(10);
  let expandedLogIds = $state<number[]>([]);

  async function loadSettings() {
    try {
      const data = await api.get<AuditComplianceSettings>("/settings/audit/");
      form = data;
    } catch {
      toast.error("Load failed", "Could not load audit & compliance settings.");
    } finally {
      loading = false;
    }
  }

  async function loadAuditLogs() {
    try {
      const rows: AuditLogEntry[] = [];
      let page = 1;
      const maxPages = 25;
      let hasMore = true;

      while (hasMore && page <= maxPages) {
        const data = await api.get<PaginatedResponse<AuditLogEntry>>("/settings/audit/logs/", {
          page: String(page),
          page_size: "200",
        });
        rows.push(...data.results);
        hasMore = Boolean(data.next);
        page += 1;
      }

      if (hasMore) {
        toast.error(
          "Audit logs truncated",
          "Loaded the latest activity only. Narrow filters to reduce result size.",
        );
      }

      auditLogs = rows;
    } catch {
      // Logs endpoint may fail if no entries yet — that's ok
      auditLogs = [];
    } finally {
      logsLoading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      const {
        id,
        created_at,
        updated_at,
        audit_status,
        ...payload
      } = form as AuditComplianceSettings;
      await api.patch<AuditComplianceSettings>("/settings/audit/", payload);
      toast.success("Saved", "Audit & compliance settings updated successfully.");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  function formatTimestamp(ts: string): string {
    const d = new Date(ts);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatDateTimeLong(ts: string): string {
    const d = new Date(ts);
    return d.toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function actionBadgeClass(action: string): string {
    if (action === "Create") return "bg-emerald-100 text-emerald-800 border-emerald-200";
    if (action === "Update") return "bg-amber-100 text-amber-800 border-amber-200";
    if (action === "Delete") return "bg-rose-100 text-rose-800 border-rose-200";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function normalizeForSearch(value: string | null | undefined): string {
    return (value || "").trim().toLowerCase();
  }

  function toDisplayValue(value: unknown): string {
    if (value === null || value === undefined) return "—";
    if (typeof value === "string") return value || "—";
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  type ChangeRow = { field: string; before: string; after: string };

  function extractChangeRows(changes: Record<string, unknown>): ChangeRow[] {
    if (!changes || typeof changes !== "object") return [];
    const rows: ChangeRow[] = [];

    for (const [field, raw] of Object.entries(changes)) {
      if (Array.isArray(raw) && raw.length >= 2) {
        rows.push({
          field,
          before: toDisplayValue(raw[0]),
          after: toDisplayValue(raw[1]),
        });
        continue;
      }
      if (raw && typeof raw === "object") {
        const asObject = raw as Record<string, unknown>;
        if ("old" in asObject || "new" in asObject) {
          rows.push({
            field,
            before: toDisplayValue(asObject.old),
            after: toDisplayValue(asObject.new),
          });
          continue;
        }
      }
      rows.push({
        field,
        before: "—",
        after: toDisplayValue(raw),
      });
    }

    return rows;
  }

  function toggleLogExpanded(id: number) {
    if (expandedLogIds.includes(id)) {
      expandedLogIds = expandedLogIds.filter((item) => item !== id);
    } else {
      expandedLogIds = [...expandedLogIds, id];
    }
  }

  const logModelOptions = $derived.by(() => {
    return Array.from(new Set(auditLogs.map((entry) => entry.content_type_name)))
      .filter((item) => item.trim().length > 0)
      .sort((a, b) => a.localeCompare(b));
  });

  const filteredLogs = $derived.by(() => {
    let rows = auditLogs.filter((entry) => {
      if (logsActionFilter && entry.action_display !== logsActionFilter) return false;
      if (logsModelFilter && entry.content_type_name !== logsModelFilter) return false;
      if (!logsSearch.trim()) return true;

      const needle = normalizeForSearch(logsSearch);
      const haystack = normalizeForSearch(
        `${entry.content_type_name} ${entry.object_repr} ${entry.actor_email} ${entry.actor_role} ${entry.ip_address ?? ""} ${entry.action_display}`,
      );
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (logsSort === "timestamp_asc") return a.timestamp.localeCompare(b.timestamp);
      if (logsSort === "action_asc") return a.action_display.localeCompare(b.action_display);
      if (logsSort === "model_asc") return a.content_type_name.localeCompare(b.content_type_name);
      if (logsSort === "actor_asc") return a.actor_email.localeCompare(b.actor_email);
      return b.timestamp.localeCompare(a.timestamp);
    });

    return rows;
  });

  const logsTotalPages = $derived(Math.max(1, Math.ceil(filteredLogs.length / logsPageSize)));
  const logsStart = $derived(filteredLogs.length === 0 ? 0 : (logsPage - 1) * logsPageSize + 1);
  const logsEnd = $derived(Math.min(filteredLogs.length, logsPage * logsPageSize));
  const logsPageRows = $derived(filteredLogs.slice(logsStart - 1, logsEnd));

  $effect(() => {
    if (logsPage > logsTotalPages) logsPage = logsTotalPages;
    if (logsPage < 1) logsPage = 1;
  });

  $effect(() => {
    loadSettings();
    loadAuditLogs();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Audit & Compliance</h2>
      <p class="mt-1 text-sm text-neutral-500">Configure audit logging, compliance controls, and data access policies for ISO 9001 alignment.</p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <div class="space-y-6 max-w-6xl">

    <!-- 8.1 Audit Logging -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-lg font-semibold tracking-tight text-neutral-800 mb-1">Audit Logging</h3>
      <p class="text-xs text-neutral-500 mb-5">Every edit, approval, and deletion is logged with timestamp, user ID, and before/after values.</p>

      <!-- Enable toggle -->
      <div class="flex items-center justify-between py-3 border-b border-neutral-100">
        <div>
          <p class="text-sm font-medium text-neutral-800">Enable Audit Logging</p>
          <p class="text-xs text-neutral-500 mt-0.5">Track all changes across core business models.</p>
        </div>
        <button
          type="button"
          onclick={() => (form.audit_logging_enabled = !form.audit_logging_enabled)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.audit_logging_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.audit_logging_enabled}
          aria-label="Toggle audit logging"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.audit_logging_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>

      <!-- Status badges -->
      <div class="flex gap-3 py-4 border-b border-neutral-100">
        <div class="flex items-center gap-2">
          <span class="text-xs text-neutral-500">Models tracked</span>
          <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">
            {form.audit_status?.models_tracked ?? 0}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-neutral-500">Middleware</span>
          {#if form.audit_status?.middleware_active}
            <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">Active</span>
          {:else}
            <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-500">Inactive</span>
          {/if}
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-neutral-500">Log entries</span>
          <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
            {(form.audit_status?.total_log_entries ?? 0).toLocaleString()}
          </span>
        </div>
      </div>

      <!-- Retention -->
      <div class="pt-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label for="retention" class="block text-sm font-medium text-neutral-700 mb-1.5">Retention Period (days)</label>
            <input
              id="retention"
              type="number"
              min="30"
              max="2555"
              bind:value={form.audit_retention_days}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
            <p class="text-xs text-neutral-400 mt-1">30 to 2,555 days (7 years).</p>
          </div>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="mt-6">
        <div class="mb-3 flex items-center justify-between gap-3">
          <p class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Recent Activity</p>
          <p class="text-[11px] text-neutral-400">All tracked create/update/delete events</p>
        </div>

        <div class="rounded-lg border border-neutral-200 overflow-hidden">
          <div class="border-b border-neutral-200 bg-neutral-50/70 px-3 py-3">
            <div class="grid grid-cols-1 gap-2 lg:grid-cols-6">
              <input
                type="text"
                bind:value={logsSearch}
                oninput={() => (logsPage = 1)}
                placeholder="Search actor, model, record..."
                class="lg:col-span-2 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              />
              <select
                bind:value={logsActionFilter}
                onchange={() => (logsPage = 1)}
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Actions</option>
                <option value="Create">Create</option>
                <option value="Update">Update</option>
                <option value="Delete">Delete</option>
              </select>
              <select
                bind:value={logsModelFilter}
                onchange={() => (logsPage = 1)}
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="">All Models</option>
                {#each logModelOptions as modelName}
                  <option value={modelName}>{modelName}</option>
                {/each}
              </select>
              <select
                bind:value={logsSort}
                onchange={() => (logsPage = 1)}
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                <option value="timestamp_desc">Latest First</option>
                <option value="timestamp_asc">Oldest First</option>
                <option value="action_asc">Action</option>
                <option value="model_asc">Model</option>
                <option value="actor_asc">Actor</option>
              </select>
              <select
                bind:value={logsPageSize}
                onchange={() => (logsPage = 1)}
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              >
                {#each LOG_PAGE_SIZE_OPTIONS as size}
                  <option value={size}>{size} / page</option>
                {/each}
              </select>
            </div>
          </div>

          {#if logsLoading}
            <div class="flex items-center justify-center py-10">
              <div class="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
            </div>
          {:else if filteredLogs.length === 0}
            <div class="px-4 py-8 text-center">
              <p class="text-xs text-neutral-400">No audit log entries match the current filters.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[1220px] w-full table-fixed">
                <thead>
                  <tr class="border-b border-neutral-200 bg-neutral-50">
                    <th class="w-[170px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Timestamp</th>
                    <th class="w-[110px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Action</th>
                    <th class="w-[140px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Model</th>
                    <th class="w-[290px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Record</th>
                    <th class="w-[190px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Actor</th>
                    <th class="w-[160px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Role</th>
                    <th class="w-[140px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-600">IP Address</th>
                    <th class="w-[100px] px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-600">Details</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each logsPageRows as entry (entry.id)}
                    <tr class="hover:bg-neutral-50">
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-600 whitespace-nowrap">{formatTimestamp(entry.timestamp)}</td>
                      <td class="px-3 py-2.5 align-top text-xs">
                        <span class={`inline-flex items-center rounded-md border px-2 py-0.5 font-medium ${actionBadgeClass(entry.action_display)}`}>
                          {entry.action_display}
                        </span>
                      </td>
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-700">{entry.content_type_name}</td>
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-800">
                        <div class="line-clamp-2 wrap-break-word">{entry.object_repr}</div>
                      </td>
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-700">
                        <div class="truncate">{entry.actor_email}</div>
                      </td>
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-600">
                        <div class="truncate">{entry.actor_role}</div>
                      </td>
                      <td class="px-3 py-2.5 align-top text-xs text-neutral-500 whitespace-nowrap">{entry.ip_address || "—"}</td>
                      <td class="px-3 py-2.5 align-top text-right">
                        <button
                          type="button"
                          onclick={() => toggleLogExpanded(entry.id)}
                          class="inline-flex items-center rounded-md border border-neutral-300 px-2 py-1 text-[11px] font-medium text-neutral-700 hover:bg-neutral-100"
                        >
                          {expandedLogIds.includes(entry.id) ? "Hide" : "Expand"}
                        </button>
                      </td>
                    </tr>
                    {#if expandedLogIds.includes(entry.id)}
                      <tr class="bg-neutral-50/60">
                        <td colspan="8" class="px-4 py-3">
                          <div class="grid grid-cols-1 gap-3 xl:grid-cols-3">
                            <div class="rounded-md border border-neutral-200 bg-white p-3">
                              <p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Entry Summary</p>
                              <dl class="space-y-1.5 text-xs">
                                <div class="grid grid-cols-[110px_1fr] gap-2">
                                  <dt class="text-neutral-500">Timestamp</dt>
                                  <dd class="text-neutral-800">{formatDateTimeLong(entry.timestamp)}</dd>
                                </div>
                                <div class="grid grid-cols-[110px_1fr] gap-2">
                                  <dt class="text-neutral-500">Action</dt>
                                  <dd class="text-neutral-800">{entry.action_display}</dd>
                                </div>
                                <div class="grid grid-cols-[110px_1fr] gap-2">
                                  <dt class="text-neutral-500">Model</dt>
                                  <dd class="text-neutral-800">{entry.content_type_name}</dd>
                                </div>
                                <div class="grid grid-cols-[110px_1fr] gap-2">
                                  <dt class="text-neutral-500">Record</dt>
                                  <dd class="text-neutral-800 wrap-break-word">{entry.object_repr}</dd>
                                </div>
                              </dl>
                            </div>

                            <div class="rounded-md border border-neutral-200 bg-white p-3">
                              <p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actor Context</p>
                              <dl class="space-y-1.5 text-xs">
                                <div class="grid grid-cols-[80px_1fr] gap-2">
                                  <dt class="text-neutral-500">Email</dt>
                                  <dd class="text-neutral-800 wrap-break-word">{entry.actor_email}</dd>
                                </div>
                                <div class="grid grid-cols-[80px_1fr] gap-2">
                                  <dt class="text-neutral-500">Role</dt>
                                  <dd class="text-neutral-800">{entry.actor_role}</dd>
                                </div>
                                <div class="grid grid-cols-[80px_1fr] gap-2">
                                  <dt class="text-neutral-500">IP</dt>
                                  <dd class="text-neutral-800">{entry.ip_address || "—"}</dd>
                                </div>
                              </dl>
                            </div>

                            <div class="rounded-md border border-neutral-200 bg-white p-3 xl:col-span-1">
                              <p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Field Changes</p>
                              {#if extractChangeRows(entry.changes).length === 0}
                                <p class="text-xs text-neutral-500">No field-level change payload captured.</p>
                              {:else}
                                <div class="max-h-48 overflow-auto rounded border border-neutral-100">
                                  <table class="w-full">
                                    <thead>
                                      <tr class="bg-neutral-50">
                                        <th class="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Field</th>
                                        <th class="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Before</th>
                                        <th class="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">After</th>
                                      </tr>
                                    </thead>
                                    <tbody class="divide-y divide-neutral-100">
                                      {#each extractChangeRows(entry.changes) as row}
                                        <tr>
                                          <td class="px-2 py-1.5 align-top text-[11px] font-medium text-neutral-700">{row.field}</td>
                                          <td class="px-2 py-1.5 align-top text-[11px] text-neutral-600 wrap-break-word">{row.before}</td>
                                          <td class="px-2 py-1.5 align-top text-[11px] text-neutral-800 wrap-break-word">{row.after}</td>
                                        </tr>
                                      {/each}
                                    </tbody>
                                  </table>
                                </div>
                              {/if}
                            </div>
                          </div>
                        </td>
                      </tr>
                    {/if}
                  {/each}
                </tbody>
              </table>
            </div>

            <div class="flex items-center justify-between border-t border-neutral-200 px-3 py-2.5">
              <p class="text-[11px] text-neutral-500">Showing {logsStart}-{logsEnd} of {filteredLogs.length}</p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => (logsPage = Math.max(1, logsPage - 1))}
                  disabled={logsPage === 1}
                  class="rounded-md border border-neutral-300 px-2.5 py-1 text-[11px] font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-40"
                >
                  Previous
                </button>
                <span class="text-[11px] text-neutral-600">Page {logsPage} of {logsTotalPages}</span>
                <button
                  type="button"
                  onclick={() => (logsPage = Math.min(logsTotalPages, logsPage + 1))}
                  disabled={logsPage === logsTotalPages}
                  class="rounded-md border border-neutral-300 px-2.5 py-1 text-[11px] font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </section>

    <!-- 8.2 Compliance Controls -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-lg font-semibold tracking-tight text-neutral-800 mb-1">Compliance Controls</h3>
      <p class="text-xs text-neutral-500 mb-5">Enforce data integrity and change management policies.</p>

      <!-- Mandatory Fields -->
      <div class="flex items-center justify-between py-3 border-b border-neutral-100">
        <div>
          <p class="text-sm font-medium text-neutral-800">Mandatory Fields Enforcement</p>
          <p class="text-xs text-neutral-500 mt-0.5">Prevent saving records when required fields are empty.</p>
        </div>
        <button
          type="button"
          onclick={() => (form.mandatory_fields_enforced = !form.mandatory_fields_enforced)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.mandatory_fields_enforced ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.mandatory_fields_enforced}
          aria-label="Toggle mandatory fields enforcement"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.mandatory_fields_enforced ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>

      <!-- Financial Period Locking -->
      <div class="py-3 border-b border-neutral-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-neutral-800">Financial Period Locking</p>
            <p class="text-xs text-neutral-500 mt-0.5">Lock all financial records (bills, invoices, budgets) before a cutoff date.</p>
          </div>
          <button
            type="button"
            onclick={() => (form.financial_period_locking = !form.financial_period_locking)}
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {form.financial_period_locking ? 'bg-neutral-800' : 'bg-neutral-200'}"
            role="switch"
            aria-checked={form.financial_period_locking}
            aria-label="Toggle financial period locking"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                     {form.financial_period_locking ? 'translate-x-5' : 'translate-x-0.5'}"
              style="margin-top: 2px;"
            ></span>
          </button>
        </div>
        {#if form.financial_period_locking}
          <div class="mt-3 sm:w-1/2">
            <label for="locked_date" class="block text-sm font-medium text-neutral-700 mb-1.5">Lock Records Before</label>
            <DateInput id="locked_date" bind:value={form.locked_before_date} />
            <p class="text-xs text-neutral-400 mt-1">All records dated before this date will be read-only.</p>
          </div>
        {/if}
      </div>

      <!-- Change Approval -->
      <div class="flex items-center justify-between pt-3">
        <div>
          <p class="text-sm font-medium text-neutral-800">Change Approval Required</p>
          <p class="text-xs text-neutral-500 mt-0.5">Require approval before changes to critical records take effect.</p>
        </div>
        <button
          type="button"
          onclick={() => (form.change_approval_required = !form.change_approval_required)}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.change_approval_required ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.change_approval_required}
          aria-label="Toggle change approval requirement"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.change_approval_required ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>
    </section>

    <!-- 8.3 Data Access & Reporting -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-lg font-semibold tracking-tight text-neutral-800 mb-1">Data Access & Reporting</h3>
      <p class="text-xs text-neutral-500 mb-5">Configure access log retention and view data change history.</p>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="access_retention" class="block text-sm font-medium text-neutral-700 mb-1.5">Access Log Retention (days)</label>
          <input
            id="access_retention"
            type="number"
            min="7"
            max="365"
            bind:value={form.access_log_retention_days}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          <p class="text-xs text-neutral-400 mt-1">7 to 365 days. Controls how long access logs are retained.</p>
        </div>
      </div>

      <!-- Summary -->
      <div class="mt-5 flex gap-4">
        <div class="flex-1 rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
          <p class="text-xs text-neutral-500">Total audit entries</p>
          <p class="text-lg font-bold text-neutral-800 mt-0.5">{(form.audit_status?.total_log_entries ?? 0).toLocaleString()}</p>
        </div>
        <div class="flex-1 rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
          <p class="text-xs text-neutral-500">Models under audit</p>
          <p class="text-lg font-bold text-neutral-800 mt-0.5">{form.audit_status?.models_tracked ?? 0}</p>
        </div>
        <div class="flex-1 rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
          <p class="text-xs text-neutral-500">Audit retention</p>
          <p class="text-lg font-bold text-neutral-800 mt-0.5">{form.audit_retention_days ?? 365}d</p>
        </div>
      </div>
    </section>

  </div>
{/if}
