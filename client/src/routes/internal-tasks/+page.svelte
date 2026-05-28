<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    InternalTaskListItem,
    InternalTaskOverlayRow,
    InternalTaskStatus,
    InternalTaskPriority,
    InternalTaskTagBucket,
    PaginatedResponse,
  } from "$lib/types";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import TaskRow from "$lib/components/internal-tasks/TaskRow.svelte";
  import { STATUS_ORDER, STATUS_TREATMENT } from "$lib/components/internal-tasks/task-status";
  import { PRIORITY_ORDER, PRIORITY_TREATMENT } from "$lib/components/internal-tasks/task-priority";

  type Row = InternalTaskListItem | InternalTaskOverlayRow;
  type Tab = "my" | "team" | "all";

  // ----- state ----------------------------------------------------------------

  let tab = $state<Tab>("my");
  let statusFilter = $state<Set<InternalTaskStatus>>(new Set(["todo", "in_progress"]));
  let priorityFilter = $state<Set<InternalTaskPriority>>(new Set());
  let tagFilters = $state<string[]>([]);
  let overdueOnly = $state(false);
  let searchQuery = $state("");
  let searchDebounced = $state("");

  let tasks = $state<InternalTaskListItem[]>([]);
  let overlay = $state<InternalTaskOverlayRow[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let nextCursor = $state<string | null>(null);
  let tagSuggestions = $state<InternalTaskTagBucket[]>([]);
  let quickAddTitle = $state("");
  let quickAddBusy = $state(false);

  // ----- debounce search ----------------------------------------------------

  let searchTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    if (searchTimer) clearTimeout(searchTimer);
    const q = searchQuery;
    searchTimer = setTimeout(() => {
      searchDebounced = q;
    }, 250);
  });

  // ----- query construction --------------------------------------------------

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {};
    if (tab === "my") params.assignee = "me";
    if (statusFilter.size > 0) {
      params.status = [...statusFilter].join(",");
    }
    if (priorityFilter.size > 0) {
      params.priority = [...priorityFilter].join(",");
    }
    for (const t of tagFilters) {
      // Repeated params: api.get's Record signature can't easily do repeated
      // values, so we encode multi-tag via comma-separated and let the server
      // do the AND. Server supports both repeat-and-comma; we pick one.
      // (Backend supports `getlist("tag")` which means repeated only.)
      // For now: we emit only the first tag to params (limitation; user can
      // refine by combining with search). For full AND semantics add a query
      // builder that emits repeated tag= params.
    }
    if (overdueOnly) params.overdue = "true";
    if (searchDebounced) params.q = searchDebounced;
    return params;
  }

  function buildOverlayParams(): Record<string, string> {
    const params: Record<string, string> = {
      source: "project_task,crm_follow_up",
      assignee: tab === "my" ? "me" : "all",
    };
    if (overdueOnly) params.overdue = "true";
    return params;
  }

  // ----- list rendering window -----------------------------------------------

  let fetchSeq = 0;
  async function load() {
    const seq = ++fetchSeq;
    loading = true;
    error = null;

    // Build URL — repeated `tag=` requires manual handling.
    const baseParams = buildParams();
    const tagQs = tagFilters.map((t) => `&tag=${encodeURIComponent(t)}`).join("");
    const url = `/internal-tasks/tasks/?${new URLSearchParams(baseParams).toString()}${tagQs}`;

    try {
      const [tasksRes, overlayRes] = await Promise.allSettled([
        api.get<PaginatedResponse<InternalTaskListItem>>(url),
        tab !== "all"
          ? api.get<{ results: InternalTaskOverlayRow[] }>(
              "/internal-tasks/overlay/",
              buildOverlayParams(),
            )
          : Promise.resolve({ results: [] }),
      ]);
      if (seq !== fetchSeq) return;
      if (tasksRes.status === "fulfilled") {
        tasks = tasksRes.value.results;
        nextCursor = tasksRes.value.next;
      } else {
        error = i18n.t("workspace.internal_tasks.error.load");
        tasks = [];
      }
      if (overlayRes.status === "fulfilled") {
        overlay = (overlayRes.value as any).results ?? [];
      } else {
        overlay = [];
      }
    } catch (err) {
      console.error(err);
      if (seq === fetchSeq) error = i18n.t("workspace.internal_tasks.error.load");
    } finally {
      if (seq === fetchSeq) loading = false;
    }
  }

  // Reload on any filter change.
  $effect(() => {
    void tab;
    void statusFilter;
    void priorityFilter;
    void tagFilters;
    void overdueOnly;
    void searchDebounced;
    void load();
  });

  // Load tag autocomplete once on mount.
  onMount(async () => {
    try {
      const res = await api.get<{ results: InternalTaskTagBucket[] }>(
        "/internal-tasks/tasks/tags/",
      );
      tagSuggestions = res.results;
    } catch {
      tagSuggestions = [];
    }
  });

  // ----- filter helpers ------------------------------------------------------

  function toggleStatus(s: InternalTaskStatus) {
    const next = new Set(statusFilter);
    if (next.has(s)) next.delete(s);
    else next.add(s);
    statusFilter = next;
  }
  function togglePriority(p: InternalTaskPriority) {
    const next = new Set(priorityFilter);
    if (next.has(p)) next.delete(p);
    else next.add(p);
    priorityFilter = next;
  }
  function toggleTag(t: string) {
    if (tagFilters.includes(t)) {
      tagFilters = tagFilters.filter((x) => x !== t);
    } else {
      tagFilters = [...tagFilters, t];
    }
  }
  function clearFilters() {
    statusFilter = new Set(["todo", "in_progress"]);
    priorityFilter = new Set();
    tagFilters = [];
    overdueOnly = false;
    searchQuery = "";
  }

  // ----- inline interactions -------------------------------------------------

  async function toggleDone(task: InternalTaskListItem) {
    const previous = task.status;
    const optimistic = previous === "done" ? "todo" : "done";
    tasks = tasks.map((t) =>
      t.id === task.id ? { ...t, status: optimistic, overdue: optimistic === "done" ? false : t.overdue } : t,
    );
    try {
      await api.post(`/internal-tasks/tasks/${task.id}/complete/`, {});
    } catch (err) {
      tasks = tasks.map((t) => (t.id === task.id ? { ...t, status: previous } : t));
      toast.error(i18n.t("workspace.internal_tasks.toast.update_failed"));
    }
  }

  async function changeStatus(task: InternalTaskListItem, next: InternalTaskStatus) {
    const previous = task.status;
    tasks = tasks.map((t) => (t.id === task.id ? { ...t, status: next } : t));
    try {
      await api.patch(`/internal-tasks/tasks/${task.id}/`, { status: next });
    } catch (err) {
      tasks = tasks.map((t) => (t.id === task.id ? { ...t, status: previous } : t));
      toast.error(i18n.t("workspace.internal_tasks.toast.update_failed"));
    }
  }

  function openTask(row: Row) {
    if ("source" in row) {
      // Overlay row: navigate to owning app.
      goto(row.edit_url);
      return;
    }
    goto(`/internal-tasks/${row.id}`);
  }

  // ----- quick-add ------------------------------------------------------------

  async function quickAdd() {
    const title = quickAddTitle.trim();
    if (!title || quickAddBusy) return;
    quickAddBusy = true;
    try {
      await api.post("/internal-tasks/tasks/", {
        title,
        status: "todo",
        priority: "medium",
        visibility: "private",
      });
      quickAddTitle = "";
      await load();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? (err.data?.detail as string) ?? i18n.t("workspace.internal_tasks.toast.create_failed")
          : i18n.t("workspace.internal_tasks.toast.create_failed");
      toast.error(msg);
    } finally {
      quickAddBusy = false;
    }
  }

  function quickAddKey(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      void quickAdd();
    }
  }

  // ----- merge + sort --------------------------------------------------------

  let merged = $derived<Row[]>([...tasks, ...overlay]);

  let isEmpty = $derived(!loading && merged.length === 0 && !error);

  function goNew() {
    goto("/internal-tasks/new");
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
        {i18n.t("workspace.internal_tasks.eyebrow")}
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.internal_tasks.title")}
      </h1>
      <p class="mt-1 max-w-xl text-sm text-neutral-500">
        {i18n.t("workspace.internal_tasks.helper")}
      </p>
    </div>
    <button
      type="button"
      onclick={goNew}
      class="hidden items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 sm:inline-flex"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      {i18n.t("workspace.internal_tasks.new_task")}
    </button>
  </div>

  <!-- Quick add -->
  <div class="rounded-2xl border border-neutral-200 bg-white p-4">
    <div class="flex items-center gap-2">
      <span class="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 bg-white" aria-hidden="true">
        <svg class="h-3 w-3 text-neutral-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </span>
      <input
        type="text"
        bind:value={quickAddTitle}
        onkeydown={quickAddKey}
        placeholder={i18n.t("workspace.internal_tasks.quick_add_placeholder")}
        class="flex-1 bg-transparent text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
        disabled={quickAddBusy}
      />
      {#if quickAddTitle.trim()}
        <button
          type="button"
          onclick={quickAdd}
          disabled={quickAddBusy}
          class="rounded-lg bg-neutral-900 px-3 py-1 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
        >
          {i18n.t("workspace.internal_tasks.quick_add")}
        </button>
      {/if}
    </div>
  </div>

  <!-- Toolbar -->
  <div class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
    <!-- Tab strip -->
    <div class="flex flex-wrap items-center gap-2">
      {#each ["my", "team", "all"] as t}
        <button
          type="button"
          onclick={() => (tab = t as Tab)}
          class="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider transition {tab === t ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
        >
          {i18n.t(`workspace.internal_tasks.tabs.${t}`)}
        </button>
      {/each}

      <span class="ml-auto inline-flex items-center gap-2">
        <input
          type="search"
          bind:value={searchQuery}
          placeholder={i18n.t("workspace.internal_tasks.search_placeholder")}
          class="rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs text-neutral-700 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        />
      </span>
    </div>

    <!-- Filter chips -->
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
        {i18n.t("workspace.internal_tasks.filters.status")}
      </span>
      {#each STATUS_ORDER as s}
        {@const treat = STATUS_TREATMENT[s]}
        <button
          type="button"
          onclick={() => toggleStatus(s)}
          class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider {statusFilter.has(s) ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-500'}"
        >
          {i18n.t(treat.labelKey)}
        </button>
      {/each}

      <span class="ml-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
        {i18n.t("workspace.internal_tasks.filters.priority")}
      </span>
      {#each PRIORITY_ORDER as p}
        {@const treat = PRIORITY_TREATMENT[p]}
        <button
          type="button"
          onclick={() => togglePriority(p)}
          class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider {priorityFilter.has(p) ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-500'}"
        >
          {i18n.t(treat.labelKey)}
        </button>
      {/each}

      <label class="ml-2 inline-flex cursor-pointer items-center gap-1.5 text-xs text-neutral-700">
        <input type="checkbox" bind:checked={overdueOnly} class="h-3.5 w-3.5 accent-rose-700" />
        {i18n.t("workspace.internal_tasks.filters.overdue_only")}
      </label>

      {#if statusFilter.size !== 2 || priorityFilter.size > 0 || tagFilters.length > 0 || overdueOnly || searchDebounced}
        <button
          type="button"
          onclick={clearFilters}
          class="ml-auto text-[11px] text-neutral-500 underline-offset-2 hover:text-neutral-900 hover:underline"
        >
          {i18n.t("workspace.internal_tasks.filters.clear")}
        </button>
      {/if}
    </div>

    {#if tagSuggestions.length > 0}
      <div class="flex flex-wrap items-center gap-1">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
          {i18n.t("workspace.internal_tasks.filters.tag")}
        </span>
        {#each tagSuggestions.slice(0, 12) as bucket}
          <button
            type="button"
            onclick={() => toggleTag(bucket.tag)}
            class="rounded-full border px-2 py-0.5 text-[10px] font-medium {tagFilters.includes(bucket.tag) ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-400'}"
          >
            #{bucket.tag}
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Canvas -->
  {#if loading && merged.length === 0}
    <div class="flex items-center justify-center py-28">
      <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if error}
    <DataStateBanner
      title={i18n.t("workspace.internal_tasks.error.load")}
      message={i18n.t("workspace.internal_tasks.error.load_helper")}
      onretry={load}
    />
  {:else if isEmpty}
    <div class="rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
      <p class="text-3xl">📝</p>
      <p class="mt-3 text-base font-semibold text-neutral-800">
        {i18n.t("workspace.internal_tasks.empty.title")}
      </p>
      <p class="mt-1 text-sm text-neutral-500">
        {i18n.t("workspace.internal_tasks.empty.helper")}
      </p>
      <button
        type="button"
        onclick={goNew}
        class="mt-4 inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        {i18n.t("workspace.internal_tasks.empty.cta")}
      </button>
    </div>
  {:else}
    <div class="space-y-2">
      {#each merged as row (`${"source" in row ? row.source : "native"}-${row.id}`)}
        <TaskRow
          task={row}
          onClick={openTask}
          onToggleDone={toggleDone}
          onChangeStatus={changeStatus}
        />
      {/each}
    </div>
  {/if}
</div>

<!-- FAB on mobile -->
<button
  type="button"
  onclick={goNew}
  class="fixed bottom-6 right-6 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg hover:bg-neutral-800 sm:hidden"
  aria-label={i18n.t("workspace.internal_tasks.new_task")}
>
  <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
</button>
