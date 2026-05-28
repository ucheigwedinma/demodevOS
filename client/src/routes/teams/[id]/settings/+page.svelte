<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import Toggle from "$lib/components/teams/Toggle.svelte";
  import UserPicker from "$lib/components/teams/UserPicker.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import ConfirmModal from "$lib/components/teams/ConfirmModal.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    UserDirectoryItem,
    WorkspaceDigestFrequency,
    WorkspaceTeamDetail,
    WorkspaceTeamMembership,
  } from "$lib/types";

  const teamId = $derived(Number($page.params.id));

  let team = $state<WorkspaceTeamDetail | null>(null);
  let members = $state<WorkspaceTeamMembership[]>([]);
  let myUserId = $state<number | null>(null);
  let loading = $state(true);
  let errorMessage = $state<string | null>(null);

  let archiveOpen = $state(false);
  let archiveSaving = $state(false);

  let transferOpen = $state(false);
  let transferTarget = $state<UserDirectoryItem | null>(null);
  let transferSaving = $state(false);

  let deleteOpen = $state(false);
  let deleteSaving = $state(false);

  async function loadAll() {
    loading = true;
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
      console.error("[/teams/[id]/settings]", err);
      errorMessage = err instanceof Error ? err.message : i18n.t("workspace.teams.error.load");
    } finally {
      loading = false;
    }
  }

  onMount(loadAll);

  const myRole = $derived(team?.my_role ?? null);
  const isOwner = $derived(myRole === "owner");
  const isOwnerOrAdmin = $derived(myRole === "owner" || myRole === "admin");
  const myMembership = $derived(
    myUserId === null ? null : members.find((m) => m.user.id === myUserId) ?? null,
  );
  const memberOptionUsers = $derived(
    members
      .filter((m) => m.user.id !== myUserId && m.role !== "owner")
      .map((m): UserDirectoryItem => ({
        id: m.user.id,
        profile_id: m.user.id,
        full_name: m.user.name,
        email: m.user.email,
        phone: "",
        job_title: "",
        department_name: "",
        role_name: "",
        user_status: "active",
        user_status_display: "Active",
        last_login: null,
        mfa_enabled: false,
        identity_type: "internal",
        identity_type_display: "Internal",
        partner_type: "",
        partner_type_display: "",
        profile_photo: null,
        date_joined: m.joined_at,
      })),
  );

  // --- Notifications --------------------------------------------------------

  async function saveNotifyRealtime(next: boolean) {
    if (!team || !myMembership) return;
    try {
      await api.patch(`/workspace/teams/${team.id}/notifications/`, { notify_realtime: next });
      myMembership.notify_realtime = next;
    } catch (err) {
      console.error("[notify]", err);
      toast.error(i18n.t("workspace.teams.error.save_prefs"));
      await loadAll();
    }
  }

  async function saveDigestFrequency(next: WorkspaceDigestFrequency) {
    if (!team || !myMembership) return;
    const prev = myMembership.digest_frequency;
    myMembership.digest_frequency = next;
    try {
      await api.patch(`/workspace/teams/${team.id}/notifications/`, {
        digest_frequency: next,
      });
    } catch (err) {
      console.error("[digest]", err);
      myMembership.digest_frequency = prev;
      toast.error(i18n.t("workspace.teams.error.save_prefs"));
    }
  }

  // --- Archive --------------------------------------------------------------

  async function toggleArchive() {
    if (!team) return;
    archiveSaving = true;
    try {
      await api.post<WorkspaceTeamDetail>(`/workspace/teams/${team.id}/archive/`, {});
      toast.success(
        team.is_archived
          ? i18n.t("workspace.teams.toast.unarchived")
          : i18n.t("workspace.teams.toast.archived"),
      );
      archiveOpen = false;
      await loadAll();
    } catch (err) {
      console.error("[archive]", err);
      toast.error(i18n.t("workspace.teams.error.archive"));
    } finally {
      archiveSaving = false;
    }
  }

  // --- Transfer -------------------------------------------------------------

  async function transferOwnership() {
    if (!team || !transferTarget) return;
    transferSaving = true;
    try {
      await api.post(`/workspace/teams/${team.id}/transfer/`, {
        new_owner_id: transferTarget.id,
      });
      toast.success(
        i18n.t("workspace.teams.toast.ownership_transferred", { name: transferTarget.full_name }),
      );
      transferOpen = false;
      transferTarget = null;
      await loadAll();
    } catch (err) {
      console.error("[transfer]", err);
      toast.error(i18n.t("workspace.teams.error.transfer"));
    } finally {
      transferSaving = false;
    }
  }

  // --- Hard delete ---------------------------------------------------------

  async function hardDelete() {
    if (!team) return;
    deleteSaving = true;
    try {
      await api.delete(`/workspace/teams/${team.id}/`);
      toast.success(i18n.t("workspace.teams.toast.deleted"));
      await goto("/teams");
    } catch (err) {
      console.error("[delete]", err);
      toast.error(i18n.t("workspace.teams.error.delete"));
    } finally {
      deleteSaving = false;
    }
  }
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
  <div class="mx-auto max-w-3xl space-y-4">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.title")}</a>
      <span class="text-neutral-300"> › </span>
      <a href={`/teams/${team.id}`} class="hover:text-blue-700 normal-case tracking-normal">{team.name}</a>
      <span class="text-neutral-300"> › </span>
      <span class="text-neutral-700 normal-case tracking-normal font-semibold">{i18n.t("workspace.teams.settings.title")}</span>
    </p>

    <!-- My notification prefs -->
    {#if myMembership}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-5">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
            {i18n.t("workspace.teams.settings.my_notifications")}
          </h2>
        </div>

        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-neutral-900">
              {i18n.t("workspace.teams.settings.realtime_label")}
            </p>
            <p class="text-xs text-neutral-500">{i18n.t("workspace.teams.settings.realtime_helper")}</p>
          </div>
          <Toggle
            checked={myMembership.notify_realtime}
            onToggle={(next) => saveNotifyRealtime(next)}
            label={i18n.t("workspace.teams.settings.realtime_label")}
          />
        </div>

        <div class="space-y-2">
          <p class="text-sm font-medium text-neutral-900">
            {i18n.t("workspace.teams.settings.digest_label")}
          </p>
          <div class="flex flex-wrap gap-2">
            {#each [
              { key: "daily", labelKey: "workspace.teams.settings.digest.daily" },
              { key: "weekly", labelKey: "workspace.teams.settings.digest.weekly" },
              { key: "off", labelKey: "workspace.teams.settings.digest.off" },
            ] as opt (opt.key)}
              <button
                type="button"
                onclick={() => saveDigestFrequency(opt.key as WorkspaceDigestFrequency)}
                aria-pressed={myMembership.digest_frequency === opt.key}
                class="rounded-full px-3 py-1.5 text-xs font-semibold transition {myMembership.digest_frequency ===
                opt.key
                  ? 'bg-neutral-900 text-white'
                  : 'border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
              >
                {i18n.t(opt.labelKey)}
              </button>
            {/each}
          </div>
          <p class="text-xs text-neutral-500">💡 {i18n.t("workspace.teams.settings.digest_hint")}</p>
        </div>
      </section>
    {/if}

    <!-- Team management -->
    {#if isOwnerOrAdmin}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">
          {i18n.t("workspace.teams.settings.team_management")}
        </h2>

        <div class="flex items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <div>
            <p class="text-sm font-medium text-neutral-900">{i18n.t("workspace.teams.settings.edit_team")}</p>
            <p class="text-xs text-neutral-500">{i18n.t("workspace.teams.settings.edit_helper")}</p>
          </div>
          <a
            href={`/teams/${team.id}/edit`}
            class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
          >
            {i18n.t("workspace.teams.action.edit")} →
          </a>
        </div>

        <div class="flex items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <div>
            <p class="text-sm font-medium text-neutral-900">
              {team.is_archived
                ? i18n.t("workspace.teams.settings.unarchive")
                : i18n.t("workspace.teams.settings.archive")}
            </p>
            <p class="text-xs text-neutral-500">
              {team.is_archived
                ? i18n.t("workspace.teams.settings.unarchive_helper")
                : i18n.t("workspace.teams.settings.archive_helper")}
            </p>
          </div>
          <button
            type="button"
            onclick={() => (archiveOpen = true)}
            class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
          >
            {team.is_archived ? i18n.t("workspace.teams.action.unarchive") : i18n.t("workspace.teams.action.archive")}
          </button>
        </div>

        {#if isOwner}
          <div class="border-t border-neutral-200 pt-4 space-y-3">
            <h3 class="text-xs font-semibold uppercase tracking-[0.14em] text-rose-700">
              {i18n.t("workspace.teams.settings.danger_zone")}
            </h3>

            <div class="flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50/40 p-4">
              <div>
                <p class="text-sm font-medium text-neutral-900">
                  {i18n.t("workspace.teams.settings.transfer")}
                </p>
                <p class="text-xs text-neutral-500">{i18n.t("workspace.teams.settings.transfer_helper")}</p>
              </div>
              <button
                type="button"
                onclick={() => (transferOpen = true)}
                class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
              >
                {i18n.t("workspace.teams.action.transfer")} →
              </button>
            </div>

            <div class="flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50/40 p-4">
              <div>
                <p class="text-sm font-medium text-rose-900">
                  {i18n.t("workspace.teams.settings.delete")}
                </p>
                <p class="text-xs text-rose-700/80">{i18n.t("workspace.teams.settings.delete_helper")}</p>
              </div>
              <button
                type="button"
                onclick={() => (deleteOpen = true)}
                class="rounded-xl border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50"
              >
                {i18n.t("workspace.teams.action.delete")}
              </button>
            </div>
          </div>
        {/if}
      </section>
    {/if}
  </div>

  <!-- Archive confirm -->
  <ConfirmModal
    open={archiveOpen}
    onclose={() => (archiveOpen = false)}
    onconfirm={toggleArchive}
    title={team.is_archived
      ? i18n.t("workspace.teams.settings.unarchive")
      : i18n.t("workspace.teams.settings.archive")}
    message={team.is_archived
      ? i18n.t("workspace.teams.confirm.unarchive_message", { team: team.name })
      : i18n.t("workspace.teams.confirm.archive_message", { team: team.name })}
    confirmLabel={team.is_archived
      ? i18n.t("workspace.teams.action.unarchive")
      : i18n.t("workspace.teams.action.archive")}
    busy={archiveSaving}
  />

  <!-- Transfer modal -->
  <Modal
    open={transferOpen}
    onclose={() => {
      transferOpen = false;
      transferTarget = null;
    }}
    title={i18n.t("workspace.teams.settings.transfer")}
  >
    <div class="space-y-4">
      <p class="text-sm text-neutral-600">{i18n.t("workspace.teams.confirm.transfer_picker_helper")}</p>
      <UserPicker
        onSelect={(user) => (transferTarget = user)}
        excludeIds={memberOptionUsers
          .filter((u) => !members.some((m) => m.user.id === u.id))
          .map((u) => u.id)}
      />
      {#if transferTarget}
        <div class="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          {i18n.t("workspace.teams.confirm.transfer_message", { name: transferTarget.full_name })}
        </div>
      {/if}
      <div class="flex items-center justify-end gap-2 pt-2">
        <button
          type="button"
          onclick={() => {
            transferOpen = false;
            transferTarget = null;
          }}
          class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
        >
          {i18n.t("workspace.teams.confirm.cancel")}
        </button>
        <button
          type="button"
          onclick={transferOwnership}
          disabled={!transferTarget || transferSaving}
          class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
        >
          {transferSaving ? i18n.t("workspace.teams.confirm.working") : i18n.t("workspace.teams.action.transfer")}
        </button>
      </div>
    </div>
  </Modal>

  <!-- Hard delete confirm -->
  <ConfirmModal
    open={deleteOpen}
    onclose={() => (deleteOpen = false)}
    onconfirm={hardDelete}
    title={i18n.t("workspace.teams.confirm.delete_title")}
    message={i18n.t("workspace.teams.confirm.delete_message", { team: team.name })}
    confirmLabel={i18n.t("workspace.teams.action.delete")}
    destructive
    typeToConfirm={team.name}
    typeToConfirmLabel={i18n.t("workspace.teams.confirm.type_team_name", { team: team.name })}
    busy={deleteSaving}
  />
{/if}
