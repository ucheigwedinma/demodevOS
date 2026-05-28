<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { IdentificationDocument, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // --- Table State ---
  let documents = $state<IdentificationDocument[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let typeFilter = $state("");

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let editingDoc = $state<IdentificationDocument | null>(null);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let selectedFile = $state<File | null>(null);
  let createForm = $state({
    user: "",
    document_type: "",
    document_number: "",
    issuing_authority: "",
    issuing_country: "",
    issue_date: "",
    expiry_date: "",
    notes: "",
  });

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      user: "",
      document_type: "",
      document_number: "",
      issuing_authority: "",
      issuing_country: "",
      issue_date: "",
      expiry_date: "",
      notes: "",
    };
    createErrors = {};
    selectedFile = null;
    editingDoc = null;
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

  // --- Helpers ---
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function isExpired(expiryDate: string | null): boolean {
    if (!expiryDate) return false;
    return new Date(expiryDate + "T00:00:00") < new Date();
  }

  function documentTypeLabel(dt: string): string {
    const map: Record<string, string> = {
      passport: "Passport",
      national_id: "National ID",
      driving_license: "Driving License",
      visa: "Visa",
      work_permit: "Work Permit",
      residence_permit: "Residence Permit",
      emirates_id: "Emirates ID",
      other: "Other",
    };
    return map[dt] ?? dt;
  }

  // --- Data Fetching ---
  async function fetchDocuments() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (typeFilter) params.document_type = typeFilter;

      const res = await api.get<PaginatedResponse<IdentificationDocument>>(
        "/hr/id-documents/",
        params,
      );
      documents = res.results;
      totalCount = res.count;
    } catch {
      documents = [];
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
      fetchDocuments();
    }, 300);
  }

  function handleTypeChange(value: string) {
    typeFilter = value;
    currentPage = 1;
    fetchDocuments();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchDocuments();
  }

  function handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    selectedFile = input.files?.[0] ?? null;
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      if (editingDoc) {
        // Edit mode (no file change via patch)
        const payload: Record<string, unknown> = {
          user: Number(createForm.user),
          document_type: createForm.document_type,
          document_number: createForm.document_number,
          issuing_authority: createForm.issuing_authority || null,
          issuing_country: createForm.issuing_country || null,
          issue_date: createForm.issue_date || null,
          expiry_date: createForm.expiry_date || null,
          notes: createForm.notes || "",
        };

        await api.patch<IdentificationDocument>(`/hr/id-documents/${editingDoc.id}/`, payload);
        toast.success("Document updated", "The identification document has been updated");
      } else {
        // Create mode with file upload
        const formData = new FormData();
        formData.append("user", createForm.user);
        formData.append("document_type", createForm.document_type);
        formData.append("document_number", createForm.document_number);
        if (createForm.issuing_authority) formData.append("issuing_authority", createForm.issuing_authority);
        if (createForm.issuing_country) formData.append("issuing_country", createForm.issuing_country);
        if (createForm.issue_date) formData.append("issue_date", createForm.issue_date);
        if (createForm.expiry_date) formData.append("expiry_date", createForm.expiry_date);
        if (createForm.notes) formData.append("notes", createForm.notes);
        if (selectedFile) formData.append("file", selectedFile);

        await api.upload<IdentificationDocument>("/hr/id-documents/", formData);
        toast.success("Document created", "The identification document has been recorded");
      }

      showSlideOver = false;
      resetCreateForm();
      fetchDocuments();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not save the document");
      }
    }
    saving = false;
  }

  async function handleDelete(doc: IdentificationDocument) {
    if (!confirm(`Delete document ${doc.document_number}?`)) return;
    try {
      await api.delete(`/hr/id-documents/${doc.id}/`);
      toast.success("Document deleted", "The identification document has been removed");
      fetchDocuments();
    } catch {
      toast.error("Error", "Could not delete the document");
    }
  }

  function openCreate() {
    resetCreateForm();
    showSlideOver = true;
  }

  function openEdit(doc: IdentificationDocument) {
    editingDoc = doc;
    createForm = {
      user: String(doc.user),
      document_type: doc.document_type,
      document_number: doc.document_number,
      issuing_authority: doc.issuing_authority || "",
      issuing_country: doc.issuing_country || "",
      issue_date: doc.issue_date || "",
      expiry_date: doc.expiry_date || "",
      notes: doc.notes || "",
    };
    createErrors = {};
    selectedFile = null;
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  $effect(() => {
    fetchDocuments();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Identification Documents</h1>
      <p class="mt-1 text-sm text-neutral-500">Employee identification and travel documents</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Document
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Search by employee, number..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Document Type</span>
        <select
          value={typeFilter}
          onchange={(e) => handleTypeChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Types</option>
          <option value="passport">Passport</option>
          <option value="national_id">National ID</option>
          <option value="driving_license">Driving License</option>
          <option value="visa">Visa</option>
          <option value="work_permit">Work Permit</option>
          <option value="residence_permit">Residence Permit</option>
          <option value="emirates_id">Emirates ID</option>
          <option value="other">Other</option>
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if documents.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No identification documents found</p>
        <button
          onclick={openCreate}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first document
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Employee</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Document Type</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Number</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issuing Country</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expiry Date</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each documents as doc}
              {@const expired = isExpired(doc.expiry_date)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-sm font-medium text-neutral-900">{doc.user_name}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{documentTypeLabel(doc.document_type)}</td>
                <td class="px-5 py-4 text-sm text-neutral-600 tabular-nums">{doc.document_number}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{doc.issuing_country || "\u2014"}</td>
                <td class="px-5 py-4 text-sm {expired ? 'text-red-500 font-medium' : 'text-neutral-600'}">
                  {formatDate(doc.expiry_date)}
                  {#if expired}
                    <span class="ml-1 text-xs">(expired)</span>
                  {/if}
                </td>
                <td class="px-5 py-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    {#if doc.file}
                      <a
                        href={doc.file}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
                        title="View file"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                        </svg>
                      </a>
                    {/if}
                    <button
                      onclick={() => openEdit(doc)}
                      class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
                      title="Edit"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
                      </svg>
                    </button>
                    <button
                      onclick={() => handleDelete(doc)}
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

<!-- Slide-Over: Create/Edit Document -->
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
        {editingDoc ? "Edit Document" : "New Document"}
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
      <form id="doc-form" onsubmit={handleSubmit} class="space-y-5">
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

        <!-- Document Type & Number -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Document Type <span class="text-neutral-400">*</span></span>
            <select
              bind:value={createForm.document_type}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">Select type</option>
              <option value="passport">Passport</option>
              <option value="national_id">National ID</option>
              <option value="driving_license">Driving License</option>
              <option value="visa">Visa</option>
              <option value="work_permit">Work Permit</option>
              <option value="residence_permit">Residence Permit</option>
              <option value="emirates_id">Emirates ID</option>
              <option value="other">Other</option>
            </select>
            {#if createFieldError("document_type")}<p class="mt-1 text-xs text-red-500">{createFieldError("document_type")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Document Number <span class="text-neutral-400">*</span></span>
            <input
              type="text"
              bind:value={createForm.document_number}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("document_number")}<p class="mt-1 text-xs text-red-500">{createFieldError("document_number")}</p>{/if}
          </label>
        </div>

        <!-- Issuing Authority & Country -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issuing Authority</span>
            <input
              type="text"
              bind:value={createForm.issuing_authority}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("issuing_authority")}<p class="mt-1 text-xs text-red-500">{createFieldError("issuing_authority")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issuing Country</span>
            <input
              type="text"
              bind:value={createForm.issuing_country}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("issuing_country")}<p class="mt-1 text-xs text-red-500">{createFieldError("issuing_country")}</p>{/if}
          </label>
        </div>

        <!-- Issue Date & Expiry Date -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
            <DateInput bind:value={createForm.issue_date} />
            {#if createFieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("issue_date")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Expiry Date</span>
            <DateInput bind:value={createForm.expiry_date} />
            {#if createFieldError("expiry_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("expiry_date")}</p>{/if}
          </label>
        </div>

        <!-- File Upload -->
        {#if !editingDoc}
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">File</span>
            <input
              type="file"
              onchange={handleFileChange}
              class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white file:mr-3 file:px-3 file:py-1.5 file:border-0 file:rounded-md file:bg-neutral-100 file:text-neutral-700 file:text-sm file:font-medium hover:file:bg-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("file")}<p class="mt-1 text-xs text-red-500">{createFieldError("file")}</p>{/if}
          </label>
        {:else if editingDoc.file}
          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Current File</span>
            <a
              href={editingDoc.file}
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-neutral-600 hover:text-neutral-900 hover:underline"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              View attached file
            </a>
          </div>
        {/if}

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
        </label>
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
        form="doc-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : editingDoc ? "Update Document" : "Create Document"}
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
