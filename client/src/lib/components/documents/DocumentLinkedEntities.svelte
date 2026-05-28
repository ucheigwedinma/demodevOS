<script lang="ts">
  import type { DocumentRecord } from "$lib/types";

  let {
    document,
  }: {
    document: DocumentRecord;
  } = $props();

  const rows = $derived.by(() => [
    { label: "Project", value: document.project_name, href: document.project ? `/projects/${document.project}` : null },
    { label: "Land", value: document.land_name, href: document.land ? `/properties/${document.land}` : null },
    { label: "Unit", value: document.unit_number, href: document.unit ? `/units/${document.unit}` : null },
    { label: "Vendor", value: document.vendor_name, href: document.vendor ? `/procurement/vendors/${document.vendor}` : null },
    { label: "Client", value: document.client_name, href: null },
    { label: "Division", value: document.business_unit_division_name, href: null },
    { label: "Department", value: document.business_unit_department_name, href: null },
  ]);
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Linked Entities</h3>
  <div class="space-y-3 text-sm">
    {#each rows as row}
      <div class="flex items-center justify-between gap-5">
        <span class="text-neutral-400">{row.label}</span>
        {#if row.value && row.href}
          <a href={row.href} class="text-neutral-900 hover:underline text-right">{row.value}</a>
        {:else if row.value}
          <span class="text-neutral-900 text-right">{row.value}</span>
        {:else}
          <span class="text-neutral-300">--</span>
        {/if}
      </div>
    {/each}
  </div>
</div>
