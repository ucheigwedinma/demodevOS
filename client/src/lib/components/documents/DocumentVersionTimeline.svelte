<script lang="ts">
  import type { DocumentVersionRecord } from "$lib/types";

  let {
    versions,
  }: {
    versions: DocumentVersionRecord[];
  } = $props();

  const approvalLabels: Record<string, string> = {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
  };

  const approvalColors: Record<string, string> = {
    pending: "bg-amber-50 text-amber-700",
    approved: "bg-emerald-50 text-emerald-700",
    rejected: "bg-red-50 text-red-700",
  };

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Version Timeline</h3>
  {#if versions.length === 0}
    <p class="text-sm text-neutral-400">No versions uploaded yet.</p>
  {:else}
    <div class="space-y-4">
      {#each versions as version, i}
        <div class="flex gap-4">
          <div class="pt-1 flex flex-col items-center">
            <span class="w-2.5 h-2.5 rounded-full bg-neutral-900"></span>
            {#if i < versions.length - 1}
              <span class="w-px flex-1 bg-neutral-200 mt-1"></span>
            {/if}
          </div>
          <div class="pb-4 flex-1">
            <div class="flex items-center justify-between gap-4">
              <p class="text-sm font-medium text-neutral-900">v{version.version_major}.{version.version_minor}</p>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {approvalColors[version.approval_status] ?? 'bg-neutral-100 text-neutral-600'}">
                {approvalLabels[version.approval_status] ?? version.approval_status}
              </span>
            </div>
            <p class="mt-1 text-xs text-neutral-500">
              Uploaded {fmtDate(version.uploaded_at)}
              {#if version.uploaded_by_name}
                by {version.uploaded_by_name}
              {/if}
            </p>
            {#if version.change_summary}
              <p class="mt-2 text-sm text-neutral-600">{version.change_summary}</p>
            {/if}
            <p class="mt-2 text-xs text-neutral-400 break-all">{version.file_path}</p>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
