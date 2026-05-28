<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { HRDocument, PaginatedResponse } from "$lib/types";

  // ---------------------------------------------------------------------------
  // List state
  // ---------------------------------------------------------------------------
  let documents = $state<HRDocument[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // Filters
  let search = $state("");
  let categoryFilter = $state("");

  // ---------------------------------------------------------------------------
  // Slide-over state
  // ---------------------------------------------------------------------------
  let showSlideOver = $state(false);
  let saving = $state(false);
  let editingId = $state<number | null>(null);
  let fieldErrors = $state<Record<string, string[]>>({});
  let selectedFile = $state<File | null>(null);

  let form = $state({
    user: "",
    title: "",
    category: "",
    description: "",
  });

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);
  let panelTitle = $derived(isEditing ? "Edit HR Attachment" : "New HR Attachment");

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

  // Collect unique categories for the filter dropdown
  let availableCategories = $derived.by(() => {
    const cats = new Set<string>();
    for (const doc of documents) {
      if (doc.category) cats.add(doc.category);
    }
    return Array.from(cats).sort();
  });

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function formatFileSize(size: number | null | undefined): string {
    if (size == null || size === 0) return "\u2014";
    if (size < 1024) return `${size} B`;
    if (size < 1048576) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1048576).toFixed(1)} MB`;
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function resetForm() {
    form = {
      user: "",
      title: "",
      category: "",
      description: "",
    };
    selectedFile = null;
    fieldErrors = {};
  }

  function populateForm(doc: HRDocument) {
    form = {
      user: String(doc.user),
      title: doc.title ?? "",
      category: doc.category ?? "",
      description: doc.description ?? "",
    };
    selectedFile = null;
  }

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  let debounceTimer: ReturnType<typeof setTimeout>;

  async function fetchDocuments() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (categoryFilter) params.category = categoryFilter;

      const res = await api.get<PaginatedResponse<HRDocument>>(
        "/hr/hr-documents/",
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

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------
  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchDocuments();
    }, 300);
  }

  function handleCategoryChange(value: string) {
    categoryFilter = value;
    currentPage = 1;
    fetchDocuments();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchDocuments();
  }

  function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      selectedFile = input.files[0];
    }
  }

  // ---------------------------------------------------------------------------
  // Slide-over actions
  // ---------------------------------------------------------------------------
  function openCreate() {
    resetForm();
    editingId = null;
    showSlideOver = true;
  }

  function openEdit(doc: HRDocument) {
    editingId = doc.id;
    populateForm(doc);
    fieldErrors = {};
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    editingId = null;
    resetForm();
  }

  async function handleSave(e: Event) {
    e.preventDefault();
    saving = true;
    fieldErrors = {};

    try {
      if (isEditing && editingId) {
        if (selectedFile) {
          // Upload new file with FormData
          const formData = new FormData();
          formData.append("user", form.user);
          formData.append("title", form.title);
          formData.append("category", form.category);
          formData.append("description", form.description);
          formData.append("file", selectedFile);
          await api.upload<HRDocument>(`/hr/hr-documents/${editingId}/`, formData);
        } else {
          // Patch without file
          const payload: Record<string, unknown> = {
            user: form.user ? Number(form.user) : null,
            title: form.title,
            category: form.category,
            description: form.description,
          };
          await api.patch<HRDocument>(`/hr/hr-documents/${editingId}/`, payload);
        }
        toast.success("Attachment updated", "HR attachment has been updated successfully.");
      } else {
        // Create with file upload
        const formData = new FormData();
        formData.append("user", form.user);
        formData.append("title", form.title);
        formData.append("category", form.category);
        formData.append("description", form.description);
        if (selectedFile) {
          formData.append("file", selectedFile);
        }
        await api.upload<HRDocument>("/hr/hr-documents/", formData);
        toast.success("Attachment created", "HR attachment has been uploaded successfully.");
      }
      closeSlideOver();
      await fetchDocuments();
    } catch (err) {
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields.");
      } else {
        toast.error("Something went wrong", "Could not save the attachment.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!editingId) return;
    try {
      await api.delete(`/hr/hr-documents/${editingId}/`);
      toast.success("Attachment deleted", "HR attachment has been removed.");
      closeSlideOver();
      await fetchDocuments();
    } catch {
      toast.error("Something went wrong", "Could not delete the attachment.");
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  $effect(() => {
    fetchDocuments();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">HR Attachments</h1>
      <p class="mt-1 text-sm text-neutral-500">General HR documents and attachments</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Attachment
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Employee name or document title..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Category</span>
        <select
          value={categoryFilter}
          onchange={(e) => handleCategoryChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Categories</option>
          {#each availableCategories as cat}
            <option value={cat}>{cat}</option>
          {/each}
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
            <path stroke-linecap="round" stroke-linejoin="round" d="m18.375 12.739-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32m.009-.01-.01.01m5.699-9.941-7.81 7.81a1.5 1.5 0 0 0 2.112 2.13" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No HR attachments found</p>
        <button
          onclick={openCreate}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Upload your first attachment
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Employee</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Size</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date Uploaded</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each documents as doc (doc.id)}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openEdit(doc)}
              >
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{doc.user_name}</div>
                </td>
                <td class="px-5 py-4">
                  <div class="text-sm text-neutral-700">{doc.title}</div>
                  {#if doc.file}
                    <a
                      href={doc.file}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-700 mt-0.5 transition-colors"
                      onclick={(e) => e.stopPropagation()}
                    >
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                      </svg>
                      Download
                    </a>
                  {/if}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {doc.category || "\u2014"}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500 text-right tabular-nums">
                  {formatFileSize(doc.file_size)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(doc.created_at)}
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

<!-- ======================================================================= -->
<!-- SLIDE-OVER: Create / Edit HR Attachment                                  -->
<!-- ======================================================================= -->
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
      <h2 class="text-lg font-semibold text-neutral-900">{panelTitle}</h2>
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
      <form id="attachment-form" onsubmit={handleSave} class="space-y-5">
        <!-- Employee -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Employee (User ID)</span>
          <input
            type="number"
            bind:value={form.user}
            required
            placeholder="User ID"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
          />
          {#if fieldError("user")}<p class="mt-1 text-xs text-red-500">{fieldError("user")}</p>{/if}
        </label>

        <!-- Title -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
          <input
            type="text"
            bind:value={form.title}
            required
            placeholder="e.g. Passport Copy, Visa Document..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
        </label>

        <!-- Category -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Category</span>
          <input
            type="text"
            bind:value={form.category}
            placeholder="e.g. ID Document, Certificate, Medical..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("category")}<p class="mt-1 text-xs text-red-500">{fieldError("category")}</p>{/if}
        </label>

        <!-- File -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">File {#if isEditing}<span class="text-neutral-400 font-normal">(leave empty to keep current)</span>{/if}</span>
          <input
            type="file"
            onchange={handleFileSelect}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent file:mr-3 file:px-3 file:py-1 file:rounded file:border-0 file:text-xs file:font-medium file:bg-neutral-100 file:text-neutral-700 hover:file:bg-neutral-200"
          />
          {#if fieldError("file")}<p class="mt-1 text-xs text-red-500">{fieldError("file")}</p>{/if}
        </label>

        <!-- Description -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.description}
            rows="3"
            placeholder="Brief description of this attachment..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("description")}<p class="mt-1 text-xs text-red-500">{fieldError("description")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between px-6 py-4 border-t border-neutral-100 shrink-0">
      <div>
        {#if isEditing}
          <button
            type="button"
            onclick={handleDelete}
            class="text-sm text-red-500 hover:text-red-700 font-medium transition-colors"
          >
            Delete
          </button>
        {/if}
      </div>
      <div class="flex items-center gap-3">
        <button
          type="button"
          onclick={closeSlideOver}
          class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="attachment-form"
          disabled={saving}
          class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : isEditing ? "Update Attachment" : "Upload Attachment"}
        </button>
      </div>
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
