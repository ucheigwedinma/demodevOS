<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type {
    Invoice,
    CustomerListItem,
    PropertyListItem,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let customers = $state<CustomerListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let submitting = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});

  let formData = $state({
    invoice_number: "",
    customer: "",
    property: "",
    issue_date: "",
    due_date: "",
    notes: "",
  });

  function fieldError(field: string): string {
    return fieldErrors[field]?.join(", ") ?? "";
  }

  async function fetchCustomers() {
    try {
      const res = await api.get<PaginatedResponse<CustomerListItem>>(
        "/finance/customers/",
        { page_size: "200" },
      );
      customers = res.results;
    } catch {
      customers = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>(
        "/finance/properties/",
        { page_size: "200" },
      );
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    submitting = true;
    fieldErrors = {};

    try {
      const body: Record<string, unknown> = {
        customer: formData.customer ? Number(formData.customer) : null,
        issue_date: formData.issue_date,
        due_date: formData.due_date,
        notes: formData.notes,
      };
      if (formData.invoice_number.trim()) {
        body.invoice_number = formData.invoice_number.trim();
      }
      if (formData.property) {
        body.property = Number(formData.property);
      }

      const result = await api.post<Invoice>("/finance/invoices/", body);
      toast.success("Invoice created", `"${result.invoice_number}" has been added`);
      goto(`/finance/invoices/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the invoice");
      }
    } finally {
      submitting = false;
    }
  }

  $effect(() => {
    fetchCustomers();
    fetchProperties();
  });

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const INVOICE_SAMPLES = [
    {
      invoice_number: "INV-2025-0091",
      notes: "Unit 14B — first quarterly service charge",
      issue_offset: 0,
      due_offset: 30,
    },
    {
      invoice_number: "INV-2025-0092",
      notes: "Parking bay lease renewal — Basement Level 2, Bay 37",
      issue_offset: -5,
      due_offset: 25,
    },
    {
      invoice_number: "INV-2025-0093",
      notes: "Roof terrace event space hire — corporate function 22 Mar",
      issue_offset: -2,
      due_offset: 14,
    },
    {
      invoice_number: "INV-2025-0094",
      notes: "Fit-out deposit — Unit 8A commercial shell",
      issue_offset: -1,
      due_offset: 7,
    },
  ];

  let invoiceDevIdx = $state(0);

  function devFillInvoice() {
    const sample = INVOICE_SAMPLES[invoiceDevIdx % INVOICE_SAMPLES.length];
    invoiceDevIdx++;

    const today = new Date();
    const issueDate = new Date(today);
    issueDate.setDate(issueDate.getDate() + sample.issue_offset);
    const dueDate = new Date(today);
    dueDate.setDate(dueDate.getDate() + sample.due_offset);

    formData.invoice_number = sample.invoice_number;
    formData.customer = customers.length > 0 ? String(customers[invoiceDevIdx % customers.length].id) : "";
    formData.property = properties.length > 0 ? String(properties[invoiceDevIdx % properties.length].id) : "";
    formData.issue_date = issueDate.toISOString().slice(0, 10);
    formData.due_date = dueDate.toISOString().slice(0, 10);
    formData.notes = sample.notes;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <Breadcrumb items={[{ label: "Finance", href: "/finance" }, { label: "Invoices", href: "/finance/invoices" }, { label: "New Invoice" }]} />
    <h1 class="text-2xl font-bold text-neutral-800 mt-3">New Invoice</h1>
    <p class="mt-1 text-sm text-neutral-500">Create a new invoice</p>
  </div>

  <!-- Form -->
  <form onsubmit={handleSubmit} class="bg-white rounded-xl border border-neutral-200 p-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Invoice Number <span class="text-neutral-400">(auto-generated if blank)</span></span
        >
        <input
          type="text"
          bind:value={formData.invoice_number}
          placeholder="Auto-generated"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
        {#if fieldError("invoice_number")}
          <p class="mt-1 text-xs text-red-600">{fieldError("invoice_number")}</p>
        {/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Customer</span
        >
        <select
          bind:value={formData.customer}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">Select a customer</option>
          {#each customers as customer}
            <option value={String(customer.id)}>{customer.name}</option>
          {/each}
        </select>
        {#if fieldError("customer")}
          <p class="mt-1 text-xs text-red-600">{fieldError("customer")}</p>
        {/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Property <span class="text-neutral-400">(optional)</span></span
        >
        <select
          bind:value={formData.property}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">None</option>
          {#each properties as property}
            <option value={String(property.id)}>{property.name}</option>
          {/each}
        </select>
        {#if fieldError("property")}
          <p class="mt-1 text-xs text-red-600">{fieldError("property")}</p>
        {/if}
      </label>

      <div class="hidden md:block"></div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Issue Date</span
        >
        <DateInput bind:value={formData.issue_date} />
        {#if fieldError("issue_date")}
          <p class="mt-1 text-xs text-red-600">{fieldError("issue_date")}</p>
        {/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Due Date</span
        >
        <DateInput bind:value={formData.due_date} />
        {#if fieldError("due_date")}
          <p class="mt-1 text-xs text-red-600">{fieldError("due_date")}</p>
        {/if}
      </label>

      <div class="md:col-span-2">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5"
            >Notes</span
          >
          <textarea
            bind:value={formData.notes}
            rows={3}
            placeholder="Additional notes..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("notes")}
            <p class="mt-1 text-xs text-red-600">{fieldError("notes")}</p>
          {/if}
        </label>
      </div>
    </div>

    <div class="flex items-center justify-end gap-3 mt-8 pt-6 border-t border-neutral-200">
      {#if isDev}
        <button
          type="button"
          onclick={devFillInvoice}
          class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <a
        href="/finance/invoices"
        class="px-4 py-2.5 text-sm font-medium text-neutral-700 rounded-lg border border-neutral-200 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </a>
      <button
        type="submit"
        disabled={submitting}
        class="inline-flex items-center px-5 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {#if submitting}
          <div
            class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"
          ></div>
        {/if}
        Create Invoice
      </button>
    </div>
  </form>
</div>
