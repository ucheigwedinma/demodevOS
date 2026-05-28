<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import TeamCard from "$lib/components/teams/TeamCard.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type { PaginatedResponse, WorkspaceTeamListItem, WorkspaceTeamPurpose } from "$lib/types";

  type TabKey = "mine" | "all" | "archived";

  let tab = $state<TabKey>("mine");
  let purposeFilter = $state<"" | WorkspaceTeamPurpose>("");
  let searchTerm = $state("");
  let teams = $state<WorkspaceTeamListItem[]>([]);
  let nextUrl = $state<string | null>(null);
  let totalCount = $state(0);

  let loading = $state(true);
  let loadingMore = $state(false);
  let errorMessage = $state<string | null>(null);

  let searchSeq = 0;
  let debounceHandle: ReturnType<typeof setTimeout> | null = null;

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {};
    if (tab === "mine") params.mine = "true";
    if (tab === "archived") params.archived = "true";
    if (purposeFilter) params.purpose = purposeFilter;
    const q = searchTerm.trim();
    if (q) params.q = q;
    return params;
  }

  async function fetchTeams() {
    const seq = ++searchSeq;
    loading = true;
    errorMessage = null;
    try {
      const res = await api.get<PaginatedResponse<WorkspaceTeamListItem>>(
        "/workspace/teams/",
        buildParams(),
      );
      if (seq !== searchSeq) return;
      teams = res.results;
      nextUrl = res.next;
      totalCount = res.count;
    } catch (err) {
      console.error("[/teams]", err);
      if (seq !== searchSeq) return;
      teams = [];
      nextUrl = null;
      totalCount = 0;
      errorMessage =
        err instanceof ApiError
          ? `${err.status}: ${err.message}`
          : i18n.t("workspace.teams.error.load");
    } finally {
      if (seq === searchSeq) loading = false;
    }
  }

  async function loadMore() {
    if (!nextUrl || loadingMore) return;
    loadingMore = true;
    try {
      // The API returns a fully-qualified URL; strip /api/ prefix to match
      // our base. Cursor pagination preserves filters in the URL.
      const path = nextUrl.replace(/^https?:\/\/[^/]+/, "").replace(/^\/api/, "");
      const res = await api.get<PaginatedResponse<WorkspaceTeamListItem>>(path);
      teams = [...teams, ...res.results];
      nextUrl = res.next;
    } catch (err) {
      console.error("[/teams loadMore]", err);
      toast.error(i18n.t("workspace.teams.error.load"));
    } finally {
      loadingMore = false;
    }
  }

  function setTab(next: TabKey) {
    if (tab === next) return;
    tab = next;
    fetchTeams();
  }

  function setPurpose(value: string) {
    purposeFilter = (value as WorkspaceTeamPurpose | "") || "";
    fetchTeams();
  }

  function onSearchInput(e: Event) {
    searchTerm = (e.target as HTMLInputElement).value;
    if (debounceHandle) clearTimeout(debounceHandle);
    debounceHandle = setTimeout(fetchTeams, 250);
  }

  function clearSearch() {
    searchTerm = "";
    fetchTeams();
  }

  onMount(fetchTeams);

  const showSearchEmptyState = $derived(
    !loading && teams.length === 0 && searchTerm.trim().length > 0,
  );
</script>

<div class="space-y-4">
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
        {i18n.t("workspace.teams.eyebrow")}
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.teams.title")}
      </h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">
        {i18n.t("workspace.teams.helper")}
      </p>
    </div>
    <a
      href="/teams/new"
      class="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      {i18n.t("workspace.teams.new")}
    </a>
  </div>

  <!-- Filter shelf -->
  <section class="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex flex-wrap items-center gap-2">
        {#each [["mine", "workspace.teams.tabs.mine"], ["all", "workspace.teams.tabs.all"], ["archived", "workspace.teams.tabs.archived"]] as [key, labelKey] (key)}
          <button
            type="button"
            onclick={() => setTab(key as TabKey)}
            class="rounded-full px-3 py-1.5 text-xs font-semibold transition {tab === key
              ? 'bg-neutral-900 text-white'
              : 'border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
          >
            {i18n.t(labelKey)}
          </button>
        {/each}
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select
          value={purposeFilter}
          onchange={(e) => setPurpose((e.target as HTMLSelectElement).value)}
          class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-700 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          <option value="">{i18n.t("workspace.teams.purpose_filter.all")}</option>
          <option value="project">{i18n.t("workspace.teams.purpose.project")}</option>
          <option value="initiative">{i18n.t("workspace.teams.purpose.initiative")}</option>
          <option value="guild">{i18n.t("workspace.teams.purpose.guild")}</option>
        </select>
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
            placeholder={i18n.t("workspace.teams.search_placeholder")}
            class="w-56 rounded-xl border border-neutral-200 bg-neutral-50 py-2 pl-9 pr-3 text-xs text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
        </div>
      </div>
    </div>
  </section>

  <!-- Body -->
  {#if loading}
    <div class="flex items-center justify-center py-28">
      <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if errorMessage}
    <DataStateBanner
      title={i18n.t("workspace.teams.error.load")}
      message={errorMessage}
      onretry={fetchTeams}
    />
  {:else if teams.length === 0}
    {#if showSearchEmptyState}
      <div class="rounded-2xl border border-neutral-200 bg-white p-8 text-center">
        <p class="text-sm text-neutral-600">
          {i18n.t("workspace.teams.empty.search", { query: searchTerm })}
        </p>
        <button
          type="button"
          onclick={clearSearch}
          class="mt-3 text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
        >
          {i18n.t("workspace.teams.empty.clear_search")}
        </button>
      </div>
    {:else if tab === "archived"}
      <div class="rounded-2xl border border-neutral-200 bg-white p-8 text-center">
        <p class="text-sm text-neutral-500">{i18n.t("workspace.teams.empty.archived")}</p>
      </div>
    {:else}
      <div class="rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
        <p class="text-3xl">👥</p>
        <h2 class="mt-3 text-lg font-semibold text-neutral-900">
          {tab === "mine"
            ? i18n.t("workspace.teams.empty.mine.title")
            : i18n.t("workspace.teams.empty.org.title")}
        </h2>
        <p class="mt-1 text-sm text-neutral-500">
          {tab === "mine"
            ? i18n.t("workspace.teams.empty.mine.helper")
            : i18n.t("workspace.teams.empty.org.helper")}
        </p>
        <div class="mt-4 flex items-center justify-center gap-3">
          {#if tab === "mine"}
            <button
              type="button"
              onclick={() => setTab("all")}
              class="text-xs font-semibold text-neutral-700 underline hover:text-neutral-900"
            >
              {i18n.t("workspace.teams.empty.browse_all")}
            </button>
          {/if}
          <a
            href="/teams/new"
            class="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800"
          >
            {i18n.t("workspace.teams.new")}
          </a>
        </div>
      </div>
    {/if}
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {#each teams as team (team.id)}
        <TeamCard {team} />
      {/each}
    </div>

    {#if nextUrl}
      <div class="flex items-center justify-center pt-2">
        <button
          type="button"
          onclick={loadMore}
          disabled={loadingMore}
          class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-xs font-semibold text-neutral-700 hover:border-neutral-400 disabled:opacity-60"
        >
          {loadingMore ? i18n.t("workspace.teams.loading_more") : i18n.t("workspace.teams.load_more")}
        </button>
      </div>
    {/if}

    <p class="text-center text-xs text-neutral-500">
      {i18n.t("workspace.teams.showing_count", { shown: teams.length, total: totalCount })}
    </p>
  {/if}
</div>
