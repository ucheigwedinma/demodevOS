<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import TeamAvatar from "$lib/components/teams/TeamAvatar.svelte";
  import PurposeChip from "$lib/components/teams/PurposeChip.svelte";
  import VisibilityChip from "$lib/components/teams/VisibilityChip.svelte";
  import MemberRow from "$lib/components/teams/MemberRow.svelte";
  import Toggle from "$lib/components/teams/Toggle.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type { WorkspaceTeamDetail, WorkspaceTeamMembership, WorkspaceTeamRole } from "$lib/types";

  const teamId = $derived(Number($page.params.id));

  let team = $state<WorkspaceTeamDetail | null>(null);
  let members = $state<WorkspaceTeamMembership[]>([]);
  let myUserId = $state<number | null>(null);
  let loading = $state(true);
  let notFound = $state(false);
  let errorMessage = $state<string | null>(null);
  let saving = $state(false);

  async function loadAll() {
    loading = true;
    notFound = false;
    errorMessage = null;
    try {
      const [t, m, me] = await Promise.all([
        api.get<WorkspaceTeamDetail>(`/workspace/teams/${teamId}/`),
        api.get<WorkspaceTeamMembership[]>(`/workspace/teams/${teamId}/members/`),
        api.get<{ id: number }>("/auth/me/"),
      ]);
      team = t;
      members = m;
      myUserId = me.id;
    } catch (err) {
      console.error("[/teams/[id]]", err);
      if (err instanceof ApiError && err.status === 404) {
        // Per UI spec: never reveal whether a secret team exists. Render
        // the same "not found" treatment for any 404 (true 404 OR access
        // denial on a secret team).
        notFound = true;
      } else {
        errorMessage = err instanceof Error ? err.message : i18n.t("workspace.teams.error.load");
      }
    } finally {
      loading = false;
    }
  }

  onMount(loadAll);

  const myRole = $derived(team?.my_role ?? null);
  const isMember = $derived(myRole !== null);
  const isOwner = $derived(myRole === "owner");
  const isOwnerOrAdmin = $derived(myRole === "owner" || myRole === "admin");
  const myMembership = $derived(
    myUserId === null ? null : members.find((m) => m.user.id === myUserId) ?? null,
  );
  const visibleMembers = $derived(members.slice(0, 8));
  const moreMembersCount = $derived(Math.max(0, members.length - 8));

  async function joinTeam() {
    if (!team) return;
    saving = true;
    try {
      await api.post(`/workspace/teams/${team.id}/join/`, {});
      toast.success(i18n.t("workspace.teams.action.joined_toast"));
      await loadAll();
    } catch (err) {
      console.error("[join]", err);
      toast.error(i18n.t("workspace.teams.error.join"));
    } finally {
      saving = false;
    }
  }

  async function requestJoin() {
    if (!team) return;
    saving = true;
    try {
      await api.post(`/workspace/teams/${team.id}/request-join/`, {});
      toast.success(i18n.t("workspace.teams.action.request_submitted"));
    } catch (err) {
      console.error("[request-join]", err);
      toast.error(i18n.t("workspace.teams.error.request_join"));
    } finally {
      saving = false;
    }
  }

  async function toggleNotifyRealtime(next: boolean) {
    if (!team) return;
    try {
      await api.patch(`/workspace/teams/${team.id}/notifications/`, { notify_realtime: next });
      if (myMembership) myMembership.notify_realtime = next;
    } catch (err) {
      console.error("[notify_realtime]", err);
      toast.error(i18n.t("workspace.teams.error.save_prefs"));
      // Roll back the toggle visually by reloading members.
      await loadAll();
    }
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound}
  <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-16 text-center">
    <p class="text-3xl">🔎</p>
    <h2 class="mt-3 text-lg font-semibold text-neutral-900">{i18n.t("workspace.teams.not_found.title")}</h2>
    <p class="mt-1 text-sm text-neutral-500">{i18n.t("workspace.teams.not_found.helper")}</p>
    <a href="/teams" class="mt-4 inline-block text-xs font-semibold text-neutral-700 underline hover:text-neutral-900">
      {i18n.t("workspace.teams.not_found.back")}
    </a>
  </div>
{:else if errorMessage}
  <DataStateBanner
    title={i18n.t("workspace.teams.error.load")}
    message={errorMessage}
    onretry={loadAll}
  />
{:else if team}
  <div class="space-y-4">
    <!-- Breadcrumb -->
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.title")}</a>
      <span class="text-neutral-300"> › </span>
      <span class="text-neutral-700 normal-case tracking-normal font-semibold">{team.name}</span>
    </p>

    <!-- Header card -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="flex items-start gap-4">
          <TeamAvatar emoji={team.emoji} color={team.color} size="lg" decorative />
          <div class="min-w-0 flex-1">
            <h1 class="text-2xl font-bold tracking-wide text-neutral-800">{team.name}</h1>
            {#if team.description}
              <p class="mt-1 max-w-2xl text-sm text-neutral-500">{team.description}</p>
            {/if}
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <PurposeChip purpose={team.purpose} />
              <VisibilityChip visibility={team.visibility} />
              {#if team.is_archived}
                <span class="rounded-full bg-neutral-100 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                  {i18n.t("workspace.teams.archived_badge")}
                </span>
              {/if}
              {#if team.is_orphaned}
                <span class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-700">
                  {i18n.t("workspace.teams.orphaned_badge")}
                </span>
              {/if}
            </div>
            {#if team.created_by}
              <p class="mt-2 text-xs text-neutral-400">
                {i18n.t("workspace.teams.created_by", { name: team.created_by.name })}
              </p>
            {/if}
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          {#if !isMember}
            {#if team.visibility === "public"}
              <button
                type="button"
                onclick={joinTeam}
                disabled={saving}
                class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800 disabled:opacity-60"
              >
                {i18n.t("workspace.teams.action.join")}
              </button>
            {:else if team.visibility === "private"}
              <button
                type="button"
                onclick={requestJoin}
                disabled={saving}
                class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400 disabled:opacity-60"
              >
                {i18n.t("workspace.teams.action.request_join")}
              </button>
            {/if}
          {:else}
            <a
              href={`/teams/${team.id}/settings`}
              class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
            >
              ✓ {i18n.t("workspace.teams.action.joined")}
            </a>
            {#if isOwnerOrAdmin}
              <a
                href={`/teams/${team.id}/edit`}
                class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
              >
                {i18n.t("workspace.teams.action.edit")}
              </a>
            {/if}
          {/if}
        </div>
      </div>
    </section>

    <!-- Two-column grid: members + side panels -->
    <div class="grid gap-4 lg:grid-cols-3">
      <!-- Members panel -->
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 lg:col-span-2">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
              {i18n.t("workspace.teams.members_panel.title")}
            </h2>
            <p class="text-xs text-neutral-500">
              {i18n.t("workspace.teams.member_count", { count: team.members_count })}
            </p>
          </div>
          {#if isOwnerOrAdmin}
            <a
              href={`/teams/${team.id}/members`}
              class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
            >
              {i18n.t("workspace.teams.action.add_member")}
            </a>
          {/if}
        </div>

        {#if members.length === 0}
          <p class="py-8 text-center text-sm text-neutral-500">
            {i18n.t("workspace.teams.members_panel.empty")}
          </p>
        {:else}
          <div class="space-y-2">
            {#each visibleMembers as membership (membership.id)}
              <MemberRow {membership} {myRole} myUserId={myUserId ?? undefined} />
            {/each}
          </div>
          {#if moreMembersCount > 0}
            <a
              href={`/teams/${team.id}/members`}
              class="mt-3 block text-center text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
            >
              {i18n.t("workspace.teams.members_panel.see_all", { count: moreMembersCount })}
            </a>
          {/if}
        {/if}
      </section>

      <!-- Side panels -->
      <div class="space-y-4">
        <!-- Linked work -->
        <section class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
            {i18n.t("workspace.teams.linked_work.title")}
          </h2>
          <p class="mt-3 text-3xl font-bold text-neutral-900 tabular-nums">
            {team.open_tickets_count}
          </p>
          <p class="text-xs text-neutral-500">{i18n.t("workspace.teams.linked_work.open_tickets")}</p>
          {#if team.open_tickets_count > 0}
            <a
              href={`/support-desk/tickets?team=${team.id}`}
              class="mt-3 inline-block text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
            >
              {i18n.t("workspace.teams.linked_work.view_tickets")}
            </a>
          {:else}
            <p class="mt-3 text-xs italic text-neutral-400">
              {i18n.t("workspace.teams.linked_work.empty")}
            </p>
          {/if}
        </section>

        <!-- Notifications quick toggles -->
        {#if myMembership}
          <section class="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
              {i18n.t("workspace.teams.notifications.title")}
            </h2>
            <div class="mt-3 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-700">{i18n.t("workspace.teams.notifications.realtime")}</span>
                <Toggle
                  checked={myMembership.notify_realtime}
                  onToggle={(next) => toggleNotifyRealtime(next)}
                  label={i18n.t("workspace.teams.notifications.realtime")}
                />
              </div>
              <a
                href={`/teams/${team.id}/settings`}
                class="block text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
              >
                {i18n.t("workspace.teams.notifications.manage")}
              </a>
            </div>
          </section>
        {/if}

        <!-- Project (only when linked) -->
        {#if team.purpose === "project"}
          <section class="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
              {i18n.t("workspace.teams.project_panel.title")}
            </h2>
            {#if team.project_name}
              <p class="mt-3 text-sm font-semibold text-neutral-900">📁 {team.project_name}</p>
              <a
                href={`/projects/${team.project}`}
                class="mt-2 inline-block text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
              >
                {i18n.t("workspace.teams.project_panel.open")}
              </a>
            {:else}
              <p class="mt-3 text-xs italic text-neutral-400">
                {i18n.t("workspace.teams.project_panel.removed")}
              </p>
            {/if}
          </section>
        {/if}
      </div>
    </div>
  </div>
{/if}
