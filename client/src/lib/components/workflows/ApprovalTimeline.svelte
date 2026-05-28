<script lang="ts">
  import type { WorkflowStepRecord } from "$lib/types";

  interface Props {
    steps: WorkflowStepRecord[];
  }

  let { steps }: Props = $props();

  const DECISION_STYLES: Record<string, { dot: string; line: string }> = {
    approved: { dot: "bg-emerald-500", line: "bg-emerald-200" },
    rejected: { dot: "bg-red-500", line: "bg-red-200" },
    pending: { dot: "bg-neutral-300", line: "bg-neutral-200" },
    skipped: { dot: "bg-neutral-200", line: "bg-neutral-100" },
    escalated: { dot: "bg-orange-500", line: "bg-orange-200" },
  };

  const DECISION_LABELS: Record<string, string> = {
    approved: "Approved",
    rejected: "Rejected",
    pending: "Pending",
    skipped: "Skipped",
    escalated: "Escalated",
  };

  function formatDateTime(d: string | null) {
    if (!d) return "";
    return new Date(d).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="space-y-0">
  {#each steps as step, i}
    {@const style = DECISION_STYLES[step.decision] || DECISION_STYLES.pending}
    <div class="flex gap-3">
      <!-- Timeline line + dot -->
      <div class="flex flex-col items-center">
        <div class="w-3 h-3 rounded-full shrink-0 {style.dot}"></div>
        {#if i < steps.length - 1}
          <div class="w-0.5 flex-1 min-h-[32px] {style.line}"></div>
        {/if}
      </div>

      <!-- Content -->
      <div class="pb-4 -mt-0.5 flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="text-sm font-medium text-neutral-900">{step.name}</p>
          <span class="text-[10px] uppercase font-semibold tracking-wider {step.decision === 'approved' ? 'text-emerald-600' : step.decision === 'rejected' ? 'text-red-600' : step.decision === 'escalated' ? 'text-orange-600' : 'text-neutral-400'}">
            {DECISION_LABELS[step.decision]}
          </span>
          {#if step.execution_mode === "parallel"}
            <span class="text-[10px] text-neutral-400 font-medium bg-neutral-50 px-1.5 py-0.5 rounded">Parallel</span>
          {/if}
        </div>
        <div class="flex items-center gap-2 mt-0.5 text-xs text-neutral-400">
          {#if step.decided_by_name}
            <span>{step.decided_by_name}</span>
            {#if step.on_behalf_of_name}
              <span class="italic">(on behalf of {step.on_behalf_of_name})</span>
            {/if}
          {:else if step.approver_role_slug}
            <span class="capitalize">{step.approver_role_slug.replace(/-/g, " ")}</span>
          {/if}
          {#if step.decided_at}
            <span>· {formatDateTime(step.decided_at)}</span>
          {/if}
          {#if step.sla_breached}
            <span class="text-orange-500 font-semibold">SLA Breached</span>
          {/if}
        </div>
        {#if step.comments}
          <p class="mt-1 text-xs text-neutral-500 italic">"{step.comments}"</p>
        {/if}
      </div>
    </div>
  {/each}
</div>
