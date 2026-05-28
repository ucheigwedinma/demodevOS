<script lang="ts">
  import type { ColumnDef } from "./types";
  import StatusBadge from "$lib/components/ui/StatusBadge.svelte";

  let {
    column,
    value,
    row,
  }: {
    column: ColumnDef;
    value: unknown;
    row: Record<string, unknown>;
  } = $props();

  function formatDate(v: unknown): string {
    if (!v) return "-";
    try {
      return new Date(v as string).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return String(v);
    }
  }

  function formatDatetime(v: unknown): string {
    if (!v) return "-";
    try {
      return new Date(v as string).toLocaleString("en-US", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
    } catch {
      return String(v);
    }
  }

  function formatCurrency(v: unknown): string {
    if (v == null) return "-";
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
</script>

{#if column.type === "badge" && value}
  <StatusBadge status={String(value)} />
{:else if column.type === "boolean"}
  <span class="text-sm {value ? 'text-emerald-600' : 'text-neutral-400'}">{value ? "Yes" : "No"}</span>
{:else if column.type === "date"}
  <span class="text-sm text-neutral-600">{formatDate(value)}</span>
{:else if column.type === "datetime"}
  <span class="text-sm text-neutral-600">{formatDatetime(value)}</span>
{:else if column.type === "currency"}
  <span class="text-sm text-neutral-900 tabular-nums">{formatCurrency(value)}</span>
{:else if column.type === "number"}
  <span class="text-sm text-neutral-900 tabular-nums">{value ?? "-"}</span>
{:else}
  <span class="text-sm text-neutral-900">{value ?? "-"}</span>
{/if}
