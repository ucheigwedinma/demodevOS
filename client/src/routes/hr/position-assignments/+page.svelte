<script lang="ts">
  import { untrack } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    HRPositionAssignment,
    HRPositionAssignmentListItem,
    HRPositionListItem,
    PaginatedResponse,
    ReportingLineUser,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let assignments = $state<HRPositionAssignmentListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let filterPosition = $state("");
  let filterPrimary = $state("");
  let filterActive = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let deleting = $state(false);
  let editingId = $state<number | null>(null);
  let fieldErrors = $state<Record<string, string[]>>({});

  let userOptions = $state<ReportingLineUser[]>([]);
  let positionOptions = $state<HRPositionListItem[]>([]);

  function todayIsoDate(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }

  let form = $state({
    user: "",
    position: "",
    start_date: todayIsoDate(),
    end_date: "",
    is_primary: true,
    is_active: true,
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    return new Date(`${dateStr}T00:00:00`).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function resetForm() {
    form = {
      user: "",
      position: "",
      start_date: todayIsoDate(),
      end_date: "",
      is_primary: true,
      is_active: true,
      notes: "",
    };
    editingId = null;
    fieldErrors = {};
  }

  async function fetchAssignments() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (filterPosition) params.position = filterPosition;
      if (filterPrimary) params.is_primary = filterPrimary;
      if (filterActive) params.is_active = filterActive;

      const response = await api.get<PaginatedResponse<HRPositionAssignmentListItem>>(
        "/hr/position-assignments/",
        params,
      );
      assignments = response.results;
      totalCount = response.count;
    } catch {
      assignments = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchFormOptions() {
    try {
      const [users, positionResponse] = await Promise.all([
        api.get<ReportingLineUser[]>("/hr/reporting-lines/"),
        api.get<PaginatedResponse<HRPositionListItem>>("/hr/positions/", {
          page_size: "200",
        }),
      ]);
      userOptions = [...users].sort((a, b) => a.full_name.localeCompare(b.full_name));
      positionOptions = positionResponse.results;
    } catch {
      userOptions = [];
      positionOptions = [];
    }
  }

  async function openCreate() {
    resetForm();
    await fetchFormOptions();
    showSlideOver = true;
  }

  async function openEdit(assignment: HRPositionAssignmentListItem) {
    resetForm();
    editingId = assignment.id;
    form.user = String(assignment.user);
    form.position = String(assignment.position);
    form.start_date = assignment.start_date;
    form.end_date = assignment.end_date ?? "";
    form.is_primary = assignment.is_primary;
    form.is_active = assignment.is_active;

    await fetchFormOptions();
    try {
      const detail = await api.get<HRPositionAssignment>(`/hr/position-assignments/${assignment.id}/`);
      form.notes = detail.notes ?? "";
    } catch {
      form.notes = "";
    }
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetForm();
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload = {
        user: form.user ? Number(form.user) : undefined,
        position: form.position ? Number(form.position) : undefined,
        start_date: form.start_date || undefined,
        end_date: form.end_date || null,
        is_primary: form.is_primary,
        is_active: form.is_active,
        notes: form.notes || "",
      };

      if (isEditing && editingId) {
        await api.patch(`/hr/position-assignments/${editingId}/`, payload);
        toast.success("Assignment updated");
      } else {
        await api.post("/hr/position-assignments/", payload);
        toast.success("Assignment created");
      }

      closeSlideOver();
      await fetchAssignments();
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        fieldErrors = error.fieldErrors;
      } else {
        toast.error("Failed to save assignment");
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!editingId) return;
    if (!confirm("Delete this position assignment?")) return;

    deleting = true;
    try {
      await api.delete(`/hr/position-assignments/${editingId}/`);
      toast.success("Assignment deleted");
      closeSlideOver();
      await fetchAssignments();
    } catch {
      toast.error("Failed to delete assignment");
    } finally {
      deleting = false;
    }
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchAssignments();
  }

  function assigneeName(userId: string): string {
    if (!userId) return "Select assignee";
    return userOptions.find((u) => String(u.id) === userId)?.full_name ?? `User #${userId}`;
  }

  function positionName(positionId: string): string {
    if (!positionId) return "Select position";
    const position = positionOptions.find((item) => String(item.id) === positionId);
    if (!position) return `Position #${positionId}`;
    return `${position.title}${position.code ? ` (${position.code})` : ""}`;
  }

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const ASSIGNMENT_SAMPLES = [
    {
      start_date: "2024-03-15", end_date: "", is_primary: true, is_active: true,
      notes: "Primary assignment — transferred from Project Alpha to manage Tower B construction phase.",
    },
    {
      start_date: "2023-09-01", end_date: "2025-08-31", is_primary: false, is_active: true,
      notes: "Secondary assignment — supporting procurement team during peak tendering season.",
    },
    {
      start_date: "2024-01-10", end_date: "", is_primary: true, is_active: true,
      notes: "New hire placement — assigned to Finance & Accounting for Q1 onboarding.",
    },
  ];
  let assignDevIdx = 0;
  function devFillAssignment() {
    const s = ASSIGNMENT_SAMPLES[assignDevIdx % ASSIGNMENT_SAMPLES.length];
    assignDevIdx++;
    form.user = userOptions.length > 0 ? String(userOptions[assignDevIdx % userOptions.length].id) : "";
    form.position = positionOptions.length > 0 ? String(positionOptions[assignDevIdx % positionOptions.length].id) : "";
    form.start_date = s.start_date;
    form.end_date = s.end_date;
    form.is_primary = s.is_primary;
    form.is_active = s.is_active;
    form.notes = s.notes;
  }

  $effect(() => {
    untrack(() => {
      fetchAssignments();
    });
  });

  $effect(() => {
    untrack(() => {
      fetchFormOptions();
    });
  });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex flex-wrap items-center justify-between gap-3 mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Position Assignments</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Assign people to roles with effective dates and primary designation.
      </p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Assignment
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <select
      value={filterPosition}
      onchange={(e) => {
        filterPosition = e.currentTarget.value;
        currentPage = 1;
        fetchAssignments();
      }}
      class="min-w-56 px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Positions</option>
      {#each positionOptions as position}
        <option value={String(position.id)}>
          {position.title}{position.code ? ` (${position.code})` : ""}
        </option>
      {/each}
    </select>

    <select
      value={filterPrimary}
      onchange={(e) => {
        filterPrimary = e.currentTarget.value;
        currentPage = 1;
        fetchAssignments();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Assignment Types</option>
      <option value="true">Primary</option>
      <option value="false">Secondary</option>
    </select>

    <select
      value={filterActive}
      onchange={(e) => {
        filterActive = e.currentTarget.value;
        currentPage = 1;
        fetchAssignments();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All States</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if assignments.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">No position assignments found for the selected filters.</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Assignee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Start Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">End Date</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Type</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">State</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each assignments as assignment}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(assignment)}>
              <td class="px-5 py-3.5">
                <p class="font-medium text-neutral-900">{assignment.user_name}</p>
              </td>
              <td class="px-5 py-3.5">
                <p class="text-neutral-700">{assignment.position_title}</p>
                <p class="font-mono text-xs text-neutral-400">{assignment.position_code}</p>
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{formatDate(assignment.start_date)}</td>
              <td class="px-5 py-3.5 text-neutral-600">{formatDate(assignment.end_date)}</td>
              <td class="px-5 py-3.5 text-center">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {assignment.is_primary ? 'bg-sky-100 text-sky-700' : 'bg-neutral-100 text-neutral-600'}"
                >
                  {assignment.is_primary ? "Primary" : "Secondary"}
                </span>
              </td>
              <td class="px-5 py-3.5 text-center">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {assignment.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}"
                >
                  {assignment.is_active ? "Active" : "Inactive"}
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} assignment{totalCount !== 1 ? "s" : ""}</span>
        <div class="flex items-center gap-1">
          <button
            onclick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &laquo;
          </button>
          {#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
            <button
              onclick={() => goToPage(page)}
              class="px-2.5 py-1 rounded text-sm {page === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}"
            >
              {page}
            </button>
          {/each}
          <button
            onclick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &raquo;
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>

{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button
      class="absolute inset-0 bg-black/30 backdrop-blur-sm"
      onclick={closeSlideOver}
      aria-label="Close"
    ></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Assignment" : "Create Assignment"}</h2>
        <button onclick={closeSlideOver} class="p-1 rounded hover:bg-neutral-100">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="assignment-user" class="block text-sm font-medium text-neutral-700 mb-1">
            Assignee <span class="text-red-500">*</span>
          </label>
          <select
            id="assignment-user"
            bind:value={form.user}
            class="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('user') ? 'border-red-400' : 'border-neutral-200'}"
          >
            <option value="">{assigneeName(form.user)}</option>
            {#each userOptions as user}
              <option value={String(user.id)}>{user.full_name}</option>
            {/each}
          </select>
          {#if fieldError("user")}
            <p class="text-xs text-red-500 mt-1">{fieldError("user")}</p>
          {/if}
        </div>

        <div>
          <label for="assignment-position" class="block text-sm font-medium text-neutral-700 mb-1">
            Position <span class="text-red-500">*</span>
          </label>
          <select
            id="assignment-position"
            bind:value={form.position}
            class="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('position') ? 'border-red-400' : 'border-neutral-200'}"
          >
            <option value="">{positionName(form.position)}</option>
            {#each positionOptions as position}
              <option value={String(position.id)}>
                {position.title}{position.code ? ` (${position.code})` : ""}
              </option>
            {/each}
          </select>
          {#if fieldError("position")}
            <p class="text-xs text-red-500 mt-1">{fieldError("position")}</p>
          {/if}
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="assignment-start" class="block text-sm font-medium text-neutral-700 mb-1">
              Start Date <span class="text-red-500">*</span>
            </label>
            <DateInput id="assignment-start" bind:value={form.start_date} />
            {#if fieldError("start_date")}
              <p class="text-xs text-red-500 mt-1">{fieldError("start_date")}</p>
            {/if}
          </div>
          <div>
            <label for="assignment-end" class="block text-sm font-medium text-neutral-700 mb-1">End Date</label>
            <DateInput id="assignment-end" bind:value={form.end_date} />
            {#if fieldError("end_date")}
              <p class="text-xs text-red-500 mt-1">{fieldError("end_date")}</p>
            {/if}
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <label class="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.is_primary} class="rounded border-neutral-300" />
            Primary assignment
          </label>
          <label class="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" />
            Active assignment
          </label>
        </div>

        <div>
          <label for="assignment-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea
            id="assignment-notes"
            bind:value={form.notes}
            rows={4}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
            placeholder="Optional context for this assignment"
          ></textarea>
          {#if fieldError("notes")}
            <p class="text-xs text-red-500 mt-1">{fieldError("notes")}</p>
          {/if}
        </div>
      </div>

      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillAssignment} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
        {/if}
        {#if isEditing}
          <button
            onclick={handleDelete}
            disabled={deleting}
            class="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-60 mr-auto"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        {/if}
        <button onclick={closeSlideOver} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">
          Cancel
        </button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
