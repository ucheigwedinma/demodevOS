<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import type { SupportDeskBreakdownItem, SupportDeskReportsOverview } from "$lib/types";

  let loading = $state(true);
  let errorMessage = $state("");
  let overview = $state<SupportDeskReportsOverview | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function formatPercent(value: number): string {
    return `${value.toFixed(2)}%`;
  }

  function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  }

  function maxCount(rows: SupportDeskBreakdownItem[]): number {
    return Math.max(1, ...rows.map((row) => row.count));
  }

  async function loadOverview() {
    loading = true;
    errorMessage = "";
    try {
      overview = await api.get<SupportDeskReportsOverview>("/support-desk/reports/overview/");
    } catch (error) {
      overview = null;
      errorMessage = parseError(error, "Could not load support report analytics.");
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void loadOverview();
  });

  let departmentPeak = $derived(maxCount(overview?.tickets_by_department ?? []));
  let categoryPeak = $derived(maxCount(overview?.tickets_by_category ?? []));
  let ticketTrendPeak = $derived(Math.max(1, ...(overview?.ticket_trend ?? []).map((row) => row.created_count)));
  let resolutionTrendPeak = $derived(Math.max(1, ...(overview?.resolution_trend ?? []).map((row) => row.average_resolution_hours ?? 0)));
  let slaTrendPeak = $derived(Math.max(1, ...(overview?.sla_performance_trend ?? []).map((row) => row.compliance_rate)));
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
  </div>
{:else if errorMessage}
  <div class="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-800">
    <h1 class="text-lg font-semibold">Reports unavailable</h1>
    <p class="mt-2 text-sm">{errorMessage}</p>
    <button
      type="button"
      onclick={() => loadOverview()}
      class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else if overview}
  <div class="space-y-8">
    <section class="space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="max-w-3xl">
          <h1 class="text-2xl font-bold text-neutral-800">Support Performance Analytics</h1>
          <p class="mt-1 text-sm text-neutral-500">
            Standard reports and trend analytics for ticket operations, SLA health, escalations, and support quality.
          </p>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-700">
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Window</p>
          <p class="mt-2 font-semibold text-neutral-800">{formatDate(overview.window_start)} - {formatDate(overview.window_end)}</p>
          <p class="mt-1 text-xs text-neutral-500">Total Tickets: {overview.total_tickets}</p>
        </div>
      </div>
    </section>

    <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400">Total Tickets</p>
        <p class="mt-3 text-3xl font-semibold text-neutral-800">{overview.total_tickets}</p>
      </article>
      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400">Resolution Time</p>
        <p class="mt-3 text-3xl font-semibold text-neutral-800">{overview.resolution_time_average_display}</p>
      </article>
      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400">SLA Compliance</p>
        <p class="mt-3 text-3xl font-semibold text-emerald-700">{formatPercent(overview.sla_compliance.compliance_rate)}</p>
      </article>
      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400">Escalation Rate</p>
        <p class="mt-3 text-3xl font-semibold text-rose-700">{formatPercent(overview.escalation_rate.escalation_rate)}</p>
      </article>
    </section>

    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-neutral-950">Standard Reports</h2>
      <p class="mt-1 text-sm text-neutral-500">Tickets by Department, Tickets by Category, Resolution Time, Agent Performance, SLA Compliance, Escalation Rate, Customer Satisfaction.</p>

      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {#each overview.standard_reports as report}
          <article class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <h3 class="text-sm font-semibold text-neutral-800">{report.title}</h3>
            <p class="mt-2 text-xs leading-5 text-neutral-600">{report.description}</p>
          </article>
        {/each}
      </div>
    </section>

    <section class="grid gap-6 xl:grid-cols-2">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Tickets by Department</h2>
        <div class="mt-5 space-y-4">
          {#if overview.tickets_by_department.length === 0}
            <p class="text-sm text-neutral-500">No department distribution available in this window.</p>
          {:else}
            {#each overview.tickets_by_department as row}
              <div class="space-y-2">
                <div class="flex items-center justify-between gap-4 text-sm">
                  <p class="font-medium text-neutral-800">{row.label}</p>
                  <p class="font-semibold text-neutral-800">{row.count}</p>
                </div>
                <div class="h-2 rounded-full bg-neutral-100">
                  <div class="h-2 rounded-full bg-cyan-500" style={`width:${Math.max(6, Math.round((row.count / departmentPeak) * 100))}%`}></div>
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Tickets by Category</h2>
        <div class="mt-5 space-y-4">
          {#if overview.tickets_by_category.length === 0}
            <p class="text-sm text-neutral-500">No category distribution available in this window.</p>
          {:else}
            {#each overview.tickets_by_category as row}
              <div class="space-y-2">
                <div class="flex items-center justify-between gap-4 text-sm">
                  <p class="font-medium text-neutral-800">{row.label}</p>
                  <p class="font-semibold text-neutral-800">{row.count}</p>
                </div>
                <div class="h-2 rounded-full bg-neutral-100">
                  <div class="h-2 rounded-full bg-indigo-500" style={`width:${Math.max(6, Math.round((row.count / categoryPeak) * 100))}%`}></div>
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </article>
    </section>

    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-neutral-950">Agent Performance</h2>
      {#if overview.agent_performance.length === 0}
        <p class="mt-4 text-sm text-neutral-500">No agent performance rows available for this window.</p>
      {:else}
        <div class="mt-4 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500">
              <tr>
                <th class="px-4 py-3">Agent</th>
                <th class="px-4 py-3">Handled</th>
                <th class="px-4 py-3">Resolved</th>
                <th class="px-4 py-3">Avg Resolution</th>
                <th class="px-4 py-3">SLA Breaches</th>
                <th class="px-4 py-3">CSAT</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100 bg-white">
              {#each overview.agent_performance as row}
                <tr>
                  <td class="px-4 py-3 font-medium text-neutral-800">{row.agent_name}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.total_tickets}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.resolved_tickets}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.average_resolution_display}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.sla_breaches}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.customer_satisfaction_display}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <section class="grid gap-6 xl:grid-cols-3">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-base font-semibold text-neutral-950">Ticket Trend</h2>
        <p class="mt-1 text-xs text-neutral-500">Created ticket volume across the selected window.</p>
        <div class="mt-5 overflow-x-auto">
          <div class="flex min-w-max items-end gap-1 pb-1">
            {#each overview.ticket_trend as row}
              <div class="flex flex-col items-center gap-1">
                <div class="h-24 w-3 rounded-sm bg-cyan-500" style={`height:${Math.max(4, Math.round((row.created_count / ticketTrendPeak) * 96))}px`} title={`${formatDate(row.date)}: ${row.created_count}`}></div>
              </div>
            {/each}
          </div>
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-base font-semibold text-neutral-950">Resolution Trend</h2>
        <p class="mt-1 text-xs text-neutral-500">Average resolution time (hours) per day.</p>
        <div class="mt-5 overflow-x-auto">
          <div class="flex min-w-max items-end gap-1 pb-1">
            {#each overview.resolution_trend as row}
              <div class="flex flex-col items-center gap-1">
                <div class="h-24 w-3 rounded-sm bg-emerald-500" style={`height:${Math.max(4, Math.round((((row.average_resolution_hours ?? 0) / resolutionTrendPeak) * 96)))}px`} title={`${formatDate(row.date)}: ${row.average_resolution_display}`}></div>
              </div>
            {/each}
          </div>
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-base font-semibold text-neutral-950">SLA Performance</h2>
        <p class="mt-1 text-xs text-neutral-500">Daily compliance rate from resolved tickets.</p>
        <div class="mt-5 overflow-x-auto">
          <div class="flex min-w-max items-end gap-1 pb-1">
            {#each overview.sla_performance_trend as row}
              <div class="flex flex-col items-center gap-1">
                <div class="h-24 w-3 rounded-sm bg-violet-500" style={`height:${Math.max(4, Math.round((row.compliance_rate / slaTrendPeak) * 96))}px`} title={`${formatDate(row.date)}: ${formatPercent(row.compliance_rate)}`}></div>
              </div>
            {/each}
          </div>
        </div>
      </article>
    </section>
  </div>
{/if}
