<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { can } from "$lib/permissions";
  import { toast } from "$lib/stores/toast.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    SupportKnowledgeArticleDetail,
    SupportKnowledgeArticleListItem,
    SupportKnowledgeArticleStatus,
    SupportKnowledgeBaseOverview,
  } from "$lib/types";

  type StatusFilter = "all" | SupportKnowledgeArticleStatus;

  type VersionTimelineEvent = {
    label: string;
    detail: string;
    at: string;
  };

  const pageSize = 12;
  const statusFilterOptions: Array<{ key: StatusFilter; label: string }> = [
    { key: "published", label: "Published" },
    { key: "in_review", label: "In Review" },
    { key: "draft", label: "Draft" },
    { key: "archived", label: "Archived" },
    { key: "all", label: "All" },
  ];

  const categoryDefaults = [
    "Account & Login",
    "System Usage",
    "HR Policies",
    "Finance Procedures",
    "IT Support",
    "Facilities",
    "Investment Portfolio",
  ];

  let loadingOverview = $state(true);
  let loadingList = $state(true);
  let detailLoading = $state(false);

  let actionKey = $state("");
  let errorMessage = $state("");

  let overview = $state<SupportKnowledgeBaseOverview | null>(null);
  let articles = $state<SupportKnowledgeArticleListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);

  let search = $state("");
  let selectedStatus = $state<StatusFilter>("published");
  let selectedCategory = $state("");

  let selectedArticleId = $state<number | null>(null);
  let selectedArticle = $state<SupportKnowledgeArticleDetail | null>(null);

  let ticketSuggestionQuery = $state("");
  let ticketSuggestionLoading = $state(false);
  let ticketSuggestionError = $state("");
  let ticketSuggestions = $state<SupportKnowledgeArticleListItem[]>([]);

  let showArticleModal = $state(false);
  let articleModalMode = $state<"create" | "edit">("create");
  let savingArticle = $state(false);
  let deletingArticle = $state(false);
  let articleForm = $state({
    title: "",
    summary: "",
    body: "",
    category: "",
    visibility: "internal" as "internal" | "portal" | "public",
    status: "draft" as "draft" | "in_review" | "published" | "archived",
  });

  const canCreate = $derived(can("support_desk.knowledge_base", "create"));
  const canEditArticle = $derived(can("support_desk.knowledge_base", "edit"));
  const canDeleteArticle = $derived(can("support_desk.knowledge_base", "delete"));

  let listSearchDebounceTimer: ReturnType<typeof setTimeout>;
  let ticketSuggestionDebounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let index = start; index <= end; index += 1) pages.push(index);
    return pages;
  });

  let categoryOptions = $derived.by(() => {
    const fromData = new Set<string>(categoryDefaults);

    for (const article of articles) {
      if (article.category?.trim()) fromData.add(article.category.trim());
    }

    for (const article of overview?.top_articles ?? []) {
      if (article.category?.trim()) fromData.add(article.category.trim());
    }

    return Array.from(fromData).sort((a, b) => a.localeCompare(b));
  });

  let relatedArticles = $derived.by(() => {
    if (!selectedArticle) return [];
    const currentCategory = selectedArticle.category?.trim();
    if (!currentCategory) return [];
    const selectedId = selectedArticle.id;

    return articles
      .filter(
        (article) =>
          article.id !== selectedId &&
          article.category?.trim() === currentCategory,
      )
      .slice(0, 4);
  });

  let attachmentLinks = $derived(
    selectedArticle ? extractAttachmentLinks(selectedArticle.body) : [],
  );

  let versionTimeline = $derived(
    selectedArticle ? buildVersionTimeline(selectedArticle) : [],
  );

  let articleHelpfulRatio = $derived.by(() => {
    if (!selectedArticle) return null;
    const totalVotes =
      selectedArticle.helpful_votes + selectedArticle.not_helpful_votes;
    if (totalVotes === 0) return null;
    return Math.round((selectedArticle.helpful_votes / totalVotes) * 10000) / 100;
  });

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function isBusy(key: string): boolean {
    return actionKey === key;
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatDate(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }


  function extractAttachmentLinks(body: string): string[] {
    const matches = body.match(/https?:\/\/[^\s)\]}>]+/g) ?? [];
    return Array.from(new Set(matches)).slice(0, 8);
  }

  function buildVersionTimeline(
    article: SupportKnowledgeArticleDetail,
  ): VersionTimelineEvent[] {
    const events: VersionTimelineEvent[] = [
      {
        label: "Draft Created",
        detail: "Initial article draft was created.",
        at: article.created_at,
      },
      {
        label: "Published",
        detail: "Article became visible in the help center.",
        at: article.published_at ?? "",
      },
      {
        label: "Last Review",
        detail: "Most recent review timestamp recorded.",
        at: article.last_reviewed_at ?? "",
      },
      {
        label: "Latest Update",
        detail: "Most recent content update was saved.",
        at: article.updated_at,
      },
    ];

    return events
      .filter((event) => Boolean(event.at))
      .sort((left, right) => new Date(right.at).getTime() - new Date(left.at).getTime());
  }

  function buildArticleParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
    };

    if (search.trim()) params.search = search.trim();
    if (selectedCategory) params.category = selectedCategory;
    if (selectedStatus !== "all") params.status = selectedStatus;

    return params;
  }

  function syncListRow(articleDetail: SupportKnowledgeArticleDetail) {
    articles = articles.map((article) =>
      article.id === articleDetail.id
        ? {
            ...article,
            title: articleDetail.title,
            slug: articleDetail.slug,
            summary: articleDetail.summary,
            category: articleDetail.category,
            status: articleDetail.status,
            status_display: articleDetail.status_display,
            visibility: articleDetail.visibility,
            visibility_display: articleDetail.visibility_display,
            owner: articleDetail.owner,
            owner_name: articleDetail.owner_name,
            reviewer: articleDetail.reviewer,
            reviewer_name: articleDetail.reviewer_name,
            published_at: articleDetail.published_at,
            last_reviewed_at: articleDetail.last_reviewed_at,
            next_review_due_at: articleDetail.next_review_due_at,
            view_count: articleDetail.view_count,
            helpful_votes: articleDetail.helpful_votes,
            not_helpful_votes: articleDetail.not_helpful_votes,
            created_at: articleDetail.created_at,
            updated_at: articleDetail.updated_at,
          }
        : article,
    );
  }

  async function loadOverview() {
    loadingOverview = true;
    try {
      overview = await api.get<SupportKnowledgeBaseOverview>(
        "/support-desk/knowledge-base/overview/",
      );
    } catch (error) {
      overview = null;
      toast.error(
        "Knowledge overview unavailable",
        parseError(error, "Could not load knowledge base overview metrics."),
      );
    } finally {
      loadingOverview = false;
    }
  }

  async function loadArticleDetail(articleId: number, recordView = true) {
    detailLoading = true;
    try {
      let detail: SupportKnowledgeArticleDetail;

      if (recordView) {
        detail = await api.post<SupportKnowledgeArticleDetail>(
          `/support-desk/knowledge-base/articles/${articleId}/record-view/`,
          {},
        );
      } else {
        detail = await api.get<SupportKnowledgeArticleDetail>(
          `/support-desk/knowledge-base/articles/${articleId}/`,
        );
      }

      selectedArticle = detail;
      selectedArticleId = detail.id;
      syncListRow(detail);
    } catch (error) {
      selectedArticle = null;
      toast.error(
        "Article unavailable",
        parseError(error, "Could not load this knowledge article."),
      );
    } finally {
      detailLoading = false;
    }
  }

  async function loadArticles(preferredArticleId?: number) {
    loadingList = true;
    errorMessage = "";

    try {
      const response = await api.get<PaginatedResponse<SupportKnowledgeArticleListItem>>(
        "/support-desk/knowledge-base/articles/",
        buildArticleParams(),
      );
      articles = response.results;
      totalCount = response.count;

      if (response.results.length === 0) {
        selectedArticleId = null;
        selectedArticle = null;
        return;
      }

      const preferredInResult =
        preferredArticleId !== undefined &&
        response.results.some((article) => article.id === preferredArticleId);

      const selectedStillVisible =
        selectedArticleId !== null &&
        response.results.some((article) => article.id === selectedArticleId);

      const nextArticleId = preferredInResult
        ? preferredArticleId!
        : selectedStillVisible
          ? selectedArticleId!
          : response.results[0].id;

      await loadArticleDetail(nextArticleId, false);
    } catch (error) {
      articles = [];
      totalCount = 0;
      selectedArticleId = null;
      selectedArticle = null;
      errorMessage = parseError(
        error,
        "Could not load knowledge base articles.",
      );
    } finally {
      loadingList = false;
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(listSearchDebounceTimer);
    listSearchDebounceTimer = setTimeout(() => {
      currentPage = 1;
      void loadArticles();
    }, 260);
  }

  function handleFilterChange() {
    currentPage = 1;
    void loadArticles();
  }

  function openCreateModal() {
    articleForm = {
      title: "",
      summary: "",
      body: "",
      category: "",
      visibility: "internal",
      status: "draft",
    };
    articleModalMode = "create";
    showArticleModal = true;
  }

  function openEditModal() {
    if (!selectedArticle) return;
    articleForm = {
      title: selectedArticle.title,
      summary: selectedArticle.summary,
      body: selectedArticle.body,
      category: selectedArticle.category,
      visibility: selectedArticle.visibility,
      status: selectedArticle.status,
    };
    articleModalMode = "edit";
    showArticleModal = true;
  }

  function closeArticleModal() {
    showArticleModal = false;
  }

  async function handleSaveArticle() {
    if (savingArticle) return;
    if (!articleForm.title.trim()) {
      toast.error("Validation error", "Title is required.");
      return;
    }
    if (!articleForm.body.trim()) {
      toast.error("Validation error", "Body content is required.");
      return;
    }

    savingArticle = true;
    try {
      const payload = {
        title: articleForm.title.trim(),
        summary: articleForm.summary.trim(),
        body: articleForm.body.trim(),
        category: articleForm.category,
        visibility: articleForm.visibility,
        status: articleForm.status,
      };

      if (articleModalMode === "create") {
        const created = await api.post<SupportKnowledgeArticleDetail>(
          "/support-desk/knowledge-base/articles/",
          payload,
        );
        showArticleModal = false;
        toast.success("Article created", `"${created.title}" has been saved.`);
        await Promise.all([loadOverview(), loadArticles(created.id)]);
      } else {
        const updated = await api.patch<SupportKnowledgeArticleDetail>(
          `/support-desk/knowledge-base/articles/${selectedArticle!.id}/`,
          payload,
        );
        selectedArticle = updated;
        syncListRow(updated);
        showArticleModal = false;
        toast.success("Article updated", `"${updated.title}" has been saved.`);
        await loadOverview();
      }
    } catch (error) {
      toast.error(
        "Save failed",
        parseError(error, "Could not save the article."),
      );
    } finally {
      savingArticle = false;
    }
  }

  async function handleDeleteArticle() {
    if (!selectedArticle || deletingArticle) return;
    if (!confirm("Are you sure you want to delete this article? This cannot be undone.")) return;

    deletingArticle = true;
    try {
      await api.delete(`/support-desk/knowledge-base/articles/${selectedArticle.id}/`);
      toast.success("Article deleted", `"${selectedArticle.title}" has been removed.`);
      selectedArticle = null;
      selectedArticleId = null;
      await Promise.all([loadOverview(), loadArticles()]);
    } catch (error) {
      toast.error(
        "Delete failed",
        parseError(error, "Could not delete the article."),
      );
    } finally {
      deletingArticle = false;
    }
  }

  function resetFilters() {
    search = "";
    selectedStatus = "published";
    selectedCategory = "";
    currentPage = 1;
    void loadArticles();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    void loadArticles();
  }

  async function handleRateArticle(helpful: boolean) {
    if (!selectedArticleId) return;

    actionKey = helpful ? "rate-helpful" : "rate-not-helpful";
    try {
      const updated = await api.post<SupportKnowledgeArticleDetail>(
        `/support-desk/knowledge-base/articles/${selectedArticleId}/feedback/`,
        { helpful },
      );
      selectedArticle = updated;
      syncListRow(updated);
      toast.success(
        "Feedback recorded",
        helpful
          ? "Marked article as helpful."
          : "Marked article as not helpful.",
      );
      await loadOverview();
    } catch (error) {
      toast.error(
        "Rating failed",
        parseError(error, "Could not save article feedback."),
      );
    } finally {
      actionKey = "";
    }
  }

  async function handleLifecycleAction(
    key: string,
    endpoint: string,
    successMessage: string,
  ) {
    if (!selectedArticleId) return;

    actionKey = key;
    try {
      const updated = await api.post<SupportKnowledgeArticleDetail>(
        `/support-desk/knowledge-base/articles/${selectedArticleId}/${endpoint}/`,
        {},
      );
      selectedArticle = updated;
      syncListRow(updated);
      toast.success("Article updated", successMessage);
      await Promise.all([loadOverview(), loadArticles(updated.id)]);
    } catch (error) {
      toast.error(
        "Action failed",
        parseError(error, "Could not update article lifecycle state."),
      );
    } finally {
      actionKey = "";
    }
  }

  function handleTicketSuggestionInput(value: string) {
    ticketSuggestionQuery = value;
    clearTimeout(ticketSuggestionDebounceTimer);
    ticketSuggestionDebounceTimer = setTimeout(() => {
      void loadTicketSuggestions(ticketSuggestionQuery);
    }, 280);
  }

  async function loadTicketSuggestions(query: string) {
    const trimmed = query.trim();

    if (trimmed.length < 3) {
      ticketSuggestions = [];
      ticketSuggestionError = "";
      return;
    }

    ticketSuggestionLoading = true;
    ticketSuggestionError = "";

    try {
      const response = await api.get<PaginatedResponse<SupportKnowledgeArticleListItem>>(
        "/support-desk/knowledge-base/articles/",
        {
          status: "published",
          page_size: "6",
          search: trimmed,
        },
      );
      ticketSuggestions = response.results;
    } catch (error) {
      ticketSuggestions = [];
      ticketSuggestionError = parseError(
        error,
        "Could not load suggestions for this ticket subject.",
      );
    } finally {
      ticketSuggestionLoading = false;
    }
  }

  onMount(async () => {
    const params = new URLSearchParams(window.location.search);
    const requestedArticle = Number(params.get("article") || "");
    const preferredArticleId = Number.isFinite(requestedArticle) && requestedArticle > 0
      ? requestedArticle
      : undefined;

    await Promise.all([loadOverview(), loadArticles(preferredArticleId)]);
  });
</script>

<div class="space-y-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <h1 class="text-2xl font-bold text-neutral-800">Support Knowledge Center</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Search and review support guidance to reduce ticket volume. This page is wired to
          <code class="rounded bg-white px-1 py-0.5 text-xs">/api/support-desk/knowledge-base/*</code>
          endpoints for article discovery, rating, and lifecycle actions.
        </p>
        {#if canCreate}
          <button
            type="button"
            onclick={openCreateModal}
            class="mt-2 inline-flex items-center gap-2 rounded-2xl bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800 transition-colors"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Article
          </button>
        {/if}
      </div>

      <div class="grid w-full max-w-sm gap-3 sm:grid-cols-2">
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Articles</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.total_articles ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Published</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.published_articles ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Total Views</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.total_views ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Helpful Ratio</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">
            {#if overview?.helpful_feedback_ratio !== null && overview?.helpful_feedback_ratio !== undefined}
              {overview.helpful_feedback_ratio}%
            {:else}
              --
            {/if}
          </p>
        </div>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-neutral-950">Suggested Articles for Ticket Creation</h2>
        <p class="mt-1 text-sm text-neutral-500">Use this live search to recommend self-service content before logging new tickets.</p>
      </div>
    </div>

    <div class="mt-4">
      <input
        type="text"
        value={ticketSuggestionQuery}
        oninput={(event) => handleTicketSuggestionInput((event.currentTarget as HTMLInputElement).value)}
        placeholder="Type a ticket subject or issue description..."
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
    </div>

    {#if ticketSuggestionLoading}
      <div class="mt-4 flex items-center gap-2 text-sm text-neutral-500">
        <div class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-700"></div>
        Looking up suggested articles...
      </div>
    {:else if ticketSuggestionError}
      <p class="mt-4 text-sm text-red-700">{ticketSuggestionError}</p>
    {:else if ticketSuggestionQuery.trim().length >= 3 && ticketSuggestions.length === 0}
      <p class="mt-4 text-sm text-neutral-500">No matching published articles found.</p>
    {:else if ticketSuggestions.length > 0}
      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {#each ticketSuggestions as article}
          <button
            type="button"
            onclick={() => loadArticleDetail(article.id)}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-left hover:border-neutral-300 hover:bg-white"
          >
            <p class="text-sm font-semibold text-neutral-800">{article.title}</p>
            <p class="mt-1 text-xs text-neutral-500">{article.category || "General"} • {article.view_count} views</p>
            <p class="mt-2 text-xs text-neutral-600">{article.summary || "No summary provided."}</p>
          </button>
        {/each}
      </div>
    {/if}
  </section>

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.95fr)]">
    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label class="block xl:col-span-2">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Search Articles</span>
            <input
              type="text"
              value={search}
              oninput={(event) => handleSearchInput((event.currentTarget as HTMLInputElement).value)}
              placeholder="Search by title, slug, category, or content"
              class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            />
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Status</span>
            <select bind:value={selectedStatus} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              {#each statusFilterOptions as option}
                <option value={option.key}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Category</span>
            <select bind:value={selectedCategory} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All categories</option>
              {#each categoryOptions as option}
                <option value={option}>{option}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="mt-4 flex justify-end">
          <button type="button" onclick={resetFilters} class="text-sm font-semibold text-neutral-500 hover:text-neutral-800">Reset filters</button>
        </div>

        <div class="mt-6 overflow-hidden rounded-3xl border border-neutral-200">
          {#if loadingList}
            <div class="flex items-center justify-center py-16">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if errorMessage}
            <div class="px-6 py-14 text-center">
              <h3 class="text-base font-semibold text-red-900">Knowledge base unavailable</h3>
              <p class="mt-2 text-sm text-red-700">{errorMessage}</p>
              <button type="button" onclick={() => loadArticles()} class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100">
                Retry
              </button>
            </div>
          {:else if articles.length === 0}
            <div class="px-6 py-14 text-center">
              <h3 class="text-base font-semibold text-neutral-950">No articles found</h3>
              <p class="mt-2 text-sm leading-6 text-neutral-500">Adjust filters or add new knowledge articles.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[980px] w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Title</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Category</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Status</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Rating</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {#each articles as article}
                    <tr
                      class={`cursor-pointer border-b border-neutral-100 transition-colors hover:bg-neutral-50 ${selectedArticleId === article.id ? "bg-sky-50/55" : "bg-white"}`}
                      onclick={() => loadArticleDetail(article.id)}
                    >
                      <td class="px-4 py-4">
                        <p class="text-sm font-semibold text-neutral-800">{article.title}</p>
                        <p class="mt-1 text-xs text-neutral-500">/{article.slug}</p>
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{article.category || "General"}</td>
                      <td class="px-4 py-4 text-sm">
                        <StatusBadge status={article.status} label={article.status_display} />
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">
                        {#if article.helpful_votes + article.not_helpful_votes > 0}
                          {Math.round((article.helpful_votes / (article.helpful_votes + article.not_helpful_votes)) * 100)}%
                        {:else}
                          --
                        {/if}
                      </td>
                      <td class="whitespace-nowrap px-4 py-4 text-sm text-neutral-500">{formatDateTime(article.updated_at)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>

        {#if articles.length > 0}
          <div class="mt-6 flex flex-wrap items-center justify-between gap-4">
            <p class="text-sm text-neutral-500">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} articles
            </p>
            <div class="flex items-center gap-2">
              <button type="button" onclick={() => goToPage(currentPage - 1)} disabled={currentPage === 1} class="rounded-xl border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50">
                Previous
              </button>
              {#each pageNumbers as page}
                <button
                  type="button"
                  onclick={() => goToPage(page)}
                  class={`rounded-xl px-3 py-2 text-sm font-semibold ${page === currentPage ? "bg-neutral-800 text-white" : "border border-neutral-200 text-neutral-700"}`}
                >
                  {page}
                </button>
              {/each}
              <button type="button" onclick={() => goToPage(currentPage + 1)} disabled={currentPage === totalPages} class="rounded-xl border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50">
                Next
              </button>
            </div>
          </div>
        {/if}
      </article>
    </section>

    <aside class="space-y-6">
      {#if detailLoading}
        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div class="flex items-center justify-center py-12">
            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
          </div>
        </article>
      {:else if !selectedArticle}
        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-5 py-6">
            <p class="text-sm font-medium text-neutral-800">No article selected</p>
            <p class="mt-2 text-sm leading-6 text-neutral-500">Select an article to view content, rate helpfulness, and manage lifecycle status.</p>
          </div>
        </article>
      {:else}
        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div class="space-y-4">
            <div>
              <h2 class="text-xl font-semibold text-neutral-950">{selectedArticle.title}</h2>
              <p class="mt-1 text-xs text-neutral-500">/{selectedArticle.slug}</p>
              <p class="mt-2 text-sm leading-6 text-neutral-600">{selectedArticle.summary || "No summary provided."}</p>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <StatusBadge status={selectedArticle.status} label={selectedArticle.status_display} />
                <span class="inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-semibold text-neutral-700">
                  {selectedArticle.visibility_display}
                </span>
              </div>
              {#if canEditArticle || canDeleteArticle}
                <div class="flex items-center gap-2">
                  {#if canEditArticle}
                    <button
                      type="button"
                      onclick={openEditModal}
                      class="rounded-xl border border-neutral-200 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50 transition-colors"
                    >
                      Edit
                    </button>
                  {/if}
                  {#if canDeleteArticle}
                    <button
                      type="button"
                      onclick={handleDeleteArticle}
                      disabled={deletingArticle}
                      class="rounded-xl border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:border-red-300 hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      {deletingArticle ? "Deleting..." : "Delete"}
                    </button>
                  {/if}
                </div>
              {/if}
            </div>

            <div class="grid gap-2 sm:grid-cols-2">
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Category</p>
                <p class="mt-1 text-sm font-medium text-neutral-800">{selectedArticle.category || "General"}</p>
              </div>
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Author</p>
                <p class="mt-1 text-sm font-medium text-neutral-800">{selectedArticle.owner_name || "Unknown"}</p>
              </div>
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Last Updated</p>
                <p class="mt-1 text-sm font-medium text-neutral-800">{formatDateTime(selectedArticle.updated_at)}</p>
              </div>
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Views</p>
                <p class="mt-1 text-sm font-medium text-neutral-800">{selectedArticle.view_count}</p>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <button type="button" onclick={() => handleRateArticle(true)} disabled={isBusy("rate-helpful")} class="rounded-2xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("rate-helpful") ? "Saving..." : "Helpful"}
              </button>
              <button type="button" onclick={() => handleRateArticle(false)} disabled={isBusy("rate-not-helpful")} class="rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("rate-not-helpful") ? "Saving..." : "Not Helpful"}
              </button>
            </div>

            <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Article Rating</p>
              <p class="mt-1 text-sm text-neutral-700">
                {#if articleHelpfulRatio !== null}
                  {articleHelpfulRatio}% helpful based on {selectedArticle.helpful_votes + selectedArticle.not_helpful_votes} rating(s).
                {:else}
                  No ratings submitted yet.
                {/if}
              </p>
            </div>

            <div class="grid gap-2 sm:grid-cols-3">
              <button
                type="button"
                onclick={() => handleLifecycleAction("submit-review", "submit-review", "Article moved to review state.")}
                disabled={isBusy("submit-review") || selectedArticle.status === "in_review" || selectedArticle.status === "archived"}
                class="rounded-xl border border-neutral-300 bg-white px-3 py-2 text-xs font-semibold text-neutral-700 hover:border-neutral-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isBusy("submit-review") ? "Updating..." : "Submit Review"}
              </button>
              <button
                type="button"
                onclick={() => handleLifecycleAction("publish", "publish", "Article published.")}
                disabled={isBusy("publish") || selectedArticle.status === "published" || selectedArticle.status === "archived"}
                class="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isBusy("publish") ? "Publishing..." : "Publish"}
              </button>
              <button
                type="button"
                onclick={() => handleLifecycleAction("archive", "archive", "Article archived.")}
                disabled={isBusy("archive") || selectedArticle.status === "archived"}
                class="rounded-xl border border-neutral-300 bg-neutral-100 px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isBusy("archive") ? "Archiving..." : "Archive"}
              </button>
            </div>

            <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Content</p>
              <pre class="mt-3 whitespace-pre-wrap wrap-break-word text-sm leading-6 text-neutral-800">{selectedArticle.body || "No article content."}</pre>
            </div>
          </div>
        </article>

        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h3 class="text-base font-semibold text-neutral-950">Article Structure</h3>
          <p class="mt-1 text-sm text-neutral-500">Title, category, content, attachments, related articles, author, and update metadata.</p>

          <div class="mt-4 space-y-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Attachments</p>
              <div class="mt-2 space-y-2">
                {#if attachmentLinks.length === 0}
                  <p class="rounded-xl border border-dashed border-neutral-300 bg-neutral-50 px-3 py-3 text-sm text-neutral-500">No attachment links detected in content.</p>
                {:else}
                  {#each attachmentLinks as link}
                    <a href={link} target="_blank" rel="noreferrer" class="block rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-sky-700 hover:border-neutral-300 hover:bg-white">
                      {link}
                    </a>
                  {/each}
                {/if}
              </div>
            </div>

            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Related Articles</p>
              <div class="mt-2 space-y-2">
                {#if relatedArticles.length === 0}
                  <p class="rounded-xl border border-dashed border-neutral-300 bg-neutral-50 px-3 py-3 text-sm text-neutral-500">No related article matches in the current category.</p>
                {:else}
                  {#each relatedArticles as article}
                    <button type="button" onclick={() => loadArticleDetail(article.id)} class="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-3 text-left hover:border-neutral-300 hover:bg-white">
                      <p class="text-sm font-semibold text-neutral-800">{article.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">Updated {formatDate(article.updated_at)}</p>
                    </button>
                  {/each}
                {/if}
              </div>
            </div>
          </div>
        </article>

        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h3 class="text-base font-semibold text-neutral-950">Version Control Timeline</h3>
          <p class="mt-1 text-sm text-neutral-500">Lifecycle and update events from article metadata.</p>

          <div class="mt-4 space-y-3">
            {#if versionTimeline.length === 0}
              <p class="rounded-xl border border-dashed border-neutral-300 bg-neutral-50 px-3 py-3 text-sm text-neutral-500">No version events available yet.</p>
            {:else}
              {#each versionTimeline as event}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-3">
                  <p class="text-sm font-semibold text-neutral-800">{event.label}</p>
                  <p class="mt-1 text-xs text-neutral-500">{event.detail}</p>
                  <p class="mt-2 text-xs font-medium text-neutral-700">{formatDateTime(event.at)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </article>
      {/if}
    </aside>
  </div>
</div>

<Modal
  open={showArticleModal}
  onclose={closeArticleModal}
  title={articleModalMode === "create" ? "New Article" : "Edit Article"}
  maxWidth="max-w-2xl"
>
  <form
    onsubmit={(e) => { e.preventDefault(); handleSaveArticle(); }}
    class="space-y-5"
  >
    <label class="block">
      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Title</span>
      <input
        type="text"
        bind:value={articleForm.title}
        placeholder="Article title"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
    </label>

    <label class="block">
      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Summary</span>
      <textarea
        bind:value={articleForm.summary}
        placeholder="Brief description of the article"
        rows="2"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10 resize-none"
      ></textarea>
    </label>

    <label class="block">
      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Body</span>
      <textarea
        bind:value={articleForm.body}
        placeholder="Full article content..."
        rows="8"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10 resize-y"
      ></textarea>
    </label>

    <div class="grid gap-4 sm:grid-cols-3">
      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Category</span>
        <select
          bind:value={articleForm.category}
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          <option value="">None</option>
          {#each categoryOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>

      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Visibility</span>
        <select
          bind:value={articleForm.visibility}
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          <option value="internal">Internal</option>
          <option value="portal">Partner Portal</option>
          <option value="public">Public</option>
        </select>
      </label>

      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Status</span>
        <select
          bind:value={articleForm.status}
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          <option value="draft">Draft</option>
          <option value="in_review">In Review</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </label>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 pt-4">
      <button
        type="button"
        onclick={closeArticleModal}
        class="rounded-xl border border-neutral-200 px-4 py-2.5 text-sm font-semibold text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={savingArticle}
        class="inline-flex items-center gap-2 rounded-xl bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800 transition-colors disabled:opacity-50"
      >
        {#if savingArticle}
          <div class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></div>
          Saving...
        {:else}
          {articleModalMode === "create" ? "Create Article" : "Save Changes"}
        {/if}
      </button>
    </div>
  </form>
</Modal>
