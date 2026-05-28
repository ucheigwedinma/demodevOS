<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { GoodsReceipt, GoodsReceiptItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const id = $derived($page.params.id);

  let grn = $state<GoodsReceipt | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);
  let errors = $state<Record<string, string[]>>({});

  // Editable form state
  let form = $state({
    status: "pending",
    received_date: "",
    received_by: "",
    delivery_note_number: "",
    inspection_notes: "",
    notes: "",
  });

  function formatDate(v: string | null): string {
    return v ? new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "\u2014";
  }

  async function loadGRN() {
    loading = true;
    try {
      grn = await api.get<GoodsReceipt>(`/procurement/goods-receipts/${id}/`);
      form = {
        status: grn.status,
        received_date: grn.received_date,
        received_by: grn.received_by,
        delivery_note_number: grn.delivery_note_number,
        inspection_notes: grn.inspection_notes,
        notes: grn.notes,
      };
    } catch {
      grn = null;
    }
    loading = false;
  }

  $effect(() => {
    void id;
    loadGRN();
  });

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  // --- Save GRN via nested endpoint ---
  async function handleSave(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;
    try {
      const payload = {
        status: form.status,
        received_date: form.received_date || null,
        received_by: form.received_by,
        delivery_note_number: form.delivery_note_number,
        inspection_notes: form.inspection_notes,
        notes: form.notes,
      };
      const updated = await api.patch<GoodsReceipt>(
        `/procurement/purchase-orders/${grn!.purchase_order}/goods-receipts/${id}/`,
        payload,
      );
      grn = updated;
      toast.success("Goods receipt updated", "Changes have been saved");
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the goods receipt");
      }
    }
    saving = false;
  }

  // --- Delete GRN via nested endpoint ---
  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this goods receipt? This action cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(
        `/procurement/purchase-orders/${grn!.purchase_order}/goods-receipts/${id}/`,
      );
      toast.success("Goods receipt deleted", "The goods receipt has been removed");
      goto("/procurement/goods-receipts");
    } catch {
      toast.error("Something went wrong", "Could not delete the goods receipt");
    }
    deleting = false;
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !grn}
  <div class="text-center py-24">
    <p class="text-neutral-400">Goods receipt not found.</p>
    <a href="/procurement/goods-receipts" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to goods receipts</a>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-8">
    <Breadcrumb items={[
      { label: "Procurement", href: "/procurement" },
      { label: "Goods Receipts", href: "/procurement/goods-receipts" },
      { label: grn.grn_number },
    ]} />
    <div class="flex items-center gap-4 mt-3">
      <h1 class="text-2xl font-bold text-neutral-900">{grn.grn_number}</h1>
      <StatusBadge status={grn.status} label={grn.status === "partially_accepted" ? "Partial" : undefined} size="md" />
    </div>
    <p class="text-sm text-neutral-500 mt-1">
      PO:
      <button
        onclick={() => goto(`/procurement/purchase-orders/${grn!.purchase_order}`)}
        class="text-neutral-900 font-medium hover:underline"
      >
        {grn.po_number}
      </button>
      <span class="mx-1.5 text-neutral-300">|</span>
      {grn.vendor_name}
    </p>
  </div>

  <!-- Form card -->
  <div class="mb-8">
    <form onsubmit={handleSave} class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
      <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Receipt Details</h3>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
          <select
            bind:value={form.status}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="pending">Pending</option>
            <option value="inspected">Inspected</option>
            <option value="accepted">Accepted</option>
            <option value="partially_accepted">Partially Accepted</option>
            <option value="rejected">Rejected</option>
          </select>
          {#if fieldError("status")}<p class="mt-1 text-xs text-red-500">{fieldError("status")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Received Date</span>
          <DateInput bind:value={form.received_date} />
          {#if fieldError("received_date")}<p class="mt-1 text-xs text-red-500">{fieldError("received_date")}</p>{/if}
        </label>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Received By</span>
          <input
            type="text"
            bind:value={form.received_by}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Name of person who received"
          />
          {#if fieldError("received_by")}<p class="mt-1 text-xs text-red-500">{fieldError("received_by")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Note Number</span>
          <input
            type="text"
            bind:value={form.delivery_note_number}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Delivery note or waybill #"
          />
          {#if fieldError("delivery_note_number")}<p class="mt-1 text-xs text-red-500">{fieldError("delivery_note_number")}</p>{/if}
        </label>
      </div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Inspection Notes</span>
        <textarea
          bind:value={form.inspection_notes}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Notes from inspection..."
        ></textarea>
        {#if fieldError("inspection_notes")}<p class="mt-1 text-xs text-red-500">{fieldError("inspection_notes")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
        <textarea
          bind:value={form.notes}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Optional notes..."
        ></textarea>
        {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
      </label>

      <div class="flex items-center justify-between pt-2">
        <div class="flex gap-3">
          <button
            type="submit"
            disabled={saving}
            class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                   hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
        <button
          type="button"
          onclick={handleDelete}
          disabled={deleting}
          class="px-4 py-2.5 border border-red-200 text-red-600 rounded-lg text-sm font-medium
                 hover:bg-red-50 disabled:opacity-50 transition-colors"
        >
          {deleting ? "Deleting..." : "Delete Receipt"}
        </button>
      </div>
    </form>
  </div>

  <!-- Items table -->
  <div class="mb-8">
    <h3 class="text-lg font-semibold text-neutral-900 mb-4">Received Items</h3>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if grn.items.length > 0}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PO Item</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Received Qty</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Accepted Qty</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Rejected Qty</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Rejection Reason</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each grn.items as item}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-neutral-900">{item.po_item_description}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{item.quantity_received}</td>
                <td class="px-5 py-4 text-right text-emerald-600 tabular-nums">{item.quantity_accepted}</td>
                <td class="px-5 py-4 text-right tabular-nums {Number(item.quantity_rejected) > 0 ? 'text-red-600' : 'text-neutral-500'}">{item.quantity_rejected}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-xs truncate">{item.rejection_reason || "\u2014"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-400">No items on this goods receipt yet.</p>
        </div>
      {/if}
    </div>
  </div>
{/if}
