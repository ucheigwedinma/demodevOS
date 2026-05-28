<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { commandPalette } from "$lib/stores/commandPalette.svelte";
  import {
    SIDEBAR_MODULE_MAP,
    SIDEBAR_SUBITEM_MODULE_MAP,
    isModuleEnabled,
  } from "$lib/modules";
  import type {
    NavSection,
    SearchResultItem,
    SearchResultCategory,
    SearchResponse,
  } from "$lib/types";

  interface Props {
    sections: NavSection[];
    enabledModules: Set<string>;
  }

  let { sections, enabledModules }: Props = $props();

  // ── Local state ──────────────────────────────────────────────────────
  let query = $state("");
  let selectedIndex = $state(0);
  let loading = $state(false);
  let apiCategories = $state<SearchResultCategory[]>([]);
  let inputEl: HTMLInputElement | undefined = $state();
  let listEl: HTMLDivElement | undefined = $state();
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  // ── Quick Actions ────────────────────────────────────────────────────
  interface QuickAction {
    label: string;
    href: string;
    module?: string;
    icon: string; // SVG path(s)
  }

  const quickActions: QuickAction[] = [
    { label: "Create Project", href: "/projects/new", module: "projects", icon: "M12 4.5v15m7.5-7.5h-15" },
    { label: "New Employee Record", href: "/hr/employees", module: "hr", icon: "M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM3 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 9.374 21c-2.331 0-4.512-.645-6.374-1.766Z" },
    { label: "Post Vacancy", href: "/hr/vacancies", module: "hr", icon: "M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0" },
    { label: "New Document", href: "/documents/repository", module: "documents", icon: "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" },
    { label: "New Invoice", href: "/finance/invoices", module: "finance", icon: "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" },
    { label: "New Bill", href: "/finance/bills", module: "finance", icon: "M9 14.25l6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0c1.1.128 1.907 1.077 1.907 2.185ZM9.75 9h.008v.008H9.75V9Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 4.5h.008v.008h-.008V13.5Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" },
    { label: "New Lead", href: "/crm/leads", module: "crm", icon: "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" },
    { label: "New Support Ticket", href: "/support-desk/tickets", module: "support_desk", icon: "M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" },
    { label: "Go to Settings", href: "/settings", icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" },
    { label: "Go to Reports", href: "/reports", module: "analytics", icon: "M3.75 4.5h16.5v15H3.75v-15Zm3 3h10.5m-10.5 3.75h10.5m-10.5 3.75h6.75" },
  ];

  // ── Fuzzy matching ───────────────────────────────────────────────────
  function fuzzyScore(query: string, target: string): number {
    const q = query.toLowerCase();
    const t = target.toLowerCase();
    let qi = 0;
    let score = 0;
    let consecutive = 0;
    let firstMatchPos = -1;

    for (let ti = 0; ti < t.length && qi < q.length; ti++) {
      if (t[ti] === q[qi]) {
        if (firstMatchPos === -1) firstMatchPos = ti;
        consecutive++;
        score += consecutive * 2; // reward consecutive matches
        if (ti === 0 || t[ti - 1] === " " || t[ti - 1] === "/" || t[ti - 1] === "-") {
          score += 5; // word boundary bonus
        }
        qi++;
      } else {
        consecutive = 0;
      }
    }

    if (qi < q.length) return 0; // not all chars matched

    // Position bonus: earlier first match → higher score
    score += Math.max(0, 20 - firstMatchPos);
    return score;
  }

  // ── Derived: filtered quick actions ──────────────────────────────────
  let filteredActions = $derived.by(() => {
    const gated = quickActions.filter((a) =>
      !a.module || isModuleEnabled(enabledModules, a.module)
    );
    if (!query.trim()) return gated;
    return gated
      .map((a) => ({ action: a, score: fuzzyScore(query, a.label) }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((r) => r.action);
  });

  // ── Derived: page search results ─────────────────────────────────────
  interface PageResult {
    label: string;
    href: string;
    sectionLabel: string;
    score: number;
  }

  let pageResults = $derived.by((): PageResult[] => {
    if (!query.trim()) return [];
    const results: PageResult[] = [];
    for (const section of sections) {
      if (!isModuleEnabled(enabledModules, SIDEBAR_MODULE_MAP[section.key])) continue;
      // Score the section itself
      const sectionScore = fuzzyScore(query, section.label);
      if (sectionScore > 0) {
        results.push({
          label: section.label,
          href: section.href,
          sectionLabel: section.label,
          score: sectionScore,
        });
      }
      // Score sub-items
      for (const item of section.subItems) {
        if (!isModuleEnabled(enabledModules, SIDEBAR_SUBITEM_MODULE_MAP[item.href])) continue;
        const itemScore = fuzzyScore(query, item.label);
        if (itemScore > 0) {
          results.push({
            label: item.label,
            href: item.href,
            sectionLabel: section.label,
            score: itemScore,
          });
        }
      }
    }
    return results.sort((a, b) => b.score - a.score).slice(0, 8);
  });

  // ── Flatten all results into a single navigable list ─────────────────
  interface FlatItem {
    kind: "recent" | "action" | "page" | "entity";
    label: string;
    subtitle?: string;
    href: string;
    category?: string;
    icon?: string;
  }

  let flatItems = $derived.by((): FlatItem[] => {
    const items: FlatItem[] = [];

    if (!query.trim()) {
      // Show recent searches as navigable items
      for (const q of commandPalette.recentSearches) {
        items.push({ kind: "recent", label: q, href: "", category: "Recent" });
      }
      // Show quick actions
      for (const a of filteredActions) {
        items.push({ kind: "action", label: a.label, href: a.href, category: "Quick Actions", icon: a.icon });
      }
    } else {
      // Quick action matches
      for (const a of filteredActions) {
        items.push({ kind: "action", label: a.label, href: a.href, category: "Quick Actions", icon: a.icon });
      }
      // Page matches
      for (const p of pageResults) {
        items.push({ kind: "page", label: p.label, subtitle: p.sectionLabel, href: p.href, category: "Pages" });
      }
      // API entity results
      for (const cat of apiCategories) {
        for (const r of cat.results) {
          items.push({ kind: "entity", label: r.title, subtitle: r.subtitle, href: r.href, category: cat.label });
        }
      }
    }

    return items;
  });

  // ── API search (debounced) ───────────────────────────────────────────
  function searchAPI(q: string) {
    if (debounceTimer) clearTimeout(debounceTimer);
    if (q.trim().length < 2) {
      apiCategories = [];
      loading = false;
      return;
    }
    loading = true;
    debounceTimer = setTimeout(async () => {
      try {
        const res = await api.get<SearchResponse>("/search/", { q: q.trim() });
        // Only update if query hasn't changed
        if (query.trim() === q.trim()) {
          apiCategories = res.categories;
        }
      } catch {
        apiCategories = [];
      } finally {
        if (query.trim() === q.trim()) loading = false;
      }
    }, 300);
  }

  // ── Watch query changes ──────────────────────────────────────────────
  $effect(() => {
    const q = query;
    selectedIndex = 0;
    searchAPI(q);
  });

  // ── Focus input when opened ──────────────────────────────────────────
  $effect(() => {
    if (commandPalette.isOpen) {
      // Slight delay so the DOM is ready
      requestAnimationFrame(() => inputEl?.focus());
    } else {
      query = "";
      apiCategories = [];
      loading = false;
      selectedIndex = 0;
    }
  });

  // ── Navigation helpers ───────────────────────────────────────────────
  function navigateTo(item: FlatItem) {
    if (item.kind === "recent") {
      // Re-run the recent search
      query = item.label;
      return;
    }
    if (query.trim()) {
      commandPalette.addRecentSearch(query.trim());
    }
    commandPalette.close();
    goto(item.href);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      commandPalette.close();
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, flatItems.length - 1);
      scrollSelectedIntoView();
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
      scrollSelectedIntoView();
      return;
    }

    if (e.key === "Enter" && flatItems.length > 0) {
      e.preventDefault();
      navigateTo(flatItems[selectedIndex]);
      return;
    }
  }

  function scrollSelectedIntoView() {
    requestAnimationFrame(() => {
      const el = listEl?.querySelector(`[data-index="${selectedIndex}"]`);
      el?.scrollIntoView({ block: "nearest" });
    });
  }

  // ── Highlight matched chars ──────────────────────────────────────────
  function highlightMatch(text: string, q: string): { text: string; match: boolean }[] {
    if (!q.trim()) return [{ text, match: false }];
    const lower = text.toLowerCase();
    const qLower = q.toLowerCase();
    const segments: { text: string; match: boolean }[] = [];
    let qi = 0;
    let lastEnd = 0;

    for (let i = 0; i < text.length && qi < qLower.length; i++) {
      if (lower[i] === qLower[qi]) {
        if (i > lastEnd) {
          segments.push({ text: text.slice(lastEnd, i), match: false });
        }
        segments.push({ text: text[i], match: true });
        lastEnd = i + 1;
        qi++;
      }
    }
    if (lastEnd < text.length) {
      segments.push({ text: text.slice(lastEnd), match: false });
    }
    return segments;
  }

  // ── Category grouping for display ────────────────────────────────────
  function getCategories(items: FlatItem[]): { label: string; startIndex: number; items: FlatItem[] }[] {
    const cats: { label: string; startIndex: number; items: FlatItem[] }[] = [];
    let currentCat = "";
    let globalIndex = 0;
    for (const item of items) {
      const cat = item.category || "Results";
      if (cat !== currentCat) {
        currentCat = cat;
        cats.push({ label: cat, startIndex: globalIndex, items: [] });
      }
      cats[cats.length - 1].items.push(item);
      globalIndex++;
    }
    return cats;
  }

  let groupedCategories = $derived(getCategories(flatItems));
</script>

{#if commandPalette.isOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-60 flex items-start justify-center pt-[12vh]"
    onkeydown={handleKeydown}
  >
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
      onclick={() => commandPalette.close()}
      tabindex={-1}
      aria-label="Close search"
    ></button>

    <!-- Modal -->
    <div
      class="relative w-full max-w-2xl mx-4 bg-white rounded-xl shadow-2xl border border-neutral-200 overflow-hidden animate-palette-in"
    >
      <!-- Search input -->
      <div class="flex items-center gap-3 px-4 py-3 border-b border-neutral-200">
        <svg class="w-5 h-5 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          bind:this={inputEl}
          bind:value={query}
          type="text"
          placeholder="Search pages, records, actions..."
          class="flex-1 text-sm text-neutral-900 placeholder:text-neutral-400 outline-none bg-transparent font-[Raleway]"
          spellcheck="false"
          autocomplete="off"
        />
        {#if query}
          <button
            onclick={() => { query = ""; inputEl?.focus(); }}
            class="p-1 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Clear search"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        {/if}
        <kbd class="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium text-neutral-400 bg-neutral-100 rounded border border-neutral-200">
          ESC
        </kbd>
      </div>

      <!-- Results -->
      <div bind:this={listEl} class="max-h-[60vh] overflow-y-auto overscroll-contain palette-scroll">
        {#if flatItems.length === 0 && query.trim() && !loading}
          <div class="px-4 py-12 text-center">
            <svg class="w-10 h-10 mx-auto text-neutral-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <p class="text-sm text-neutral-500">No results for "<span class="font-medium text-neutral-700">{query}</span>"</p>
            <p class="text-xs text-neutral-400 mt-1">Try a different search term</p>
          </div>
        {:else if flatItems.length === 0 && !query.trim() && commandPalette.recentSearches.length === 0 && filteredActions.length === 0}
          <div class="px-4 py-12 text-center">
            <p class="text-sm text-neutral-500">Start typing to search...</p>
          </div>
        {:else}
          {#each groupedCategories as category}
            <div class="py-1">
              <div class="px-4 py-1.5 flex items-center justify-between">
                <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{category.label}</span>
                {#if category.label === "Recent" && !query.trim()}
                  <button
                    onclick={() => commandPalette.clearRecentSearches()}
                    class="text-[10px] text-neutral-400 hover:text-neutral-600 transition-colors"
                  >
                    Clear
                  </button>
                {/if}
              </div>
              {#each category.items as item, i}
                {@const globalIdx = category.startIndex + i}
                <button
                  data-index={globalIdx}
                  class="w-full flex items-center gap-3 px-4 py-2 text-left transition-colors {globalIdx === selectedIndex ? 'bg-neutral-100' : 'hover:bg-neutral-50'}"
                  onclick={() => navigateTo(item)}
                  onmouseenter={() => { selectedIndex = globalIdx; }}
                >
                  <!-- Icon -->
                  {#if item.kind === "recent"}
                    <svg class="w-4 h-4 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                    </svg>
                  {:else if item.kind === "action" && item.icon}
                    <svg class="w-4 h-4 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
                    </svg>
                  {:else if item.kind === "page"}
                    <svg class="w-4 h-4 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                  {:else}
                    <svg class="w-4 h-4 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 0 0-1.883 2.542l.857 6a2.25 2.25 0 0 0 2.227 1.932H19.05a2.25 2.25 0 0 0 2.227-1.932l.857-6a2.25 2.25 0 0 0-1.883-2.542m-16.5 0V6A2.25 2.25 0 0 1 6 3.75h3.879a1.5 1.5 0 0 1 1.06.44l2.122 2.12a1.5 1.5 0 0 0 1.06.44H18A2.25 2.25 0 0 1 20.25 9v.776" />
                    </svg>
                  {/if}

                  <!-- Text -->
                  <div class="flex-1 min-w-0">
                    <div class="text-sm text-neutral-800 truncate">
                      {#each highlightMatch(item.label, query) as seg}
                        {#if seg.match}
                          <span class="font-semibold text-neutral-900">{seg.text}</span>
                        {:else}
                          {seg.text}
                        {/if}
                      {/each}
                    </div>
                    {#if item.subtitle && item.kind !== "recent"}
                      <div class="text-xs text-neutral-400 truncate">{item.subtitle}</div>
                    {/if}
                  </div>

                  <!-- Remove recent item -->
                  {#if item.kind === "recent"}
                    <span
                      role="button"
                      tabindex="-1"
                      onclick={(e: MouseEvent) => { e.stopPropagation(); commandPalette.removeRecentSearch(item.label); }}
                      onkeydown={(e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); e.preventDefault(); commandPalette.removeRecentSearch(item.label); } }}
                      class="p-0.5 rounded text-neutral-300 hover:text-neutral-500 transition-colors cursor-pointer"
                      aria-label="Remove"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                      </svg>
                    </span>
                  {/if}

                  <!-- Enter hint for selected -->
                  {#if globalIdx === selectedIndex}
                    <kbd class="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium text-neutral-400 bg-neutral-200/60 rounded">
                      ↵
                    </kbd>
                  {/if}
                </button>
              {/each}
            </div>
          {/each}

          <!-- Loading skeleton for API results -->
          {#if loading && query.trim().length >= 2}
            <div class="py-1 px-4">
              <div class="py-1.5">
                <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Searching records...</span>
              </div>
              {#each { length: 3 } as _}
                <div class="flex items-center gap-3 py-2 animate-pulse">
                  <div class="w-4 h-4 rounded bg-neutral-200"></div>
                  <div class="flex-1 space-y-1.5">
                    <div class="h-3.5 w-48 rounded bg-neutral-200"></div>
                    <div class="h-2.5 w-32 rounded bg-neutral-100"></div>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </div>

      <!-- Footer -->
      <div class="px-4 py-2 border-t border-neutral-100 flex items-center gap-4 text-[10px] text-neutral-400">
        <span class="flex items-center gap-1">
          <kbd class="px-1 py-0.5 bg-neutral-100 rounded border border-neutral-200 font-medium">↑</kbd>
          <kbd class="px-1 py-0.5 bg-neutral-100 rounded border border-neutral-200 font-medium">↓</kbd>
          Navigate
        </span>
        <span class="flex items-center gap-1">
          <kbd class="px-1 py-0.5 bg-neutral-100 rounded border border-neutral-200 font-medium">↵</kbd>
          Open
        </span>
        <span class="flex items-center gap-1">
          <kbd class="px-1 py-0.5 bg-neutral-100 rounded border border-neutral-200 font-medium">Esc</kbd>
          Close
        </span>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes palette-in {
    from {
      opacity: 0;
      transform: scale(0.98) translateY(-8px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .animate-palette-in {
    animation: palette-in 150ms ease-out;
  }

  .animate-fade-in {
    animation: fade-in 100ms ease-out;
  }

  /* Black scrollbar on hover */
  div :global([bind\:this]) {
    scrollbar-width: thin;
    scrollbar-color: transparent transparent;
  }

  .palette-scroll {
    scrollbar-width: thin;
    scrollbar-color: transparent transparent;
    transition: scrollbar-color 0.2s;
  }

  .palette-scroll:hover {
    scrollbar-color: rgb(23 23 23) transparent;
  }

  .palette-scroll::-webkit-scrollbar {
    width: 6px;
  }

  .palette-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .palette-scroll::-webkit-scrollbar-thumb {
    background: transparent;
    border-radius: 3px;
    transition: background 0.2s;
  }

  .palette-scroll:hover::-webkit-scrollbar-thumb {
    background: rgb(23 23 23);
  }
</style>
