<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ContactDirectoryItem } from "$lib/types";

  // --- State ---
  let contacts = $state<ContactDirectoryItem[]>([]);
  let loading = $state(true);
  let search = $state("");

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      fetchContacts();
    }, 300);
  }

  // --- Data Fetching ---
  async function fetchContacts() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;

      const res = await api.get<ContactDirectoryItem[]>(
        "/hr/contact-directory/",
        params,
      );
      contacts = res;
    } catch (err) {
      contacts = [];
      if (err instanceof ApiError) {
        toast.error("Error", "Could not load contact directory");
      } else {
        toast.error("Something went wrong", "Please try again");
      }
    } finally {
      loading = false;
    }
  }

  // --- Initialize ---
  $effect(() => {
    fetchContacts();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Contact Information</h1>
    <p class="mt-1 text-sm text-neutral-500">Employee contact directory</p>
  </div>

  <!-- Search -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
      <input
        type="text"
        placeholder="Search by name, department, email..."
        value={search}
        oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
        class="w-full max-w-md px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </label>
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
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No contacts found</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Phone</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Location</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each contacts as contact}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-sm font-medium text-neutral-900">{contact.full_name}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{contact.department_name ?? "\u2014"}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{contact.phone || "\u2014"}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {#if contact.email}
                    <a href="mailto:{contact.email}" class="hover:underline">{contact.email}</a>
                  {:else}
                    {"\u2014"}
                  {/if}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">{contact.office_location || "\u2014"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Result count -->
      <div class="border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          {contacts.length} {contacts.length === 1 ? "contact" : "contacts"} found
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
