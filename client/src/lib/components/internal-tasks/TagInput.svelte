<script lang="ts">
  import { api } from "$lib/api";
  import type { InternalTaskTagBucket } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Multi-tag chip input. Enter to add the typed value; Backspace at empty
   * input removes the last chip. Autocomplete dropdown fetches from
   * GET /api/internal-tasks/tasks/tags/ on focus (one-shot, cached).
   *
   * Tags are lowercased + trimmed before submit; duplicates ignored.
   */

  interface Props {
    tags: string[];
    placeholder?: string;
  }

  let { tags = $bindable([]), placeholder }: Props = $props();

  let query = $state("");
  let inputEl = $state<HTMLInputElement | null>(null);
  let containerEl = $state<HTMLDivElement | null>(null);
  let suggestions = $state<InternalTaskTagBucket[]>([]);
  let suggestionsLoaded = $state(false);
  let open = $state(false);

  async function loadSuggestions() {
    if (suggestionsLoaded) return;
    try {
      const res = await api.get<{ results: InternalTaskTagBucket[] }>(
        "/internal-tasks/tasks/tags/",
      );
      suggestions = res.results;
    } catch {
      suggestions = [];
    } finally {
      suggestionsLoaded = true;
    }
  }

  function focus() {
    open = true;
    void loadSuggestions();
  }

  function addTag(raw: string) {
    const tag = (raw || "").trim().toLowerCase();
    if (!tag) return;
    if (tags.includes(tag)) {
      query = "";
      return;
    }
    tags = [...tags, tag];
    query = "";
  }

  function removeAt(index: number) {
    tags = tags.filter((_, i) => i !== index);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      if (query.trim()) addTag(query);
    } else if (e.key === "Backspace" && !query && tags.length > 0) {
      tags = tags.slice(0, -1);
    } else if (e.key === "Escape") {
      open = false;
    }
  }

  function handleOutsideClick(e: MouseEvent) {
    if (!containerEl) return;
    if (!containerEl.contains(e.target as Node)) open = false;
  }

  $effect(() => {
    if (open) {
      document.addEventListener("click", handleOutsideClick);
      return () => document.removeEventListener("click", handleOutsideClick);
    }
  });

  let filteredSuggestions = $derived(
    suggestions
      .filter(
        (s) =>
          !tags.includes(s.tag) &&
          (query === "" || s.tag.includes(query.toLowerCase())),
      )
      .slice(0, 8),
  );
</script>

<div bind:this={containerEl} class="relative">
  <div
    class="flex flex-wrap items-center gap-1.5 rounded-2xl border border-neutral-200 bg-neutral-50 px-3 py-2.5 focus-within:border-neutral-800 focus-within:ring-2 focus-within:ring-neutral-800/10"
  >
    {#each tags as tag, i (tag)}
      <span class="inline-flex items-center gap-1 rounded-full bg-white border border-neutral-200 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
        {tag}
        <button
          type="button"
          onclick={() => removeAt(i)}
          aria-label={i18n.t("workspace.internal_tasks.tag.remove", { tag })}
          class="ml-0.5 text-neutral-400 hover:text-neutral-700"
        >
          <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </span>
    {/each}
    <input
      bind:this={inputEl}
      bind:value={query}
      onfocus={focus}
      onkeydown={handleKeydown}
      placeholder={tags.length === 0 ? (placeholder ?? i18n.t("workspace.internal_tasks.tag.placeholder")) : ""}
      class="min-w-[6rem] flex-1 bg-transparent text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
      type="text"
    />
  </div>

  {#if open && filteredSuggestions.length > 0}
    <ul
      class="absolute left-0 right-0 z-30 mt-1 max-h-56 overflow-auto rounded-2xl border border-neutral-200 bg-white py-1 shadow-md"
      role="listbox"
    >
      {#each filteredSuggestions as s}
        <li>
          <button
            type="button"
            onclick={() => addTag(s.tag)}
            class="flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-xs hover:bg-neutral-50"
            role="option"
            aria-selected={false}
          >
            <span class="text-neutral-800">{s.tag}</span>
            <span class="text-neutral-400 tabular-nums">{s.count}</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
