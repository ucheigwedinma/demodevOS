<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { EmergencyContact, PaginatedResponse } from "$lib/types";

  // --- Table State ---
  let contacts = $state<EmergencyContact[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let userFilter = $state("");

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let editingContact = $state<EmergencyContact | null>(null);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    user: "",
    name: "",
    relationship: "",
    phone: "",
    secondary_phone: "",
    email: "",
    address: "",
    is_primary: false,
    sort_order: "0",
  });

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      user: "",
      name: "",
      relationship: "",
      phone: "",
      secondary_phone: "",
      email: "",
      address: "",
      is_primary: false,
      sort_order: "0",
    };
    createErrors = {};
    editingContact = null;
  }

  // --- Derived ---
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  // --- Data Fetching ---
  async function fetchContacts() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (userFilter) params.user = userFilter;

      const res = await api.get<PaginatedResponse<EmergencyContact>>(
        "/hr/emergency-contacts/",
        params,
      );
      contacts = res.results;
      totalCount = res.count;
    } catch {
      contacts = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchContacts();
    }, 300);
  }

  function handleUserFilterChange(value: string) {
    userFilter = value;
    currentPage = 1;
    fetchContacts();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchContacts();
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        user: Number(createForm.user),
        name: createForm.name,
        relationship: createForm.relationship,
        phone: createForm.phone,
        secondary_phone: createForm.secondary_phone || null,
        email: createForm.email || null,
        address: createForm.address || null,
        is_primary: createForm.is_primary,
        sort_order: Number(createForm.sort_order) || 0,
      };

      if (editingContact) {
        await api.patch<EmergencyContact>(`/hr/emergency-contacts/${editingContact.id}/`, payload);
        toast.success("Contact updated", "The emergency contact has been updated");
      } else {
        await api.post<EmergencyContact>("/hr/emergency-contacts/", payload);
        toast.success("Contact created", "The emergency contact has been recorded");
      }

      showSlideOver = false;
      resetCreateForm();
      fetchContacts();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not save the contact");
      }
    }
    saving = false;
  }

  async function handleDelete(contact: EmergencyContact) {
    if (!confirm(`Delete emergency contact "${contact.name}"?`)) return;
    try {
      await api.delete(`/hr/emergency-contacts/${contact.id}/`);
      toast.success("Contact deleted", "The emergency contact has been removed");
      fetchContacts();
    } catch {
      toast.error("Error", "Could not delete the contact");
    }
  }

  function openCreate() {
    resetCreateForm();
    showSlideOver = true;
  }

  function openEdit(contact: EmergencyContact) {
    editingContact = contact;
    createForm = {
      user: String(contact.user),
      name: contact.name,
      relationship: contact.relationship,
      phone: contact.phone,
      secondary_phone: contact.secondary_phone || "",
      email: contact.email || "",
      address: contact.address || "",
      is_primary: contact.is_primary,
      sort_order: String(contact.sort_order),
    };
    createErrors = {};
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  $effect(() => {
    fetchContacts();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Emergency Contacts</h1>
      <p class="mt-1 text-sm text-neutral-500">Employee emergency contact information</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Contact
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Search by contact name, relationship..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Filter by User ID</span>
        <input
          type="text"
          placeholder="Enter user ID..."
          value={userFilter}
          oninput={(e) => handleUserFilterChange((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if contacts.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No emergency contacts found</p>
        <button
          onclick={openCreate}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first emergency contact
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Employee</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Contact Name</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Relationship</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Phone</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Primary</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each contacts as contact}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-sm font-medium text-neutral-900">{contact.user_name}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{contact.name}</td>
                <td class="px-5 py-4 text-sm text-neutral-600 capitalize">{contact.relationship || "\u2014"}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{contact.phone || "\u2014"}</td>
                <td class="px-5 py-4">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {contact.is_primary ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                    {contact.is_primary ? "Primary" : "Secondary"}
                  </span>
                </td>
                <td class="px-5 py-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      onclick={() => openEdit(contact)}
                      class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
                      title="Edit"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
                      </svg>
                    </button>
                    <button
                      onclick={() => handleDelete(contact)}
                      class="p-1.5 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-neutral-100 transition-colors"
                      title="Delete"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<!-- Slide-Over: Create/Edit Emergency Contact -->
{#if showSlideOver}
  <!-- Backdrop -->
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeSlideOver}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <!-- Panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg flex flex-col bg-white shadow-2xl animate-slide-in-right">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-900">
        {editingContact ? "Edit Emergency Contact" : "New Emergency Contact"}
      </h2>
      <button
        onclick={closeSlideOver}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="contact-form" onsubmit={handleSubmit} class="space-y-5">
        <!-- User -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">User ID <span class="text-neutral-400">*</span></span>
          <input
            type="number"
            bind:value={createForm.user}
            required
            placeholder="Enter user ID"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if createFieldError("user")}<p class="mt-1 text-xs text-red-500">{createFieldError("user")}</p>{/if}
        </label>

        <!-- Name & Relationship -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Name <span class="text-neutral-400">*</span></span>
            <input
              type="text"
              bind:value={createForm.name}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("name")}<p class="mt-1 text-xs text-red-500">{createFieldError("name")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Relationship <span class="text-neutral-400">*</span></span>
            <input
              type="text"
              bind:value={createForm.relationship}
              required
              placeholder="e.g. Spouse, Parent, Sibling"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("relationship")}<p class="mt-1 text-xs text-red-500">{createFieldError("relationship")}</p>{/if}
          </label>
        </div>

        <!-- Phone & Secondary Phone -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone <span class="text-neutral-400">*</span></span>
            <input
              type="tel"
              bind:value={createForm.phone}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("phone")}<p class="mt-1 text-xs text-red-500">{createFieldError("phone")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Secondary Phone</span>
            <input
              type="tel"
              bind:value={createForm.secondary_phone}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("secondary_phone")}<p class="mt-1 text-xs text-red-500">{createFieldError("secondary_phone")}</p>{/if}
          </label>
        </div>

        <!-- Email -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email</span>
          <input
            type="email"
            bind:value={createForm.email}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if createFieldError("email")}<p class="mt-1 text-xs text-red-500">{createFieldError("email")}</p>{/if}
        </label>

        <!-- Address -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Address</span>
          <textarea
            bind:value={createForm.address}
            rows="3"
            placeholder="Full address..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if createFieldError("address")}<p class="mt-1 text-xs text-red-500">{createFieldError("address")}</p>{/if}
        </label>

        <!-- Primary & Sort Order -->
        <div class="grid grid-cols-2 gap-4 items-start">
          <label class="flex items-center gap-3 pt-6">
            <input
              type="checkbox"
              bind:checked={createForm.is_primary}
              class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
            />
            <span class="text-sm font-medium text-neutral-700">Primary Contact</span>
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Sort Order</span>
            <input
              type="number"
              min="0"
              bind:value={createForm.sort_order}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if createFieldError("sort_order")}<p class="mt-1 text-xs text-red-500">{createFieldError("sort_order")}</p>{/if}
          </label>
        </div>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      <button
        type="button"
        onclick={closeSlideOver}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="contact-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : editingContact ? "Update Contact" : "Create Contact"}
      </button>
    </div>
  </div>
{/if}

<svelte:window onkeydown={(e) => { if (e.key === "Escape" && showSlideOver) closeSlideOver(); }} />

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
