<script lang="ts">
  import { api } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { PaginatedResponse, UserDirectoryItem } from "$lib/types";

  /**
   * UserPicker — async-search picker for org members. Hits /iam/users/.
   *
   * Two modes via `multiple`:
   *  - false (default): returns one user via `onSelect`, clears input.
   *  - true: maintains a `selected` list, emits a "Selected" pill row.
   */

  interface Props {
    multiple?: boolean;
    placeholder?: string;
    /** Single mode: fires when a user is picked from the dropdown. */
    onSelect?: (user: UserDirectoryItem) => void;
    /** Multi mode: bind to a list of users; component manages add/remove. */
    selected?: UserDirectoryItem[];
    /** Optional filter — exclude users by id (e.g. existing members). */
    excludeIds?: number[];
  }

  let {
    multiple = false,
    placeholder,
    onSelect,
    selected = $bindable([]),
    excludeIds = [],
  }: Props = $props();

  let query = $state("");
  let results = $state<UserDirectoryItem[]>([]);
  let loading = $state(false);
  let open = $state(false);
  let inputEl = $state<HTMLInputElement | null>(null);
  let containerEl = $state<HTMLDivElement | null>(null);

  let searchSeq = 0;
  let debounceHandle: ReturnType<typeof setTimeout> | null = null;

  async function runSearch(q: string) {
    const seq = ++searchSeq;
    if (!q.trim()) {
      results = [];
      loading = false;
      return;
    }
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<UserDirectoryItem>>("/iam/users/", {
        q: q.trim(),
        status: "active",
        page_size: "10",
      });
      if (seq !== searchSeq) return;
      const exclude = new Set(excludeIds);
      results = res.results.filter((u) => !exclude.has(u.id));
    } catch (err) {
      console.error("[UserPicker]", err);
      if (seq !== searchSeq) return;
      results = [];
    } finally {
      if (seq === searchSeq) loading = false;
    }
  }

  function onInput(e: Event) {
    query = (e.target as HTMLInputElement).value;
    open = true;
    if (debounceHandle) clearTimeout(debounceHandle);
    debounceHandle = setTimeout(() => runSearch(query), 250);
  }

  function pick(user: UserDirectoryItem) {
    if (multiple) {
      if (!selected.some((u) => u.id === user.id)) {
        selected = [...selected, user];
      }
    } else {
      onSelect?.(user);
    }
    query = "";
    results = [];
    open = false;
    inputEl?.focus();
  }

  function removeSelected(id: number) {
    selected = selected.filter((u) => u.id !== id);
  }

  function handleClickOutside(e: MouseEvent) {
    if (!open) return;
    if (containerEl && !containerEl.contains(e.target as Node)) {
      open = false;
    }
  }

  const placeholderText = $derived(
    placeholder ?? i18n.t("workspace.teams.user_picker.placeholder"),
  );
</script>

<svelte:window onclick={handleClickOutside} />

<div bind:this={containerEl} class="relative w-full">
  <div class="relative">
    <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-4.35-4.35M16.5 10.5a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z" />
      </svg>
    </span>
    <input
      bind:this={inputEl}
      type="search"
      role="combobox"
      aria-expanded={open}
      aria-autocomplete="list"
      placeholder={placeholderText}
      value={query}
      oninput={onInput}
      onfocus={() => (open = true)}
      class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 py-3 pl-9 pr-4 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
    />
  </div>

  {#if open && (loading || results.length > 0 || query.trim().length > 0)}
    <div
      role="listbox"
      class="absolute left-0 right-0 z-30 mt-1 max-h-72 overflow-auto rounded-2xl border border-neutral-200 bg-white shadow-md"
    >
      {#if loading}
        <p class="px-4 py-3 text-xs text-neutral-500">{i18n.t("workspace.teams.user_picker.searching")}</p>
      {:else if results.length === 0 && query.trim().length > 0}
        <p class="px-4 py-3 text-xs text-neutral-500">{i18n.t("workspace.teams.user_picker.no_matches")}</p>
      {:else}
        {#each results as user (user.id)}
          <button
            type="button"
            role="option"
            aria-selected="false"
            onclick={() => pick(user)}
            class="flex w-full items-center gap-3 px-4 py-2 text-left transition-colors hover:bg-neutral-50"
          >
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-700" aria-hidden="true">
              {(user.full_name || user.email || "?").slice(0, 2).toUpperCase()}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-neutral-900">{user.full_name || user.email}</span>
              <span class="block truncate text-xs text-neutral-500">
                {user.email}{#if user.job_title}<span> · {user.job_title}</span>{/if}
              </span>
            </span>
          </button>
        {/each}
      {/if}
    </div>
  {/if}

  {#if multiple && selected.length > 0}
    <div class="mt-3 flex flex-wrap gap-2">
      {#each selected as user (user.id)}
        <span class="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-700">
          {user.full_name || user.email}
          <button
            type="button"
            onclick={() => removeSelected(user.id)}
            class="rounded-full p-0.5 text-neutral-500 hover:bg-neutral-200 hover:text-neutral-800"
            aria-label={i18n.t("workspace.teams.user_picker.remove_selected")}
          >
            <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      {/each}
    </div>
  {/if}
</div>
