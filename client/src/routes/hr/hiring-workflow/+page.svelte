<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { HiringWorkflowItem, HiringWorkflowStep } from "$lib/types";

  interface HiringWorkflowResponse {
    items: HiringWorkflowItem[];
    by_state: Record<string, HiringWorkflowItem[]>;
    counts: Record<string, number>;
  }

  let loading = $state(true);
  let items = $state<HiringWorkflowItem[]>([]);
  let counts = $state<Record<string, number>>({});

  let filterState = $state("all");

  const stateLabels: Record<string, string> = {
    draft: "Draft",
    pending: "Pending",
    in_progress: "In Progress",
    approved: "Approved",
    rejected: "Rejected",
    cancelled: "Cancelled",
    escalated: "Escalated",
  };

  const stateBadgeClasses: Record<string, string> = {
    pending: "bg-neutral-200 text-neutral-700",
    in_progress: "bg-neutral-400 text-white",
    approved: "bg-neutral-900 text-white",
    rejected: "bg-neutral-200 text-neutral-400",
    cancelled: "bg-neutral-100 text-neutral-400",
    escalated: "bg-neutral-600 text-white",
    draft: "bg-neutral-100 text-neutral-500",
  };

  const decisionBadgeClasses: Record<string, string> = {
    pending: "bg-neutral-200 text-neutral-600",
    approved: "bg-neutral-900 text-white",
    rejected: "bg-neutral-300 text-neutral-700",
  };

  const objectTypeBadge: Record<string, string> = {
    requisition: "Requisition",
    offer: "Offer",
  };

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatDateTime(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function fetchWorkflows() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (filterState !== "all") params.state = filterState;
      const res = await api.get<HiringWorkflowResponse>("/hr/hiring-workflow/", params);
      items = res.items;
      counts = res.counts;
    } catch {
      items = [];
      counts = {};
      toast.error("Load failed", "Could not load hiring workflows.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchWorkflows();
  });

  let filteredItems = $derived(
    filterState === "all"
      ? items
      : items.filter((item) => item.state === filterState)
  );

  let statCards = $derived([
    { label: "Pending", key: "pending", count: counts["pending"] ?? 0 },
    { label: "In Progress", key: "in_progress", count: counts["in_progress"] ?? 0 },
    { label: "Approved", key: "approved", count: counts["approved"] ?? 0 },
    { label: "Rejected", key: "rejected", count: counts["rejected"] ?? 0 },
  ]);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Hiring Workflow</h1>
      <p class="text-sm text-neutral-500 mt-1">
        Approval pipeline for requisitions and offers
      </p>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div
        class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"
      ></div>
    </div>
  {:else}
    <!-- Summary stats -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {#each statCards as card}
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p
            class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider"
          >
            {card.label}
          </p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">
            {card.count}
          </p>
        </div>
      {/each}
    </div>

    <!-- Filter -->
    <div class="flex items-center gap-3">
      <label
        for="state-filter"
        class="text-sm font-medium text-neutral-600"
      >
        State
      </label>
      <select
        id="state-filter"
        bind:value={filterState}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900"
      >
        <option value="all">All</option>
        <option value="pending">Pending</option>
        <option value="in_progress">In Progress</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="cancelled">Cancelled</option>
        <option value="escalated">Escalated</option>
      </select>
    </div>

    <!-- Workflow cards -->
    {#if filteredItems.length === 0}
      <div class="rounded-xl border border-neutral-200 bg-white px-6 py-16 text-center">
        <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-100">
          <svg
            class="h-6 w-6 text-neutral-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <p class="text-sm font-medium text-neutral-900">No workflows found</p>
        <p class="mt-1 text-sm text-neutral-500">
          There are no hiring workflow items matching your current filter.
        </p>
      </div>
    {:else}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {#each filteredItems as item (item.id)}
          <div
            class="rounded-xl border border-neutral-200 bg-white overflow-hidden"
          >
            <!-- Card header -->
            <div class="px-5 py-4 border-b border-neutral-100">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span
                      class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider border border-neutral-200 bg-neutral-50 text-neutral-600"
                    >
                      {objectTypeBadge[item.object_type] ?? item.object_type}
                    </span>
                    <span
                      class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold {stateBadgeClasses[item.state] ?? 'bg-neutral-100 text-neutral-500'}"
                    >
                      {stateLabels[item.state] ?? item.state}
                    </span>
                  </div>
                  <h3
                    class="mt-2 text-sm font-semibold text-neutral-900 leading-snug"
                  >
                    {item.object_label}
                  </h3>
                </div>
              </div>
              <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
                <span>
                  Template:
                  <span class="font-medium text-neutral-700">
                    {item.template_name}
                  </span>
                </span>
                {#if item.submitted_by_name}
                  <span>
                    Submitted by:
                    <span class="font-medium text-neutral-700">
                      {item.submitted_by_name}
                    </span>
                  </span>
                {/if}
                {#if item.submitted_at}
                  <span>
                    Submitted:
                    <span class="font-medium text-neutral-700">
                      {formatDate(item.submitted_at)}
                    </span>
                  </span>
                {/if}
              </div>
            </div>

            <!-- Steps timeline -->
            {#if item.steps.length > 0}
              <div class="px-5 py-4">
                <p
                  class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-3"
                >
                  Approval Steps
                </p>
                <div class="space-y-0">
                  {#each item.steps as step, stepIndex (step.id)}
                    <div class="relative flex gap-3">
                      <!-- Vertical connector line -->
                      <div class="flex flex-col items-center">
                        <div
                          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold
                            {step.decision === 'approved'
                              ? 'border-neutral-900 bg-neutral-900 text-white'
                              : step.decision === 'rejected'
                                ? 'border-neutral-300 bg-neutral-300 text-white'
                                : 'border-neutral-200 bg-white text-neutral-400'}"
                        >
                          {step.sequence}
                        </div>
                        {#if stepIndex < item.steps.length - 1}
                          <div
                            class="w-px flex-1 min-h-4 bg-neutral-200"
                          ></div>
                        {/if}
                      </div>

                      <!-- Step content -->
                      <div class="pb-4 min-w-0 flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                          <span
                            class="text-sm font-medium text-neutral-800"
                          >
                            {step.name}
                          </span>
                          <span
                            class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold {decisionBadgeClasses[step.decision] ?? 'bg-neutral-100 text-neutral-500'}"
                          >
                            {stateLabels[step.decision] ?? step.decision}
                          </span>
                        </div>
                        <div
                          class="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-neutral-500"
                        >
                          {#if step.decided_by_name}
                            <span>
                              {step.decided_by_name}
                            </span>
                          {/if}
                          {#if step.decided_at}
                            <span>
                              {formatDateTime(step.decided_at)}
                            </span>
                          {/if}
                        </div>
                        {#if step.comments}
                          <p
                            class="mt-1 text-xs text-neutral-500 italic leading-relaxed"
                          >
                            "{step.comments}"
                          </p>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {:else}
              <div class="px-5 py-4">
                <p class="text-xs text-neutral-400 italic">
                  No approval steps defined.
                </p>
              </div>
            {/if}

            <!-- Completed at footer -->
            {#if item.completed_at}
              <div
                class="px-5 py-3 border-t border-neutral-100 bg-neutral-50"
              >
                <p class="text-xs text-neutral-500">
                  Completed:
                  <span class="font-medium text-neutral-700">
                    {formatDateTime(item.completed_at)}
                  </span>
                </p>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>
