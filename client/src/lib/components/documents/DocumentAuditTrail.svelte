<script lang="ts">
  export type AuditEvent = {
    id: string | number;
    timestamp: string;
    event_type: string;
    actor: string;
    actor_role?: string | null;
    ip_address?: string | null;
    summary: string;
  };

  let {
    events,
  }: {
    events: AuditEvent[];
  } = $props();

  const eventLabel: Record<string, string> = {
    document_created: "Document Created",
    metadata_changed: "Metadata Changed",
    version_uploaded: "Version Uploaded",
    document_generated: "Document Generated",
    approval_decision: "Approval Decision",
    workflow_submitted: "Workflow Submitted",
    workflow_step_decision: "Workflow Step Decision",
    comment_added: "Comment Added",
    document_downloaded: "Download",
    document_shared: "Share",
    signature_request_sent: "Signature Request Sent",
    signature_completed: "Signature Completed",
    signature_cancelled: "Signature Cancelled",
    document_archived: "Archived",
    document_superseded: "Superseded",
    document_deleted: "Deleted",
  };

  const eventColors: Record<string, string> = {
    document_created: "bg-teal-50 text-teal-700",
    metadata_changed: "bg-amber-50 text-amber-700",
    version_uploaded: "bg-blue-50 text-blue-700",
    document_generated: "bg-cyan-50 text-cyan-700",
    approval_decision: "bg-emerald-50 text-emerald-700",
    workflow_submitted: "bg-violet-50 text-violet-700",
    workflow_step_decision: "bg-fuchsia-50 text-fuchsia-700",
    comment_added: "bg-neutral-100 text-neutral-700",
    document_downloaded: "bg-sky-50 text-sky-700",
    document_shared: "bg-indigo-50 text-indigo-700",
    signature_request_sent: "bg-indigo-50 text-indigo-700",
    signature_completed: "bg-emerald-50 text-emerald-700",
    signature_cancelled: "bg-orange-100 text-orange-800",
    document_archived: "bg-zinc-200 text-zinc-800",
    document_superseded: "bg-orange-100 text-orange-800",
    document_deleted: "bg-red-100 text-red-800",
  };

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Audit Trail</h3>
  {#if events.length === 0}
    <p class="text-sm text-neutral-400">No audit events available yet.</p>
  {:else}
    <div class="space-y-3 max-h-[460px] overflow-y-auto pr-1">
      {#each events as event}
        <div class="rounded-lg border border-neutral-200 px-4 py-3">
          <div class="flex items-center justify-between gap-4">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {eventColors[event.event_type] ?? 'bg-neutral-100 text-neutral-700'}">
              {eventLabel[event.event_type] ?? event.event_type}
            </span>
            <span class="text-xs text-neutral-400">{fmtDate(event.timestamp)}</span>
          </div>
          <p class="mt-2 text-sm text-neutral-900">{event.summary}</p>
          <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500">
            <span>By {event.actor}</span>
            {#if event.actor_role}
              <span>Role: {event.actor_role}</span>
            {/if}
            {#if event.ip_address}
              <span>IP: {event.ip_address}</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
