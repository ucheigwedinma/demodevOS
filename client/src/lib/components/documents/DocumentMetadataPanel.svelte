<script lang="ts">
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { DocumentRecord } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let {
    document,
  }: {
    document: DocumentRecord;
  } = $props();

  const confidentialityLabels: Record<string, string> = {
    public: "Public",
    internal: "Internal",
    confidential: "Confidential",
    restricted: "Restricted",
  };

  function fmtCurrency(value: string): string {
    return currency.format(value);
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Metadata Panel</h3>
  <div class="grid md:grid-cols-2 gap-x-10 gap-y-3 text-sm">
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Document Number</span><span class="text-neutral-900 font-medium">{document.document_number}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Status</span><StatusBadge status={document.status} size="sm" /></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Title</span><span class="text-neutral-900 max-w-[60%] text-right">{document.title}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Type</span><span class="text-neutral-900">{document.document_type_name}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Category</span><span class="text-neutral-900">{document.category}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Phase</span><span class="text-neutral-900">{document.phase_name}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Confidentiality</span><span class="text-neutral-900">{confidentialityLabels[document.confidentiality_level] ?? document.confidentiality_level}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Contract Value</span><span class="text-neutral-900 tabular-nums">{fmtCurrency(document.contract_value)}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Project Risk</span><span class="text-neutral-900 capitalize">{document.project_risk_rating ?? "n/a"}</span></div>
    <div class="flex justify-between gap-5"><span class="text-neutral-400">Created</span><span class="text-neutral-900">{fmtDate(document.created_at)}</span></div>
  </div>
</div>
