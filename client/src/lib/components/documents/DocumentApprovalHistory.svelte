<script lang="ts">
  import type { DocumentApprovalRecord } from "$lib/types";

  let {
    approvals,
  }: {
    approvals: DocumentApprovalRecord[];
  } = $props();

  const decisionColors: Record<string, string> = {
    approved: "bg-emerald-50 text-emerald-700",
    rejected: "bg-red-50 text-red-700",
  };

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Approval History</h3>
  {#if approvals.length === 0}
    <p class="text-sm text-neutral-400">No approval decisions recorded yet.</p>
  {:else}
    <div class="space-y-3">
      {#each approvals as approval}
        <div class="rounded-lg border border-neutral-200 px-4 py-3">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="text-sm font-medium text-neutral-900">{approval.user_name || "Unknown user"}</p>
              <p class="text-xs text-neutral-500 mt-0.5">{approval.role_name} · {approval.document_version_label}</p>
            </div>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {decisionColors[approval.decision] ?? 'bg-neutral-100 text-neutral-600'}">
              {approval.decision}
            </span>
          </div>
          {#if approval.comments}
            <p class="mt-2 text-sm text-neutral-600">{approval.comments}</p>
          {/if}
          <p class="mt-2 text-xs text-neutral-400">{fmtDate(approval.timestamp)}</p>
        </div>
      {/each}
    </div>
  {/if}
</div>
