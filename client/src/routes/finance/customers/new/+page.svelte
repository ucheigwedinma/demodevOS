<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Customer } from "$lib/types";

  let form = $state({
    name: "",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    notes: "",
    is_active: true,
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const result = await api.post<Customer>("/finance/customers/", form);
      toast.success("Customer created", `"${form.name}" has been added`);
      goto(`/finance/customers/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the customer");
      }
    }
    saving = false;
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }
</script>

<div class="max-w-2xl">
  <Breadcrumb items={[{ label: "Finance", href: "/finance" }, { label: "Customers", href: "/finance/customers" }, { label: "New Customer" }]} />
  <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">New Customer</h1>

  <form onsubmit={handleSubmit} class="space-y-6">
    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Name</span>
        <input
          bind:value={form.name}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Customer name"
        />
        {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
      </label>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Person</span>
          <input
            bind:value={form.contact_person}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Full name"
          />
          {#if fieldError("contact_person")}<p class="mt-1 text-xs text-red-500">{fieldError("contact_person")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email</span>
          <input
            type="email"
            bind:value={form.email}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="customer@example.com"
          />
          {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">{fieldError("email")}</p>{/if}
        </label>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</span>
          <input
            bind:value={form.phone}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="+1 (555) 000-0000"
          />
          {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">{fieldError("phone")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID</span>
          <input
            bind:value={form.tax_id}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Tax identification number"
          />
          {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-500">{fieldError("tax_id")}</p>{/if}
        </label>
      </div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Address</span>
        <textarea
          bind:value={form.address}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Full address"
        ></textarea>
        {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">{fieldError("address")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
        <textarea
          bind:value={form.notes}
          rows={3}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Optional notes"
        ></textarea>
      </label>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <label class="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" bind:checked={form.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
        <span class="text-sm text-neutral-700">Active customer</span>
      </label>
    </div>

    <div class="flex gap-3">
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : "Create Customer"}
      </button>
      <a href="/finance/customers" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
        Cancel
      </a>
    </div>
  </form>
</div>
