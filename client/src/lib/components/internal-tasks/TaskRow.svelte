<script lang="ts">
  import type {
    InternalTaskListItem,
    InternalTaskOverlayRow,
    InternalTaskStatus,
  } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { resolveTeamEdge } from "$lib/components/calendar/team-edge-colors";
  import { STATUS_TREATMENT } from "./task-status";
  import { PRIORITY_TREATMENT } from "./task-priority";
  import StatusChip from "./StatusChip.svelte";
  import PriorityChip from "./PriorityChip.svelte";
  import OperationalTaskBadge from "./OperationalTaskBadge.svelte";

  /**
   * List row for both native InternalTaskListItem and overlay rows.
   * Detects via the `source` property (overlay rows have it).
   *
   * Per UI spec:
   *   - Status checkbox toggles done ↔ todo only (1-click)
   *   - Status chip (separate from checkbox) is editable; opens dropdown
   *   - Priority chip only shown for high + urgent (per PRIORITY_TREATMENT.showInRow)
   *   - Overdue: red text on due_date only
   *   - Team-scoped: left-edge accent (4px strip)
   *   - Overlay rows: dashed border + "P"/"C" badge in top-right
   */

  type Row = InternalTaskListItem | InternalTaskOverlayRow;

  interface Props {
    task: Row;
    /** Map team_id → color token (parent supplies via teams cache). */
    teamColor?: string | null;
    /** Click handler; navigates to detail or owning app for overlay rows. */
    onClick?: (task: Row) => void;
    /** Optimistic done/reopen toggle. Only called for native tasks (not overlay). */
    onToggleDone?: (task: InternalTaskListItem) => void;
    /** Optimistic status change via dropdown. Native tasks only. */
    onChangeStatus?: (task: InternalTaskListItem, status: InternalTaskStatus) => void;
  }

  let { task, teamColor = null, onClick, onToggleDone, onChangeStatus }: Props = $props();

  let isOverlay = $derived("source" in task);
  let teamEdge = $derived(resolveTeamEdge(teamColor));
  let borderStyle = $derived(isOverlay ? "border-dashed" : "border-solid");

  let nativeTask = $derived(isOverlay ? null : (task as InternalTaskListItem));
  let overlayTask = $derived(isOverlay ? (task as InternalTaskOverlayRow) : null);

  let isDone = $derived(task.status === "done");

  let priorityTreatment = $derived(PRIORITY_TREATMENT[task.priority]);
  let showPriority = $derived(priorityTreatment.showInRow);

  function fmtDueDate(d: string | null): string {
    if (!d) return "";
    return new Intl.DateTimeFormat(i18n.locale, {
      month: "short",
      day: "numeric",
    }).format(new Date(`${d}T00:00:00`));
  }

  function handleClick(e: MouseEvent) {
    // Don't open detail when clicking the inline checkbox or chip.
    if ((e.target as HTMLElement).closest("button")) return;
    onClick?.(task);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Enter") onClick?.(task);
  }

  function toggleDone() {
    if (!nativeTask) return;
    onToggleDone?.(nativeTask);
  }

  function changeStatus(status: InternalTaskStatus) {
    if (!nativeTask) return;
    onChangeStatus?.(nativeTask, status);
  }

  let overdue = $derived(
    !isOverlay && (task as InternalTaskListItem).overdue && !isDone,
  );
  let dueLabel = $derived(task.due_date ? fmtDueDate(task.due_date) : "");
</script>

<div
  class="group relative flex w-full items-center gap-3 rounded-2xl border-l-4 border bg-white px-4 py-3 text-left transition hover:border-neutral-400 {teamEdge} {borderStyle} {isDone ? 'opacity-60' : ''}"
  role="button"
  tabindex="0"
  aria-label={task.title}
  onclick={handleClick}
  onkeydown={handleKey}
>
  <!-- Checkbox: native only; toggles done ↔ todo -->
  {#if nativeTask}
    <button
      type="button"
      onclick={toggleDone}
      aria-label={isDone
        ? i18n.t("workspace.internal_tasks.action.reopen")
        : i18n.t("workspace.internal_tasks.action.mark_done")}
      class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border {isDone ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-transparent hover:border-neutral-700'}"
    >
      <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
      </svg>
    </button>
  {:else}
    <!-- Overlay row: read-only marker -->
    <span class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-neutral-300 bg-neutral-50" aria-hidden="true">
      <svg class="h-3 w-3 text-neutral-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75M3.75 21.75h13.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75A2.25 2.25 0 0 0 1.5 12.75v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
      </svg>
    </span>
  {/if}

  <!-- Title + meta -->
  <div class="min-w-0 flex-1">
    <div class="truncate text-sm font-medium text-neutral-900 {isDone ? 'line-through' : ''}">
      {task.title}
    </div>
    <!-- second line: source attribution for overlay rows -->
    {#if overlayTask}
      <div class="mt-0.5 truncate text-[11px] text-neutral-500">
        {#if overlayTask.source === "project_task"}
          {i18n.t("workspace.internal_tasks.overlay.from_project", { name: overlayTask.project_name ?? "—" })}
        {:else}
          {i18n.t("workspace.internal_tasks.overlay.from_lead", { name: overlayTask.lead_name ?? "—" })}
        {/if}
      </div>
    {:else if (task as InternalTaskListItem).tags?.length}
      <div class="mt-0.5 flex flex-wrap gap-1">
        {#each (task as InternalTaskListItem).tags.slice(0, 4) as t}
          <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
            #{t}
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Right column: priority + status + due + overlay badge -->
  <div class="flex shrink-0 items-center gap-2">
    {#if showPriority}
      <PriorityChip priority={task.priority} />
    {/if}

    {#if nativeTask}
      <StatusChip
        status={task.status}
        editable
        onChange={(s) => changeStatus(s)}
      />
    {:else}
      <StatusChip status={task.status} />
    {/if}

    {#if dueLabel}
      <span
        class="text-xs tabular-nums {overdue ? 'font-semibold text-rose-700' : 'text-neutral-500'}"
        aria-label={overdue ? i18n.t("workspace.internal_tasks.overdue") : undefined}
      >
        {dueLabel}
      </span>
    {/if}

    {#if overlayTask}
      <OperationalTaskBadge source={overlayTask.source} />
    {/if}
  </div>
</div>
