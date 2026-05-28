<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    InternalTaskChecklistItem,
    InternalTaskComment,
    InternalTaskDetail,
    InternalTaskStatus,
  } from "$lib/types";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import ConfirmModal from "$lib/components/teams/ConfirmModal.svelte";
  import StatusChip from "$lib/components/internal-tasks/StatusChip.svelte";
  import PriorityChip from "$lib/components/internal-tasks/PriorityChip.svelte";
  import ChecklistEditor from "$lib/components/internal-tasks/ChecklistEditor.svelte";
  import CommentThread from "$lib/components/internal-tasks/CommentThread.svelte";

  let id = $derived(parseInt($page.params.id ?? "0"));

  let detail = $state<InternalTaskDetail | null>(null);
  let comments = $state<InternalTaskComment[]>([]);
  let currentUserId = $state<number>(0);
  let loading = $state(true);
  let notFound = $state(false);
  let error = $state<string | null>(null);

  let deleteOpen = $state(false);
  let saveTimer: ReturnType<typeof setTimeout> | null = null;

  onMount(load);

  async function load() {
    loading = true;
    notFound = false;
    error = null;
    try {
      const [det, cmts, me] = await Promise.all([
        api.get<InternalTaskDetail>(`/internal-tasks/tasks/${id}/`),
        api
          .get<InternalTaskComment[]>(`/internal-tasks/tasks/${id}/comments/`)
          .catch(() => [] as InternalTaskComment[]),
        api
          .get<{ id: number }>("/auth/me/")
          .catch(() => ({ id: 0 })),
      ]);
      detail = det;
      comments = cmts;
      currentUserId = me.id ?? 0;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        notFound = true;
      } else {
        console.error(err);
        error = i18n.t("workspace.internal_tasks.error.load");
      }
    } finally {
      loading = false;
    }
  }

  // ----- inline optimistic updates -----------------------------------------

  async function changeStatus(next: InternalTaskStatus) {
    if (!detail) return;
    const previous = detail.status;
    detail = { ...detail, status: next, completed_at: next === "done" ? new Date().toISOString() : null };
    try {
      const updated = await api.patch<InternalTaskDetail>(
        `/internal-tasks/tasks/${detail.id}/`,
        { status: next },
      );
      detail = updated;
    } catch (err) {
      detail = { ...detail, status: previous };
      toast.error(i18n.t("workspace.internal_tasks.toast.update_failed"));
    }
  }

  async function saveChecklist(next: InternalTaskChecklistItem[]) {
    if (!detail) return;
    const previous = detail.checklist_items;
    detail = { ...detail, checklist_items: next };
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        await api.post(`/internal-tasks/tasks/${id}/checklist/`, { items: next });
      } catch (err) {
        if (detail) detail = { ...detail, checklist_items: previous };
        toast.error(i18n.t("workspace.internal_tasks.toast.update_failed"));
      }
    }, 500);
  }

  async function toggleDone() {
    if (!detail) return;
    const previous = detail.status;
    const next: InternalTaskStatus = previous === "done" ? "todo" : "done";
    await changeStatus(next);
  }

  async function deleteTask() {
    if (!detail) return;
    deleteOpen = false;
    try {
      await api.delete(`/internal-tasks/tasks/${detail.id}/`);
      toast.success(i18n.t("workspace.internal_tasks.toast.deleted"));
      goto("/internal-tasks");
    } catch (err) {
      toast.error(i18n.t("workspace.internal_tasks.toast.delete_failed"));
    }
  }

  function edit() {
    if (detail) goto(`/internal-tasks/${detail.id}/edit`);
  }

  // ----- derived state -----------------------------------------------------

  let isCreator = $derived(detail?.my_role === "creator");
  let canEdit = $derived(detail?.my_role === "creator" || detail?.my_role === "assignee");
  let canDelete = $derived(detail?.my_role === "creator");

  function fmtDueDate(d: string | null): string {
    if (!d) return "";
    return new Intl.DateTimeFormat(i18n.locale, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    }).format(new Date(`${d}T00:00:00`));
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound}
  <div class="mx-auto max-w-md rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
    <p class="text-3xl">🔍</p>
    <p class="mt-3 text-base font-semibold text-neutral-800">
      {i18n.t("workspace.internal_tasks.error.not_found")}
    </p>
    <p class="mt-1 text-sm text-neutral-500">
      {i18n.t("workspace.internal_tasks.error.not_found_helper")}
    </p>
    <a
      href="/internal-tasks"
      class="mt-4 inline-flex items-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
    >
      {i18n.t("workspace.internal_tasks.back_to_list")}
    </a>
  </div>
{:else if error || !detail}
  <DataStateBanner
    title={i18n.t("workspace.internal_tasks.error.load")}
    message={i18n.t("workspace.internal_tasks.error.load_helper")}
    onretry={load}
  />
{:else}
  <div class="space-y-6">
    <!-- Breadcrumbs -->
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.title")}</a>
      <span class="text-neutral-300"> › </span>
      <span class="text-blue-600 normal-case tracking-normal">{detail.title}</span>
    </p>

    <!-- Header card -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-start gap-3">
        <button
          type="button"
          onclick={toggleDone}
          disabled={!canEdit}
          aria-label={detail.status === "done"
            ? i18n.t("workspace.internal_tasks.action.reopen")
            : i18n.t("workspace.internal_tasks.action.mark_done")}
          class="mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border {detail.status === 'done' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-transparent hover:border-neutral-700'} disabled:cursor-not-allowed disabled:opacity-50"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        </button>

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <StatusChip
              status={detail.status}
              size="md"
              editable={canEdit}
              onChange={(s) => changeStatus(s)}
            />
            <PriorityChip priority={detail.priority} size="md" />
            <span
              class="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-neutral-600"
            >
              {i18n.t(`workspace.internal_tasks.visibility.${detail.visibility}`)}
            </span>
          </div>

          <h1
            class="mt-3 text-2xl font-bold tracking-wide text-neutral-800 {detail.status === 'done' ? 'line-through opacity-60' : ''}"
          >
            {detail.title}
          </h1>
          {#if detail.description}
            <p class="mt-2 max-w-2xl whitespace-pre-wrap text-sm text-neutral-600">
              {detail.description}
            </p>
          {/if}

          <dl class="mt-4 grid gap-2 sm:grid-cols-2">
            <div class="flex items-start gap-2 text-sm text-neutral-700">
              <span class="text-neutral-400" aria-hidden="true">👤</span>
              <span>
                <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  {i18n.t("workspace.internal_tasks.detail.assignee")}
                </span><br />
                {#if detail.assignee}
                  {detail.assignee.name}
                {:else}
                  <span class="text-neutral-500">{i18n.t("workspace.internal_tasks.unassigned")}</span>
                {/if}
              </span>
            </div>
            {#if detail.due_date}
              <div class="flex items-start gap-2 text-sm text-neutral-700">
                <span class="text-neutral-400" aria-hidden="true">📅</span>
                <span>
                  <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                    {i18n.t("workspace.internal_tasks.detail.due")}
                  </span><br />
                  <span class={detail.overdue ? "font-semibold text-rose-700" : ""}>
                    {fmtDueDate(detail.due_date)}
                  </span>
                </span>
              </div>
            {/if}
            <div class="flex items-start gap-2 text-sm text-neutral-700">
              <span class="text-neutral-400" aria-hidden="true">✍️</span>
              <span>
                <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  {i18n.t("workspace.internal_tasks.detail.creator")}
                </span><br />
                {detail.creator.name}
              </span>
            </div>
            {#if detail.team}
              <div class="flex items-start gap-2 text-sm text-neutral-700">
                <span class="text-neutral-400" aria-hidden="true">👥</span>
                <span>
                  <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                    {i18n.t("workspace.internal_tasks.detail.team")}
                  </span><br />
                  <a class="text-neutral-900 hover:underline" href={`/teams/${detail.team}`}>
                    {i18n.t("workspace.internal_tasks.detail.open_team")} →
                  </a>
                </span>
              </div>
            {/if}
          </dl>

          {#if detail.tags.length > 0}
            <div class="mt-3 flex flex-wrap gap-1.5">
              {#each detail.tags as tag}
                <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">
                  #{tag}
                </span>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="mt-5 flex flex-wrap items-center gap-2">
        {#if canEdit}
          <button
            type="button"
            onclick={edit}
            class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
          >
            {i18n.t("workspace.internal_tasks.actions.edit")}
          </button>
        {/if}
        {#if canDelete}
          <button
            type="button"
            onclick={() => (deleteOpen = true)}
            class="rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:border-rose-400"
          >
            {i18n.t("workspace.internal_tasks.actions.delete")}
          </button>
        {/if}
      </div>
    </section>

    <!-- Checklist -->
    {#if detail.checklist_items.length > 0 || canEdit}
      <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">
          {i18n.t("workspace.internal_tasks.detail.checklist")}
        </h2>
        <ChecklistEditor
          items={detail.checklist_items}
          readonly={!canEdit}
          onChange={saveChecklist}
        />
      </section>
    {/if}

    <!-- Comments -->
    <CommentThread {currentUserId} taskId={detail.id} bind:comments />
  </div>
{/if}

<ConfirmModal
  open={deleteOpen}
  destructive
  title={i18n.t("workspace.internal_tasks.delete_confirm.title")}
  message={i18n.t("workspace.internal_tasks.delete_confirm.message")}
  confirmLabel={i18n.t("workspace.internal_tasks.actions.delete")}
  onclose={() => (deleteOpen = false)}
  onconfirm={deleteTask}
/>
