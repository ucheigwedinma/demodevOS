<script lang="ts">
  import type { ColumnDef } from "./types";
  import { exportCSV, exportXLSX, exportPDF } from "./export";
  import { toast } from "$lib/stores/toast.svelte";

  let {
    columns,
    data,
    resourceLabel,
  }: {
    columns: ColumnDef[];
    data: Record<string, unknown>[];
    resourceLabel: string;
  } = $props();

  let open = $state(false);
  let exporting = $state(false);

  function close() {
    open = false;
  }

  async function handleExport(format: "csv" | "xlsx" | "pdf") {
    close();
    exporting = true;
    try {
      if (format === "csv") {
        exportCSV(columns, data, resourceLabel);
      } else if (format === "xlsx") {
        await exportXLSX(columns, data, resourceLabel);
      } else {
        await exportPDF(columns, data, resourceLabel);
      }
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (e) {
      console.error("Export failed:", e);
      toast.error("Export failed", "Could not generate the file.");
    } finally {
      exporting = false;
    }
  }
</script>

<svelte:window onclick={close} />

<div class="relative">
  <button
    onclick={(e) => { e.stopPropagation(); open = !open; }}
    disabled={data.length === 0 || exporting}
    class="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors
           {data.length === 0 || exporting
             ? 'border-neutral-100 text-neutral-300 cursor-not-allowed'
             : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300'}"
    title="Export"
  >
    {#if exporting}
      <div class="w-4 h-4 border-2 border-neutral-300 border-t-neutral-700 rounded-full animate-spin"></div>
    {:else}
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
    {/if}
    Export
  </button>

  {#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div
      class="absolute right-0 top-full mt-1 w-44 bg-white rounded-lg border border-neutral-200 shadow-lg py-1 z-20"
      onclick={(e) => e.stopPropagation()}
    >
      <button
        onclick={() => handleExport("csv")}
        class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left"
      >
        <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        CSV
      </button>
      <button
        onclick={() => handleExport("xlsx")}
        class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left"
      >
        <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 15.75h7.5" />
        </svg>
        Excel (.xlsx)
      </button>
      <button
        onclick={() => handleExport("pdf")}
        class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left"
      >
        <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        PDF
      </button>
    </div>
  {/if}
</div>
