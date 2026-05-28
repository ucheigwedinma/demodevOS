<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Bill, VendorListItem, PropertyListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let form = $state({
    bill_number: "",
    vendor: "",
    property: "",
    issue_date: "",
    due_date: "",
    notes: "",
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);
  let vendors = $state<VendorListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);

  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" });
      vendors = res.results;
    } catch {
      vendors = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  $effect(() => {
    fetchVendors();
    fetchProperties();
  });

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const BILL_SAMPLES = [
    {
      bill_number: "BILL-2025-0042",
      notes: "Cement and rebar delivery for Phase 3 foundation works",
      issue_offset: -3,
      due_offset: 27,
    },
    {
      bill_number: "BILL-2025-0043",
      notes: "Electrical wiring and panel installation — Block A",
      issue_offset: -7,
      due_offset: 23,
    },
    {
      bill_number: "BILL-2025-0044",
      notes: "Plumbing fixtures and fittings — Units 12–24",
      issue_offset: -1,
      due_offset: 29,
    },
    {
      bill_number: "BILL-2025-0045",
      notes: "Site security services — March 2025",
      issue_offset: -14,
      due_offset: 16,
    },
  ];

  let billDevIdx = $state(0);

  function devFillBill() {
    const sample = BILL_SAMPLES[billDevIdx % BILL_SAMPLES.length];
    billDevIdx++;

    const today = new Date();
    const issueDate = new Date(today);
    issueDate.setDate(issueDate.getDate() + sample.issue_offset);
    const dueDate = new Date(today);
    dueDate.setDate(dueDate.getDate() + sample.due_offset);

    form.bill_number = sample.bill_number;
    form.vendor = vendors.length > 0 ? String(vendors[billDevIdx % vendors.length].id) : "";
    form.property = properties.length > 0 ? String(properties[billDevIdx % properties.length].id) : "";
    form.issue_date = issueDate.toISOString().slice(0, 10);
    form.due_date = dueDate.toISOString().slice(0, 10);
    form.notes = sample.notes;
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        vendor: form.vendor ? Number(form.vendor) : null,
        property: form.property ? Number(form.property) : null,
        issue_date: form.issue_date || null,
        due_date: form.due_date || null,
        notes: form.notes,
      };
      if (form.bill_number.trim()) {
        payload.bill_number = form.bill_number.trim();
      }
      const result = await api.post<Bill>("/finance/bills/", payload);
      toast.success("Bill created", `"${result.bill_number}" has been added`);
      goto(`/finance/bills/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the bill");
      }
    }
    saving = false;
  }
</script>

<div class="max-w-2xl">
  <Breadcrumb items={[{ label: "Finance", href: "/finance" }, { label: "Bills", href: "/finance/bills" }, { label: "New Bill" }]} />
  <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">New Bill</h1>

  <form onsubmit={handleSubmit} class="space-y-6">
    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Bill Number <span class="text-neutral-400 font-normal">(auto-generated if blank)</span></span>
        <input
          bind:value={form.bill_number}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Auto-generated"
        />
        {#if fieldError("bill_number")}<p class="mt-1 text-xs text-red-500">{fieldError("bill_number")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
        <select
          bind:value={form.vendor}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">Select a vendor</option>
          {#each vendors as vendor}
            <option value={String(vendor.id)}>{vendor.name}</option>
          {/each}
        </select>
        {#if fieldError("vendor")}<p class="mt-1 text-xs text-red-500">{fieldError("vendor")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={form.property}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each properties as property}
            <option value={String(property.id)}>{property.name}</option>
          {/each}
        </select>
        {#if fieldError("property")}<p class="mt-1 text-xs text-red-500">{fieldError("property")}</p>{/if}
      </label>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
          <DateInput bind:value={form.issue_date} />
          {#if fieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{fieldError("issue_date")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Due Date</span>
          <DateInput bind:value={form.due_date} />
          {#if fieldError("due_date")}<p class="mt-1 text-xs text-red-500">{fieldError("due_date")}</p>{/if}
        </label>
      </div>

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
    </div>

    <div class="flex gap-3">
      {#if isDev}
        <button
          type="button"
          onclick={devFillBill}
          class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Create Bill"}
      </button>
      <a href="/finance/bills" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
        Cancel
      </a>
    </div>
  </form>
</div>
