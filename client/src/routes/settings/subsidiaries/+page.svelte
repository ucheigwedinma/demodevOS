<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { SubsidiaryListItem, Subsidiary } from "$lib/types";

  let loading = $state(true);
  let subsidiaries = $state<SubsidiaryListItem[]>([]);
  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let deleting = $state<number | null>(null);

  let form = $state({
    name: "",
    legal_name: "",
    registration_number: "",
    tax_id: "",
    relationship_type: "subsidiary" as Subsidiary["relationship_type"],
    status: "active" as Subsidiary["status"],
    address: "",
    city: "",
    country: "",
    contact_email: "",
    contact_phone: "",
    notes: "",
  });

  const RELATIONSHIP_TYPES = [
    { value: "subsidiary", label: "Subsidiary" },
    { value: "branch", label: "Branch Office" },
    { value: "joint_venture", label: "Joint Venture" },
    { value: "associate", label: "Associate Company" },
  ];

  const STATUS_OPTIONS = [
    { value: "active", label: "Active" },
    { value: "dormant", label: "Dormant" },
    { value: "dissolved", label: "Dissolved" },
  ];

  async function loadSubsidiaries() {
    try {
      const data = await api.get<SubsidiaryListItem[]>("/settings/subsidiaries/");
      subsidiaries = data;
    } catch {
      toast.error("Load failed", "Could not load subsidiaries.");
    } finally {
      loading = false;
    }
  }

  function openAdd() {
    editingId = null;
    form = {
      name: "",
      legal_name: "",
      registration_number: "",
      tax_id: "",
      relationship_type: "subsidiary",
      status: "active",
      address: "",
      city: "",
      country: "",
      contact_email: "",
      contact_phone: "",
      notes: "",
    };
    showModal = true;
  }

  async function openEdit(id: number) {
    try {
      const data = await api.get<Subsidiary>(`/settings/subsidiaries/${id}/`);
      editingId = id;
      form = {
        name: data.name,
        legal_name: data.legal_name,
        registration_number: data.registration_number,
        tax_id: data.tax_id,
        relationship_type: data.relationship_type,
        status: data.status,
        address: data.address,
        city: data.city,
        country: data.country,
        contact_email: data.contact_email,
        contact_phone: data.contact_phone,
        notes: data.notes,
      };
      showModal = true;
    } catch {
      toast.error("Error", "Could not load subsidiary details.");
    }
  }

  async function handleSave() {
    if (!form.name.trim()) {
      toast.error("Validation", "Name is required.");
      return;
    }
    saving = true;
    try {
      if (editingId) {
        await api.patch(`/settings/subsidiaries/${editingId}/`, form);
        toast.success("Updated", "Subsidiary updated successfully.");
      } else {
        await api.post("/settings/subsidiaries/", form);
        toast.success("Created", "Subsidiary created successfully.");
      }
      showModal = false;
      await loadSubsidiaries();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form for errors.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete(id: number) {
    deleting = id;
    try {
      await api.delete(`/settings/subsidiaries/${id}/`);
      toast.success("Deleted", "Subsidiary removed.");
      await loadSubsidiaries();
    } catch {
      toast.error("Delete failed", "Could not delete subsidiary.");
    } finally {
      deleting = null;
    }
  }

  function statusColor(status: string): string {
    switch (status) {
      case "active": return "bg-emerald-50 text-emerald-700";
      case "dormant": return "bg-amber-50 text-amber-700";
      case "dissolved": return "bg-red-50 text-red-700";
      default: return "bg-neutral-100 text-neutral-600";
    }
  }

  function typeLabel(type: string): string {
    return RELATIONSHIP_TYPES.find((t) => t.value === type)?.label ?? type;
  }

  $effect(() => {
    loadSubsidiaries();
  });
</script>

<!-- Header -->
<div class="flex items-center justify-between mb-8">
  <div>
    <h2 class="text-xl font-bold text-neutral-800">Subsidiaries</h2>
    <p class="mt-1 text-sm text-neutral-500">Manage subsidiary companies and related entities.</p>
  </div>
  <button
    onclick={openAdd}
    class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
  >
    Add Subsidiary
  </button>
</div>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else if subsidiaries.length === 0}
  <!-- Empty State -->
  <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
    <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
      <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
      </svg>
    </div>
    <h3 class="text-sm font-semibold text-neutral-800">No subsidiaries yet</h3>
    <p class="mt-1.5 text-sm text-neutral-500">Add your first subsidiary or related entity.</p>
    <button onclick={openAdd} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">
      Add Subsidiary
    </button>
  </div>
{:else}
  <!-- Table -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-neutral-200 bg-neutral-50">
          <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Name</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Type</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Status</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider">Location</th>
          <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wider">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-100">
        {#each subsidiaries as sub}
          <tr class="hover:bg-neutral-50 transition-colors">
            <td class="px-5 py-4 font-medium text-neutral-800">{sub.name}</td>
            <td class="px-5 py-4 text-neutral-600">{typeLabel(sub.relationship_type)}</td>
            <td class="px-5 py-4">
              <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize {statusColor(sub.status)}">
                {sub.status}
              </span>
            </td>
            <td class="px-5 py-4 text-neutral-600">
              {[sub.city, sub.country].filter(Boolean).join(", ") || "—"}
            </td>
            <td class="px-5 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <button onclick={() => openEdit(sub.id)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">
                  Edit
                </button>
                <button
                  onclick={() => handleDelete(sub.id)}
                  disabled={deleting === sub.id}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  {deleting === sub.id ? "..." : "Delete"}
                </button>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<!-- Add/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6">
        <h2 class="text-lg font-bold text-neutral-800 mb-6">
          {editingId ? "Edit Subsidiary" : "Add Subsidiary"}
        </h2>

        <div class="space-y-4">
          <div>
            <label for="sub-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
            <input id="sub-name" type="text" bind:value={form.name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="sub-type" class="block text-sm font-medium text-neutral-700 mb-1.5">Relationship Type</label>
              <select id="sub-type" bind:value={form.relationship_type} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow">
                {#each RELATIONSHIP_TYPES as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="sub-status" class="block text-sm font-medium text-neutral-700 mb-1.5">Status</label>
              <select id="sub-status" bind:value={form.status} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow">
                {#each STATUS_OPTIONS as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
          </div>

          <div>
            <label for="sub-legal" class="block text-sm font-medium text-neutral-700 mb-1.5">Legal Name</label>
            <input id="sub-legal" type="text" bind:value={form.legal_name} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="sub-reg" class="block text-sm font-medium text-neutral-700 mb-1.5">Registration No.</label>
              <input id="sub-reg" type="text" bind:value={form.registration_number} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
            <div>
              <label for="sub-tax" class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID</label>
              <input id="sub-tax" type="text" bind:value={form.tax_id} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
          </div>

          <div>
            <label for="sub-address" class="block text-sm font-medium text-neutral-700 mb-1.5">Address</label>
            <textarea id="sub-address" rows="2" bind:value={form.address} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"></textarea>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="sub-city" class="block text-sm font-medium text-neutral-700 mb-1.5">City</label>
              <input id="sub-city" type="text" bind:value={form.city} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
            <div>
              <label for="sub-country" class="block text-sm font-medium text-neutral-700 mb-1.5">Country</label>
              <input id="sub-country" type="text" bind:value={form.country} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="sub-email" class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Email</label>
              <input id="sub-email" type="email" bind:value={form.contact_email} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
            <div>
              <label for="sub-phone" class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Phone</label>
              <input id="sub-phone" type="tel" bind:value={form.contact_phone} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow" />
            </div>
          </div>

          <div>
            <label for="sub-notes" class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</label>
            <textarea id="sub-notes" rows="2" bind:value={form.notes} class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"></textarea>
          </div>
        </div>

        <div class="mt-7 flex items-center justify-end gap-3">
          <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
            Cancel
          </button>
          <button onclick={handleSave} disabled={saving} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">
            {saving ? "Saving..." : editingId ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
