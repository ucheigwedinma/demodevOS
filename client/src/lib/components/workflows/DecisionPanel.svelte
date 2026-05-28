<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { WorkflowInstanceDetail, WorkflowStepRecord } from "$lib/types";

  interface Props {
    instance: WorkflowInstanceDetail;
    onDecision: () => void;
  }

  let { instance, onDecision }: Props = $props();

  let comments = $state("");
  let submitting = $state(false);

  let pendingStep = $derived<WorkflowStepRecord | undefined>(
    instance.steps.find((s) => s.decision === "pending"),
  );

  async function decide(decision: "approved" | "rejected") {
    if (!pendingStep) return;
    submitting = true;
    try {
      await api.post(`/workflows/instances/${instance.id}/decide/`, {
        step_id: pendingStep.id,
        decision,
        comments,
      });
      toast.success(
        decision === "approved" ? "Approved" : "Rejected",
        `Step "${pendingStep.name}" has been ${decision}.`,
      );
      comments = "";
      onDecision();
    } catch {
      toast.error("Error", `Could not record decision.`);
    } finally {
      submitting = false;
    }
  }
</script>

{#if pendingStep && (instance.state === "pending" || instance.state === "in_progress")}
  <div class="bg-white rounded-xl border border-neutral-200 p-6">
    <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-1">
      Pending Decision
    </h3>
    <p class="text-xs text-neutral-400 mb-4">
      Step {pendingStep.sequence}: {pendingStep.name}
    </p>

    <textarea
      bind:value={comments}
      rows={2}
      placeholder="Add comments (optional)..."
      class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none mb-4
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    ></textarea>

    <div class="flex gap-3">
      <button
        type="button"
        onclick={() => decide("approved")}
        disabled={submitting}
        class="flex-1 px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium
               hover:bg-emerald-700 disabled:opacity-50 transition-colors"
      >
        {submitting ? "Saving..." : "Approve"}
      </button>
      <button
        type="button"
        onclick={() => decide("rejected")}
        disabled={submitting}
        class="flex-1 px-4 py-2.5 border border-red-200 text-red-600 rounded-lg text-sm font-medium
               hover:bg-red-50 disabled:opacity-50 transition-colors"
      >
        {submitting ? "Saving..." : "Reject"}
      </button>
    </div>
  </div>
{/if}
