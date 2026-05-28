<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type { LeadDetail, PipelineStage } from "$lib/types";

  type LeadModalTab = "overview" | "activities" | "preferences" | "timeline";

  let {
    open = false,
    leadId = null,
    onClose = undefined,
    backdropZ = 70,
    panelZ = 80,
  }: {
    open?: boolean;
    leadId?: number | null;
    onClose?: (() => void) | undefined;
    backdropZ?: number;
    panelZ?: number;
  } = $props();

  let loading = $state(false);
  let error = $state("");
  let leadDetail = $state<LeadDetail | null>(null);
  let activeTab = $state<LeadModalTab>("overview");
  let loadedLeadId = $state<number | null>(null);

  const tabs: { key: LeadModalTab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "activities", label: "Activities" },
    { key: "preferences", label: "Preferences" },
    { key: "timeline", label: "Timeline" },
  ];

  const pipelineStages: { key: PipelineStage; label: string }[] = [
    { key: "inquiry", label: "Inquiry" },
    { key: "qualified", label: "Qualified" },
    { key: "site_visit", label: "Site Visit" },
    { key: "offer_made", label: "Offer Made" },
    { key: "reservation", label: "Reservation" },
    { key: "spa_issued", label: "SPA Issued" },
    { key: "closed", label: "Closed" },
  ];

  const leadPriorityLabels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  const leadTypeLabels: Record<string, string> = {
    buyer: "Buyer",
    tenant: "Tenant",
    investor: "Investor",
  };

  const leadPaymentCapabilityLabels: Record<string, string> = {
    cash: "Cash",
    mortgage: "Mortgage",
    installment: "Installment",
    mixed: "Mixed",
    undetermined: "Undetermined",
  };

  const leadStageDateKeys: Record<PipelineStage, keyof LeadDetail> = {
    inquiry: "inquiry_date",
    qualified: "qualified_date",
    site_visit: "site_visit_date",
    offer_made: "offer_date",
    reservation: "reservation_date",
    spa_issued: "spa_issued_date",
    closed: "closed_date",
  };

  const sortedLeadActivities = $derived(
    leadDetail
      ? [...leadDetail.activities].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
      : [],
  );

  const sortedLeadTransitions = $derived(
    leadDetail
      ? [...leadDetail.stage_transitions].sort(
          (a, b) => new Date(b.transitioned_at).getTime() - new Date(a.transitioned_at).getTime(),
        )
      : [],
  );

  const leadCurrentStageIndex = $derived.by(() => {
    const detail = leadDetail;
    if (!detail) return -1;
    return pipelineStages.findIndex((stage) => stage.key === detail.pipeline_stage);
  });

  function formatLeadDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatLeadDateTime(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatLeadAmount(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return currency.format(parseFloat(value));
  }

  function leadStageLabel(stage: PipelineStage): string {
    return pipelineStages.find((entry) => entry.key === stage)?.label ?? stage;
  }

  async function fetchLeadDetail(id: number) {
    loading = true;
    error = "";
    try {
      leadDetail = await api.get<LeadDetail>(`/crm/leads/${id}/`);
      loadedLeadId = id;
    } catch (err) {
      leadDetail = null;
      loadedLeadId = null;
      if (err instanceof ApiError) {
        if (err.status === 403) {
          error = "You do not have permission to view this lead.";
        } else if (err.status === 404) {
          error = "Lead not found.";
        } else {
          error = "Could not load lead details.";
          toast.error("Error", "Could not load lead details");
        }
      } else {
        error = "Could not load lead details.";
        toast.error("Error", "Could not load lead details");
      }
    } finally {
      loading = false;
    }
  }

  function closeModal() {
    onClose?.();
  }

  $effect(() => {
    if (!open) {
      loading = false;
      error = "";
      leadDetail = null;
      loadedLeadId = null;
      activeTab = "overview";
      return;
    }
    if (!leadId) return;
    if (loadedLeadId === leadId && leadDetail) return;
    activeTab = "overview";
    void fetchLeadDetail(leadId);
  });
</script>

{#if open}
  <button
    class="fixed inset-0 bg-black/50 backdrop-blur-sm cursor-default"
    style={`z-index: ${backdropZ};`}
    onclick={closeModal}
    tabindex="-1"
    aria-label="Close lead details"
  ></button>

  <div class="fixed inset-0 flex items-center justify-center p-4 sm:p-6" style={`z-index: ${panelZ};`}>
    <div class="h-[92vh] w-full max-w-6xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl">
      <div class="flex h-full flex-col">
        <div class="flex items-start justify-between gap-4 border-b border-neutral-100 px-6 py-4">
          <div class="min-w-0">
            <h2 class="truncate text-xl font-semibold text-neutral-900">
              {leadDetail?.full_name || "Lead Details"}
            </h2>
            {#if leadDetail}
              <div class="mt-2 flex items-center gap-2">
                <StatusBadge status={leadDetail.status} label={leadDetail.status_display} />
                <StatusBadge status={leadDetail.pipeline_stage} label={leadDetail.pipeline_stage_display} />
              </div>
            {/if}
          </div>
          <button
            onclick={closeModal}
            class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            aria-label="Close"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-5">
          {#if loading}
            <div class="space-y-4 animate-pulse">
              <div class="h-16 rounded-lg bg-neutral-100"></div>
              <div class="h-12 rounded-lg bg-neutral-100"></div>
              <div class="h-48 rounded-lg bg-neutral-100"></div>
              <div class="h-48 rounded-lg bg-neutral-100"></div>
            </div>
          {:else if error || !leadDetail}
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-5">
              <p class="text-sm text-neutral-600">{error || "Could not load lead details."}</p>
            </div>
          {:else}
            <div class="space-y-5">
              <div class="rounded-xl border border-neutral-200 bg-white p-5">
                <div class="flex items-center">
                  {#each pipelineStages as stage, i}
                    {@const isCompleted = i <= leadCurrentStageIndex}
                    {@const isCurrent = i === leadCurrentStageIndex}
                    {@const stageDate = leadDetail[leadStageDateKeys[stage.key]] as string | null}

                    {#if i > 0}
                      <div class="h-0.5 flex-1 transition-colors {i <= leadCurrentStageIndex ? 'bg-neutral-900' : 'bg-neutral-200'}"></div>
                    {/if}

                    <div class="relative flex flex-col items-center">
                      <div
                        class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors
                        {isCompleted ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-400'}
                        {isCurrent ? 'ring-2 ring-neutral-900 ring-offset-2' : ''}"
                      >
                        {#if isCompleted && !isCurrent}
                          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                          </svg>
                        {:else}
                          {i + 1}
                        {/if}
                      </div>
                      <span class="mt-1.5 whitespace-nowrap text-[10px] font-medium {isCompleted ? 'text-neutral-900' : 'text-neutral-400'}">
                        {stage.label}
                      </span>
                      {#if stageDate}
                        <span class="mt-0.5 whitespace-nowrap text-[9px] text-neutral-400">
                          {formatLeadDate(stageDate)}
                        </span>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>

              <div class="border-b border-neutral-200">
                <nav class="flex gap-6">
                  {#each tabs as tab}
                    <button
                      type="button"
                      onclick={() => (activeTab = tab.key)}
                      class="pb-3 text-sm font-medium border-b-2 transition-colors
                      {activeTab === tab.key
                        ? 'border-neutral-900 text-neutral-900'
                        : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
                    >
                      {tab.label}
                    </button>
                  {/each}
                </nav>
              </div>

              {#if activeTab === "overview"}
                <div class="grid gap-5 md:grid-cols-2">
                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Contact Information</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Email</span><span class="text-right text-neutral-900">{leadDetail.email || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Phone</span><span class="text-right text-neutral-900">{leadDetail.phone || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Secondary Phone</span><span class="text-right text-neutral-900">{leadDetail.secondary_phone || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Company</span><span class="text-right text-neutral-900">{leadDetail.company || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Nationality</span><span class="text-right text-neutral-900">{leadDetail.nationality || "\u2014"}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Lead Details</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Lead Type</span><span class="text-right text-neutral-900">{leadTypeLabels[leadDetail.lead_type]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Priority</span><span class="text-right text-neutral-900">{leadPriorityLabels[leadDetail.priority]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Score</span><span class="text-right tabular-nums text-neutral-900">{leadDetail.score}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Source</span><span class="text-right text-neutral-900">{leadDetail.source_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Broker</span><span class="text-right text-neutral-900">{leadDetail.broker_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Referral</span><span class="text-right text-neutral-900">{leadDetail.referral_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Assigned To</span><span class="text-right text-neutral-900">{leadDetail.assigned_to_name || "\u2014"}</span></div>
                    </div>
                    <div class="space-y-1">
                      <p class="text-xs text-neutral-400">Tags</p>
                      {#if leadDetail.tags.length > 0}
                        <div class="flex flex-wrap gap-1.5">
                          {#each leadDetail.tags as tag}
                            <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-700">
                              {tag}
                            </span>
                          {/each}
                        </div>
                      {:else}
                        <p class="text-sm text-neutral-900">\u2014</p>
                      {/if}
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Budget & Payment</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Budget Min</span><span class="text-right tabular-nums text-neutral-900">{formatLeadAmount(leadDetail.budget_min)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Budget Max</span><span class="text-right tabular-nums text-neutral-900">{formatLeadAmount(leadDetail.budget_max)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Payment Capability</span><span class="text-right text-neutral-900">{leadPaymentCapabilityLabels[leadDetail.payment_capability]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Preferred Locations</span><span class="text-right text-neutral-900">{leadDetail.preferred_locations.join(", ") || "\u2014"}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Key Dates</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Inquiry Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.inquiry_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Qualified Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.qualified_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Site Visit Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.site_visit_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Offer Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.offer_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Reservation Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.reservation_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">SPA Issued Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.spa_issued_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Closed Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.closed_date)}</span></div>
                      <div class="flex justify-between gap-4 border-t border-neutral-100 pt-2.5"><span class="font-medium text-neutral-500">Days in Pipeline</span><span class="text-right font-semibold tabular-nums text-neutral-900">{leadDetail.days_in_pipeline}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5 md:col-span-2">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Notes</h3>
                    <p class="whitespace-pre-line text-sm text-neutral-600">
                      {leadDetail.notes || "No notes recorded."}
                    </p>
                    {#if leadDetail.status === "lost" && leadDetail.lost_reason}
                      <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                        <p class="text-xs text-neutral-400">Lost Reason</p>
                        <p class="mt-1 whitespace-pre-line text-sm text-neutral-700">{leadDetail.lost_reason}</p>
                      </div>
                    {/if}
                    {#if leadDetail.converted_customer_name}
                      <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                        <p class="text-xs text-neutral-400">Converted Customer</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{leadDetail.converted_customer_name}</p>
                      </div>
                    {/if}
                  </section>
                </div>
              {/if}

              {#if activeTab === "activities"}
                {#if sortedLeadActivities.length === 0}
                  <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
                    <p class="text-sm text-neutral-400">No activities recorded yet.</p>
                  </div>
                {:else}
                  <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
                    {#each sortedLeadActivities as activity}
                      <div class="p-5">
                        <div class="flex items-start justify-between gap-4">
                          <div class="min-w-0">
                            <div class="flex items-center gap-2">
                              <p class="text-sm font-medium text-neutral-900">{activity.subject}</p>
                              <span class="inline-flex items-center rounded bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                                {activity.activity_type_display}
                              </span>
                              {#if activity.is_completed}
                                <span class="inline-flex items-center rounded bg-neutral-900 px-2 py-0.5 text-[10px] font-medium text-white">
                                  Completed
                                </span>
                              {/if}
                            </div>
                            {#if activity.description}
                              <p class="mt-1 whitespace-pre-line text-sm text-neutral-500">{activity.description}</p>
                            {/if}
                            <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-400">
                              {#if activity.scheduled_at}
                                <span>Scheduled: {formatLeadDateTime(activity.scheduled_at)}</span>
                              {/if}
                              {#if activity.completed_at}
                                <span>Completed: {formatLeadDateTime(activity.completed_at)}</span>
                              {/if}
                              {#if activity.performed_by_name}
                                <span>By: {activity.performed_by_name}</span>
                              {/if}
                              <span>Logged: {formatLeadDateTime(activity.created_at)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                {/if}
              {/if}

              {#if activeTab === "preferences"}
                <div class="space-y-5">
                  <section class="rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-neutral-900">Project Interests</h3>
                    {#if leadDetail.project_interests.length === 0}
                      <p class="text-sm text-neutral-400">No project interests recorded.</p>
                    {:else}
                      <div class="space-y-3">
                        {#each leadDetail.project_interests as interest}
                          <div class="rounded-lg border border-neutral-100 p-3">
                            <div class="flex items-center gap-2">
                              <p class="text-sm font-medium text-neutral-900">{interest.project_name}</p>
                              <span class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium
                                {interest.interest_level === 'high' ? 'bg-neutral-900 text-white' :
                                  interest.interest_level === 'medium' ? 'bg-neutral-200 text-neutral-700' :
                                  'bg-neutral-100 text-neutral-500'}"
                              >
                                {interest.interest_level}
                              </span>
                            </div>
                            {#if interest.notes}
                              <p class="mt-1 text-xs text-neutral-500">{interest.notes}</p>
                            {/if}
                            <p class="mt-1 text-xs text-neutral-400">Added {formatLeadDate(interest.created_at?.slice(0, 10))}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </section>

                  <section class="rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-neutral-900">Unit Preferences</h3>
                    {#if leadDetail.unit_preferences.length === 0}
                      <p class="text-sm text-neutral-400">No unit preferences recorded.</p>
                    {:else}
                      <div class="space-y-3">
                        {#each leadDetail.unit_preferences as pref}
                          <div class="rounded-lg border border-neutral-100 p-3">
                            <p class="text-sm font-medium text-neutral-900">{pref.unit_type_display || pref.unit_type}</p>
                            <div class="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                              {#if pref.min_bedrooms != null || pref.max_bedrooms != null}
                                <p><span class="text-neutral-400">Bedrooms:</span> <span class="text-neutral-700">{pref.min_bedrooms ?? "?"} - {pref.max_bedrooms ?? "?"}</span></p>
                              {/if}
                              {#if pref.min_area_sqft || pref.max_area_sqft}
                                <p><span class="text-neutral-400">Area:</span> <span class="text-neutral-700">{pref.min_area_sqft ?? "?"} - {pref.max_area_sqft ?? "?"} sqft</span></p>
                              {/if}
                              {#if pref.floor_preference}
                                <p><span class="text-neutral-400">Floor:</span> <span class="text-neutral-700">{pref.floor_preference}</span></p>
                              {/if}
                              {#if pref.view_preference}
                                <p><span class="text-neutral-400">View:</span> <span class="text-neutral-700">{pref.view_preference}</span></p>
                              {/if}
                            </div>
                            {#if pref.notes}
                              <p class="mt-2 text-xs text-neutral-500">{pref.notes}</p>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </section>
                </div>
              {/if}

              {#if activeTab === "timeline"}
                {#if sortedLeadTransitions.length === 0}
                  <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
                    <p class="text-sm text-neutral-400">No stage transitions recorded.</p>
                  </div>
                {:else}
                  <div class="relative">
                    <div class="absolute bottom-3 left-[17px] top-3 w-px bg-neutral-200"></div>
                    <div class="space-y-0">
                      {#each sortedLeadTransitions as transition, i}
                        <div class="relative flex gap-4 pb-6">
                          <div class="relative z-10 shrink-0">
                            <div class="flex h-[35px] w-[35px] items-center justify-center rounded-full border-2 border-neutral-300 bg-white {i === 0 ? 'border-neutral-900' : ''}">
                              <svg class="h-4 w-4 {i === 0 ? 'text-neutral-900' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                              </svg>
                            </div>
                          </div>
                          <div class="min-w-0 flex-1 rounded-xl border border-neutral-200 bg-white p-4">
                            <div class="flex flex-wrap items-center gap-2">
                              <StatusBadge status={transition.from_stage} label={leadStageLabel(transition.from_stage)} />
                              <svg class="h-3.5 w-3.5 shrink-0 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                              </svg>
                              <StatusBadge status={transition.to_stage} label={leadStageLabel(transition.to_stage)} />
                            </div>
                            <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-400">
                              {#if transition.transitioned_by_name}
                                <span>By {transition.transitioned_by_name}</span>
                              {/if}
                              <span>{formatLeadDateTime(transition.transitioned_at)}</span>
                            </div>
                            {#if transition.notes}
                              <p class="mt-2 whitespace-pre-line text-xs text-neutral-500">{transition.notes}</p>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(e) => {
    if (!open || e.key !== "Escape") return;
    closeModal();
  }}
/>
