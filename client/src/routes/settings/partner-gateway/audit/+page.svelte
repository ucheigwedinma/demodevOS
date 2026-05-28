<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    PartnerOnboardingAuditEvent,
    PartnerOnboardingCaseListItem,
  } from "$lib/types";

  let loading = $state(true);
  let events = $state<PartnerOnboardingAuditEvent[]>([]);
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let caseFilter = $state("");
  let eventFilter = $state("");
  let search = $state("");

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  async function fetchAllPages<T>(endpoint: string, params: Record<string, string> = {}): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;
    while (page <= 40) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });
      if (Array.isArray(payload)) {
        rows.push(...payload);
        break;
      }
      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }
    return rows;
  }

  async function loadData() {
    loading = true;
    try {
      const [eventRows, caseRows] = await Promise.all([
        fetchAllPages<PartnerOnboardingAuditEvent>("/partners/audit-events/", { ordering: "-created_at", page_size: "300" }),
        fetchAllPages<PartnerOnboardingCaseListItem>("/partners/cases/", { ordering: "-created_at", page_size: "200" }),
      ]);
      events = eventRows;
      cases = caseRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load onboarding audit timeline."));
    } finally {
      loading = false;
    }
  }

  function caseTitle(caseId: number): string {
    const row = cases.find((item) => item.id === caseId);
    return row ? row.title : `Case #${caseId}`;
  }

  const filteredEvents = $derived.by(() => {
    return events.filter((row) => {
      if (caseFilter && String(row.case) !== caseFilter) return false;
      if (eventFilter && row.event_type !== eventFilter) return false;
      if (!search.trim()) return true;
      const needle = search.trim().toLowerCase();
      const haystack = `${row.message} ${row.actor_email ?? ""} ${row.actor_role_label}`.toLowerCase();
      return haystack.includes(needle);
    });
  });

  $effect(() => {
    loadData();
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-semibold text-neutral-800">Audit Timeline</h2>
    <p class="mt-1 text-sm text-neutral-500">Immutable event history for onboarding, approvals, entitlements, and portal access grants.</p>
  </div>

  <section class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 p-4">
      <div class="grid gap-3 md:grid-cols-4">
        <input type="text" bind:value={search} placeholder="Search message/actor..." class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />
        <select bind:value={caseFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Cases</option>
          {#each cases as row}
            <option value={String(row.id)}>{row.title}</option>
          {/each}
        </select>
        <select bind:value={eventFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Events</option>
          <option value="case_created">Case Created</option>
          <option value="stages_initialized">Stages Initialized</option>
          <option value="stage_status_changed">Stage Status Changed</option>
          <option value="case_status_changed">Case Status Changed</option>
          <option value="approval_recorded">Approval Recorded</option>
          <option value="entitlement_provisioned">Entitlement Provisioned</option>
          <option value="portal_access_granted">Portal Access Granted</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else if filteredEvents.length === 0}
      <div class="px-6 py-10 text-center text-sm text-neutral-500">No audit events found.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1200px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Time</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Case</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Event</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Message</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Actor</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">IP</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each filteredEvents as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{new Date(row.created_at).toLocaleString()}</td>
                <td class="px-4 py-3 text-neutral-800">{caseTitle(row.case)}</td>
                <td class="px-4 py-3 text-neutral-600">{row.event_type.replaceAll("_", " ")}</td>
                <td class="px-4 py-3 text-neutral-700">{row.message}</td>
                <td class="px-4 py-3 text-neutral-600">{row.actor_email || row.actor_role_label || "system"}</td>
                <td class="px-4 py-3 text-neutral-500">{row.ip_address || "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>
