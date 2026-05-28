<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import MemberRow from "$lib/components/teams/MemberRow.svelte";
  import UserPicker from "$lib/components/teams/UserPicker.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import ConfirmModal from "$lib/components/teams/ConfirmModal.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    UserDirectoryItem,
    WorkspaceTeamDetail,
    WorkspaceTeamMembership,
    WorkspaceTeamRole,
  } from "$lib/types";

  const teamId = $derived(Number($page.params.id));

  let team = $state<WorkspaceTeamDetail | null>(null);
  let members = $state<WorkspaceTeamMembership[]>([]);
  let myUserId = $state<number | null>(null);
  let loading = $state(true);
  let errorMessage = $state<string | null>(null);

  let roleFilter = $state<"all" | WorkspaceTeamRole>("all");
  let searchTerm = $state("");
  let pendingIds = $state<Set<number>>(new Set());

  let addOpen = $state(false);
  let pickedUsers = $state<UserDirectoryItem[]>([]);
  let addSaving = $state(false);

  // Confirm-remove modal
  let confirmRemove = $state<WorkspaceTeamMembership | null>(null);
  // Confirm-transfer modal
  let confirmTransfer = $state<WorkspaceTeamMembership | null>(null);
  let transferSaving = $state(false);

  let searchSeq = 0;
  let debounceHandle: ReturnType<typeof setTimeout> | null = null;

  async function loadAll() {
    loading = true;
    errorMessage = null;
    try {
      const params: Record<string, string> = {};
      if (roleFilter !== "all") params.role = roleFilter;
      const q = searchTerm.trim();
      if (q) params.q = q;

      const [t, m, me] = await Promise.all([
        api.get<WorkspaceTeamDetail>(`/workspace/teams/${teamId}/`),
        api.get<WorkspaceTeamMembership[]>(`/workspace/teams/${teamId}/members/`, params),
        api.get<{ id: number }>("/auth/me/"),
      ]);
      team = t;
      members = m;
      myUserId = me.id;
    } catch (err) {
      console.error("[/teams/[id]/members]", err);
      errorMessage = err instanceof Error ? err.message : i18n.t("workspace.teams.error.load");
    } finally {
      loading = false;
    }
  }

  async function refilter() {
    const seq = ++searchSeq;
    try {
      const params: Record<string, string> = {};
      if (roleFilter !== "all") params.role = roleFilter;
      const q = searchTerm.trim();
      if (q) params.q = q;
      const m = await api.get<WorkspaceTeamMembership[]>(
        `/workspace/teams/${teamId}/members/`,
        params,
      );
      if (seq !== searchSeq) return;
      members = m;
    } catch (err) {
      console.error("[/teams/[id]/members refilter]", err);
    }
  }

  function setRoleFilter(next: "all" | WorkspaceTeamRole) {
    if (roleFilter === next) return;
    roleFilter = next;
    refilter();
  }

  function onSearchInput(e: Event) {
    searchTerm = (e.target as HTMLInputElement).value;
    if (debounceHandle) clearTimeout(debounceHandle);
    debounceHandle = setTimeout(refilter, 250);
  }

  onMount(loadAll);

  const myRole = $derived(team?.my_role ?? null);
  const isOwnerOrAdmin = $derived(myRole === "owner" || myRole === "admin");

  // --- Optimistic mutations -------------------------------------------------

  async function changeRole(membership: WorkspaceTeamMembership, next: WorkspaceTeamRole) {
    const prev = membership.role;
    members = members.map((m) =>
      m.id === membership.id ? { ...m, role: next } : m,
    );
    pendingIds = new Set([...pendingIds, membership.id]);
    try {
      const updated = await api.patch<WorkspaceTeamMembership>(
        `/workspace/teams/${teamId}/members/${membership.user.id}/`,
        { role: next, if_unchanged_since: membership.updated_at },
      );
      members = members.map((m) => (m.id === membership.id ? updated : m));
    } catch (err) {
      console.error("[role change]", err);
      // Roll back
      members = members.map((m) =>
        m.id === membership.id ? { ...m, role: prev } : m,
      );
      if (err instanceof ApiError && err.status === 409) {
        toast.warning(i18n.t("workspace.teams.error.role_conflict"));
        await refilter();
      } else {
        toast.error(i18n.t("workspace.teams.error.role_change"));
      }
    } finally {
      const next = new Set(pendingIds);
      next.delete(membership.id);
      pendingIds = next;
    }
  }

  async function removeMember(membership: WorkspaceTeamMembership) {
    const snapshot = members;
    members = members.filter((m) => m.id !== membership.id);
    pendingIds = new Set([...pendingIds, membership.id]);
    try {
      await api.delete(`/workspace/teams/${teamId}/members/${membership.user.id}/`);
      toast.success(
        membership.user.id === myUserId
          ? i18n.t("workspace.teams.toast.left")
          : i18n.t("workspace.teams.toast.removed", { name: membership.user.name }),
      );
    } catch (err) {
      console.error("[remove member]", err);
      members = snapshot;
      toast.error(i18n.t("workspace.teams.error.remove"));
    } finally {
      const next = new Set(pendingIds);
      next.delete(membership.id);
      pendingIds = next;
      confirmRemove = null;
    }
  }

  async function addMembers() {
    if (!team || pickedUsers.length === 0) return;
    const targetTeamId = team.id;
    addSaving = true;
    const targets = [...pickedUsers];
    pickedUsers = [];
    try {
      await Promise.all(
        targets.map((u) =>
          api.post(`/workspace/teams/${targetTeamId}/members/`, {
            user_id: u.id,
            role: "member",
          }),
        ),
      );
      addOpen = false;
      toast.success(i18n.t("workspace.teams.toast.members_added"));
      await refilter();
    } catch (err) {
      console.error("[add members]", err);
      toast.error(i18n.t("workspace.teams.error.add"));
      pickedUsers = targets;
    } finally {
      addSaving = false;
    }
  }

  async function transferOwnership(target: WorkspaceTeamMembership) {
    if (!team) return;
    transferSaving = true;
    try {
      await api.post(`/workspace/teams/${team.id}/transfer/`, {
        new_owner_id: target.user.id,
      });
      toast.success(i18n.t("workspace.teams.toast.ownership_transferred", { name: target.user.name }));
      confirmTransfer = null;
      await loadAll();
    } catch (err) {
      console.error("[transfer]", err);
      toast.error(i18n.t("workspace.teams.error.transfer"));
    } finally {
      transferSaving = false;
    }
  }

  const existingMemberIds = $derived(members.map((m) => m.user.id));
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if errorMessage || !team}
  <DataStateBanner
    title={i18n.t("workspace.teams.error.load")}
    message={errorMessage ?? ""}
    onretry={loadAll}
  />
{:else}
  <div class="space-y-4">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.title")}</a>
      <span class="text-neutral-300"> › </span>
      <a href={`/teams/${team.id}`} class="hover:text-blue-700 normal-case tracking-normal">{team.name}</a>
      <span class="text-neutral-300"> › </span>
      <span class="text-neutral-700 normal-case tracking-normal font-semibold">{i18n.t("workspace.teams.members_panel.title")}</span>
    </p>

    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.teams.members_page.title", { name: team.name })}
      </h1>
      {#if isOwnerOrAdmin}
        <button
          type="button"
          onclick={() => (addOpen = true)}
          class="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          {i18n.t("workspace.teams.action.add_member")}
        </button>
      {/if}
    </div>

    <!-- Filter shelf -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex flex-wrap gap-2">
          {#each [
            { key: "all", labelKey: "workspace.teams.role_filter.all" },
            { key: "owner", labelKey: "workspace.teams.role.owner" },
            { key: "admin", labelKey: "workspace.teams.role.admin" },
            { key: "member", labelKey: "workspace.teams.role.member" },
            { key: "guest", labelKey: "workspace.teams.role.guest" },
          ] as opt (opt.key)}
            <button
              type="button"
              onclick={() => setRoleFilter(opt.key as "all" | WorkspaceTeamRole)}
              class="rounded-full px-3 py-1.5 text-xs font-semibold transition {roleFilter === opt.key
                ? 'bg-neutral-900 text-white'
                : 'border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
            >
              {i18n.t(opt.labelKey)}
            </button>
          {/each}
        </div>
        <div class="relative">
          <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-4.35-4.35M16.5 10.5a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z" />
            </svg>
          </span>
          <input
            type="search"
            value={searchTerm}
            oninput={onSearchInput}
            placeholder={i18n.t("workspace.teams.members_page.search_placeholder")}
            class="w-56 rounded-xl border border-neutral-200 bg-neutral-50 py-2 pl-9 pr-3 text-xs text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
        </div>
      </div>
    </section>

    <!-- Members list -->
    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      {#if members.length === 0}
        <p class="py-12 text-center text-sm text-neutral-500">
          {i18n.t("workspace.teams.members_page.empty")}
        </p>
      {:else}
        <div class="space-y-2">
          {#each members as membership (membership.id)}
            <MemberRow
              {membership}
              {myRole}
              myUserId={myUserId ?? undefined}
              pending={pendingIds.has(membership.id)}
              onRoleChange={(next) => changeRole(membership, next)}
              onRemove={() => (confirmRemove = membership)}
              onTransfer={() => (confirmTransfer = membership)}
            />
          {/each}
        </div>
      {/if}
    </section>
  </div>

  <!-- Add members modal -->
  <Modal open={addOpen} onclose={() => (addOpen = false)} title={i18n.t("workspace.teams.add_modal.title")}>
    <div class="space-y-4">
      <p class="text-sm text-neutral-600">{i18n.t("workspace.teams.add_modal.helper")}</p>
      <UserPicker multiple bind:selected={pickedUsers} excludeIds={existingMemberIds} />
      <div class="flex items-center justify-end gap-2 pt-2">
        <button
          type="button"
          onclick={() => (addOpen = false)}
          class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
        >
          {i18n.t("workspace.teams.confirm.cancel")}
        </button>
        <button
          type="button"
          onclick={addMembers}
          disabled={addSaving || pickedUsers.length === 0}
          class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
        >
          {addSaving
            ? i18n.t("workspace.teams.add_modal.adding")
            : i18n.t("workspace.teams.add_modal.add", { count: pickedUsers.length })}
        </button>
      </div>
    </div>
  </Modal>

  <!-- Confirm remove -->
  <ConfirmModal
    open={confirmRemove !== null}
    onclose={() => (confirmRemove = null)}
    onconfirm={() => confirmRemove && removeMember(confirmRemove)}
    title={confirmRemove?.user.id === myUserId
      ? i18n.t("workspace.teams.confirm.leave_title")
      : i18n.t("workspace.teams.confirm.remove_title")}
    message={confirmRemove?.user.id === myUserId
      ? i18n.t("workspace.teams.confirm.leave_message", { team: team.name })
      : i18n.t("workspace.teams.confirm.remove_message", { name: confirmRemove?.user.name ?? "" })}
    confirmLabel={confirmRemove?.user.id === myUserId
      ? i18n.t("workspace.teams.action.leave")
      : i18n.t("workspace.teams.action.remove")}
    destructive
    busy={confirmRemove !== null && pendingIds.has(confirmRemove.id)}
  />

  <!-- Confirm transfer -->
  <ConfirmModal
    open={confirmTransfer !== null}
    onclose={() => (confirmTransfer = null)}
    onconfirm={() => confirmTransfer && transferOwnership(confirmTransfer)}
    title={i18n.t("workspace.teams.confirm.transfer_title")}
    message={i18n.t("workspace.teams.confirm.transfer_message", { name: confirmTransfer?.user.name ?? "" })}
    confirmLabel={i18n.t("workspace.teams.action.transfer")}
    busy={transferSaving}
  />
{/if}
