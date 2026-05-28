<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Investor, InvestorType } from "$lib/types";

  const investorTypeOptions: Array<{ value: InvestorType; label: string }> = [
    { value: "individual", label: "Individual" },
    { value: "institutional", label: "Institutional" },
    { value: "family_office", label: "Family Office" },
    { value: "fund", label: "Fund" },
    { value: "corporate", label: "Corporate" },
  ];

  let form = $state({
    name: "",
    investor_type: "individual" as InvestorType,
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    entity_name: "",
    registration_number: "",
    notes: "",
    is_active: true,
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  function hasFieldError(field: string): boolean {
    return Boolean(fieldError(field));
  }

  function parseApiErrorMessage(error: ApiError): string {
    const detail = error.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    const nonField = error.fieldErrors.non_field_errors?.[0];
    if (nonField) return nonField;
    return "Please fix the highlighted fields below.";
  }

  async function handleSubmit(event: Event) {
    event.preventDefault();

    errors = {};
    if (!form.name.trim()) {
      errors = { name: ["Investor name is required."] };
      toast.error("Validation error", "Investor name is required.");
      return;
    }

    saving = true;
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
        contact_person: form.contact_person.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
        tax_id: form.tax_id.trim(),
        entity_name: form.entity_name.trim(),
        registration_number: form.registration_number.trim(),
        notes: form.notes.trim(),
      };

      const created = await api.post<Investor>("/finance/investors/", payload);
      toast.success("Investor created", `"${created.name}" has been added.`);
      if (typeof created.id === "number") {
        goto(`/finance/investors/${created.id}`);
      } else {
        goto("/finance/investors");
      }
    } catch (error) {
      if (error instanceof ApiError) {
        errors = error.fieldErrors;
        toast.error("Could not create investor", parseApiErrorMessage(error));
      } else {
        toast.error("Could not create investor", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="max-w-3xl space-y-6">
  <div>
    <Breadcrumb items={[{ label: "Finance", href: "/finance" }, { label: "Investors", href: "/finance/investors" }, { label: "New Investor" }]} />
    <h1 class="mt-3 text-2xl font-bold text-neutral-800">New Investor</h1>
    <p class="mt-1 text-sm text-neutral-500">Create an external investor profile for project funding and waterfall allocations.</p>
  </div>

  <form onsubmit={handleSubmit} class="space-y-6">
    {#if fieldError("non_field_errors")}
      <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {fieldError("non_field_errors")}
      </div>
    {/if}

    <div class="rounded-xl border border-neutral-200 bg-white p-6 space-y-5">
      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Investor Name</span>
        <input
          bind:value={form.name}
          class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('name') ? 'border-red-300' : 'border-neutral-200'}"
          placeholder="Investor name"
        />
        {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
      </label>

      <div class="grid gap-4 md:grid-cols-2">
        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Investor Type</span>
          <select
            bind:value={form.investor_type}
            class="w-full rounded-lg border px-3 py-2.5 text-sm bg-white focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('investor_type') ? 'border-red-300' : 'border-neutral-200'}"
          >
            {#each investorTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          {#if fieldError("investor_type")}<p class="mt-1 text-xs text-red-500">{fieldError("investor_type")}</p>{/if}
        </label>

        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Entity Name (optional)</span>
          <input
            bind:value={form.entity_name}
            class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('entity_name') ? 'border-red-300' : 'border-neutral-200'}"
            placeholder="Legal entity name"
          />
          {#if fieldError("entity_name")}<p class="mt-1 text-xs text-red-500">{fieldError("entity_name")}</p>{/if}
        </label>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Tax ID (optional)</span>
          <input
            bind:value={form.tax_id}
            class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('tax_id') ? 'border-red-300' : 'border-neutral-200'}"
            placeholder="Tax identification number"
          />
          {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-500">{fieldError("tax_id")}</p>{/if}
        </label>

        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Registration Number (optional)</span>
          <input
            bind:value={form.registration_number}
            class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('registration_number') ? 'border-red-300' : 'border-neutral-200'}"
            placeholder="Company registration number"
          />
          {#if fieldError("registration_number")}<p class="mt-1 text-xs text-red-500">{fieldError("registration_number")}</p>{/if}
        </label>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-6 space-y-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Contact</h2>

      <div class="grid gap-4 md:grid-cols-2">
        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Contact Person (optional)</span>
          <input
            bind:value={form.contact_person}
            class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('contact_person') ? 'border-red-300' : 'border-neutral-200'}"
            placeholder="Full name"
          />
          {#if fieldError("contact_person")}<p class="mt-1 text-xs text-red-500">{fieldError("contact_person")}</p>{/if}
        </label>

        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Email (optional)</span>
          <input
            type="email"
            bind:value={form.email}
            class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('email') ? 'border-red-300' : 'border-neutral-200'}"
            placeholder="name@company.com"
          />
          {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">{fieldError("email")}</p>{/if}
        </label>
      </div>

      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Phone (optional)</span>
        <input
          bind:value={form.phone}
          class="w-full rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('phone') ? 'border-red-300' : 'border-neutral-200'}"
          placeholder="+1 (555) 000-0000"
        />
        {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">{fieldError("phone")}</p>{/if}
      </label>

      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Address (optional)</span>
        <textarea
          bind:value={form.address}
          rows={3}
          class="w-full resize-none rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('address') ? 'border-red-300' : 'border-neutral-200'}"
          placeholder="Mailing address"
        ></textarea>
        {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">{fieldError("address")}</p>{/if}
      </label>

      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Notes (optional)</span>
        <textarea
          bind:value={form.notes}
          rows={3}
          class="w-full resize-none rounded-lg border px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-800 {hasFieldError('notes') ? 'border-red-300' : 'border-neutral-200'}"
          placeholder="Additional context"
        ></textarea>
        {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
      </label>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-6">
      <label class="inline-flex items-center gap-3">
        <input type="checkbox" bind:checked={form.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
        <span class="text-sm text-neutral-700">Active investor</span>
      </label>
    </div>

    <div class="flex gap-3">
      <button
        type="submit"
        disabled={saving}
        class="rounded-lg bg-neutral-800 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Create Investor"}
      </button>
      <a
        href="/finance/investors"
        class="rounded-lg border border-neutral-200 px-6 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </a>
    </div>
  </form>
</div>
