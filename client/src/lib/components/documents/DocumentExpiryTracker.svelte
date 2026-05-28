<script lang="ts">
  import type { DocumentExpiryRecord } from "$lib/types";

  let {
    expiry,
  }: {
    expiry: DocumentExpiryRecord | null;
  } = $props();

  const triggerLabel: Record<string, string> = {
    building_permit: "Building Permit",
    insurance: "Insurance",
    performance_bond: "Performance Bond",
    eia_renewal: "EIA Renewal",
    warranty_end: "Warranty End",
  };

  function fmtDate(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function daysToExpiry(value: string): number {
    const date = new Date(value);
    const now = new Date();
    return Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Expiry Tracker</h3>
  {#if !expiry}
    <p class="text-sm text-neutral-400">No expiry profile is configured for this document.</p>
  {:else}
    {@const days = daysToExpiry(expiry.expiry_date)}
    <div class="space-y-3 text-sm">
      <div class="flex justify-between"><span class="text-neutral-400">Trigger</span><span class="text-neutral-900">{triggerLabel[expiry.trigger_category] ?? expiry.trigger_category}</span></div>
      <div class="flex justify-between"><span class="text-neutral-400">Expiry Date</span><span class="text-neutral-900">{fmtDate(expiry.expiry_date)}</span></div>
      <div class="flex justify-between"><span class="text-neutral-400">Days Remaining</span><span class="font-medium {days < 0 ? 'text-red-600' : days <= 30 ? 'text-amber-600' : 'text-neutral-900'}">{days < 0 ? `${Math.abs(days)} overdue` : `${days} days`}</span></div>
      <div class="pt-2 border-t border-neutral-100 space-y-2">
        <div class="flex justify-between text-xs"><span class="text-neutral-400">90-day alert</span><span class="text-neutral-600">{fmtDate(expiry.alert_90_days_sent_at)}</span></div>
        <div class="flex justify-between text-xs"><span class="text-neutral-400">30-day alert</span><span class="text-neutral-600">{fmtDate(expiry.alert_30_days_sent_at)}</span></div>
        <div class="flex justify-between text-xs"><span class="text-neutral-400">Expired alert</span><span class="text-neutral-600">{fmtDate(expiry.expired_alert_sent_at)}</span></div>
        <div class="flex justify-between text-xs"><span class="text-neutral-400">Escalated</span><span class="text-neutral-600">{fmtDate(expiry.escalated_at)}</span></div>
      </div>
    </div>
  {/if}
</div>
