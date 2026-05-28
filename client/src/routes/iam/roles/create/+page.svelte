<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse, RoleDetail } from "$lib/types";

  let roles = $state<RoleListItem[]>([]);
  let loadingRoles = $state(true);
  let saving = $state(false);

  let form = $state({
    name: "",
    description: "",
    clone_from_id: null as number | null,
  });

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const ROLE_SAMPLES = [
    { name: "Project Manager", description: "Full access to project dashboards, budgets, timelines, and team assignments. Can approve change orders and sign off on milestones." },
    { name: "Sales Agent", description: "View and manage leads, client interactions, and unit reservations. Can generate SOA and payment schedules but cannot modify pricing." },
    { name: "Finance Controller", description: "Access to all financial modules including journals, chart of accounts, SPVs, and bank reconciliations. Can approve payments up to authority limit." },
  ];
  let roleDevIdx = 0;
  function devFill() {
    const s = ROLE_SAMPLES[roleDevIdx % ROLE_SAMPLES.length];
    roleDevIdx++;
    form.name = s.name;
    form.description = s.description;
  }

  async function loadRoles() {
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", { page_size: "200", ordering: "name" });
      roles = res.results;
    } catch {
      // Cloning is optional — if it fails, the page still works
    } finally {
      loadingRoles = false;
    }
  }

  $effect(() => {
    loadRoles();
  });

  async function handleCreate() {
    if (!form.name.trim()) {
      toast.error("Validation", "Role name is required.");
      return;
    }
    saving = true;
    try {
      const created = await api.post<{ id: number; name: string }>("/settings/roles/", {
        name: form.name.trim(),
        description: form.description.trim(),
      });

      // Optionally clone permissions from another role
      if (form.clone_from_id !== null) {
        try {
          const source = await api.get<RoleDetail>(`/settings/roles/${form.clone_from_id}/`);
          const permissions = source.permissions.map((p) => ({
            sub_module: p.sub_module,
            action: p.action,
            granted: true,
          }));
          if (permissions.length) {
            await api.put(`/settings/roles/${created.id}/permissions/`, { permissions });
          }
        } catch {
          // Don't block — role is created, just warn
          toast.error("Partial", "Role created, but permission cloning failed.");
        }
      }

      toast.success("Created", `Role "${created.name}" created.`);
      goto(`/iam/roles/${created.id}/permissions`);
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form for errors.");
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="max-w-2xl space-y-6">
  <div>
    <a href="/iam/roles" class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-3">
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to Roles
    </a>
    <h1 class="text-2xl font-bold text-neutral-900">Create Role</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Define a new role and optionally clone permissions from an existing one.
      You'll be taken to the permission matrix after save.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-6 space-y-5">
    <div>
      <label for="role-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
      <input id="role-name" type="text" bind:value={form.name} placeholder="e.g. Marketing Manager"
        class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
    </div>

    <div>
      <label for="role-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
      <textarea id="role-desc" rows="4" bind:value={form.description}
        placeholder="What can this role do? Who should it be assigned to?"
        class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"></textarea>
    </div>

    <div>
      <label for="role-clone" class="block text-sm font-medium text-neutral-700 mb-1.5">
        Clone permissions from
        <span class="text-xs font-normal text-neutral-500 ml-1">(optional)</span>
      </label>
      <select id="role-clone" bind:value={form.clone_from_id}
        class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
        <option value={null}>— Start with empty permissions —</option>
        {#if loadingRoles}
          <option disabled>Loading roles…</option>
        {:else}
          {#each roles as r}
            <option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>
          {/each}
        {/if}
      </select>
      <p class="mt-1.5 text-xs text-neutral-500">
        If selected, the new role will start with the same permission matrix as the chosen role.
        You can adjust it on the next screen.
      </p>
    </div>

    <div class="rounded-lg bg-neutral-50 border border-neutral-200 p-4 text-xs text-neutral-600">
      <p class="font-medium text-neutral-700 mb-1">What happens next</p>
      <p>
        After save, you'll land on the permission matrix for the new role where you can grant or revoke
        granular access by module, sub-module, and action.
      </p>
    </div>
  </div>

  <div class="flex items-center gap-3">
    {#if isDev}
      <button onclick={devFill}
        class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">
        Dev Fill
      </button>
    {/if}
    <a href="/iam/roles"
      class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors {isDev ? '' : 'ml-auto'}">
      Cancel
    </a>
    <button onclick={handleCreate} disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors disabled:opacity-60">
      {saving ? "Creating..." : "Create role"}
    </button>
  </div>
</div>
