<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import TeamAvatar from "$lib/components/teams/TeamAvatar.svelte";
  import {
    TEAM_COLOR_TOKENS,
    TEAM_COLORS,
    TEAM_EMOJI_PICKS,
  } from "$lib/components/teams/team-colors";
  import type {
    PaginatedResponse,
    ProjectListItem,
    WorkspaceTeamColor,
    WorkspaceTeamCreatePayload,
    WorkspaceTeamDetail,
    WorkspaceTeamPurpose,
    WorkspaceTeamVisibility,
  } from "$lib/types";

  let name = $state("");
  let description = $state("");
  let purpose = $state<WorkspaceTeamPurpose>("initiative");
  let visibility = $state<WorkspaceTeamVisibility>("public");
  let projectId = $state<number | null>(null);
  let emoji = $state("👥");
  let color = $state<WorkspaceTeamColor>("sky");

  let projects = $state<ProjectListItem[]>([]);
  let projectsLoading = $state(false);

  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});

  async function loadProjects() {
    if (purpose !== "project" || projects.length > 0) return;
    projectsLoading = true;
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
        page_size: "100",
      });
      projects = res.results;
    } catch (err) {
      console.error("[/teams/new]", err);
    } finally {
      projectsLoading = false;
    }
  }

  $effect(() => {
    if (purpose === "project") loadProjects();
  });

  function devFill() {
    name = "Mobile Launch Squad";
    description = "Cross-functional release team for the Q3 mobile launch.";
    purpose = "initiative";
    visibility = "public";
    emoji = "🚀";
    color = "violet";
  }

  function fieldError(key: string): string | null {
    const errs = fieldErrors[key];
    return errs && errs.length > 0 ? errs[0] : null;
  }

  async function submit() {
    fieldErrors = {};
    if (!name.trim()) {
      fieldErrors = { name: [i18n.t("workspace.teams.create.name_required")] };
      return;
    }
    saving = true;
    const payload: WorkspaceTeamCreatePayload = {
      name: name.trim(),
      description: description.trim() || undefined,
      purpose,
      visibility,
      emoji,
      color,
    };
    if (purpose === "project") payload.project = projectId;
    try {
      const created = await api.post<WorkspaceTeamDetail>("/workspace/teams/", payload);
      toast.success(i18n.t("workspace.teams.create.success"));
      await goto(`/teams/${created.id}`);
    } catch (err) {
      console.error("[/teams/new submit]", err);
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error(i18n.t("workspace.teams.create.error"));
      } else {
        toast.error(i18n.t("workspace.teams.create.error"));
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="mx-auto max-w-3xl space-y-4">
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.title")}</a>
    </p>
    <div class="mt-2 flex items-center justify-between">
      <h1 class="text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.teams.create.title")}
      </h1>
      <a
        href="/teams"
        class="rounded-xl border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {i18n.t("workspace.teams.create.cancel")}
      </a>
    </div>
  </div>

  <!-- Section 1 — Identity -->
  <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-5">
    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.teams.create.section_identity")}
    </p>

    <label class="block">
      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-500">
        {i18n.t("workspace.teams.create.name")} *
      </span>
      <input
        type="text"
        bind:value={name}
        maxlength="120"
        placeholder={i18n.t("workspace.teams.create.name_placeholder")}
        aria-required="true"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
      {#if fieldError("name")}
        <p class="mt-1 text-xs text-rose-600">{fieldError("name")}</p>
      {/if}
    </label>

    <label class="block">
      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-500">
        {i18n.t("workspace.teams.create.description")}
      </span>
      <textarea
        bind:value={description}
        rows="3"
        placeholder={i18n.t("workspace.teams.create.description_placeholder")}
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      ></textarea>
    </label>

    <div>
      <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-500">
        {i18n.t("workspace.teams.create.avatar")}
      </span>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div class="flex flex-col items-center gap-2">
          <TeamAvatar {emoji} {color} size="xl" decorative />
        </div>
        <div class="flex-1 space-y-3">
          <div class="grid grid-cols-8 gap-2">
            {#each TEAM_EMOJI_PICKS as candidate (candidate)}
              <button
                type="button"
                onclick={() => (emoji = candidate)}
                aria-pressed={emoji === candidate}
                class="flex h-10 w-10 items-center justify-center rounded-xl border text-xl transition {emoji ===
                candidate
                  ? 'border-neutral-900 bg-neutral-50 ring-2 ring-neutral-900/10'
                  : 'border-neutral-200 hover:border-neutral-400'}"
              >
                {candidate}
              </button>
            {/each}
          </div>
          <div class="flex flex-wrap gap-2">
            {#each TEAM_COLOR_TOKENS as token (token)}
              <button
                type="button"
                onclick={() => (color = token)}
                aria-label={token}
                aria-pressed={color === token}
                class="h-8 w-8 rounded-full transition {TEAM_COLORS[token].swatch} {color === token
                  ? 'ring-2 ring-neutral-900 ring-offset-2'
                  : 'hover:scale-110'}"
              ></button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Section 2 — Purpose -->
  <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-4">
    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.teams.create.section_purpose")}
    </p>
    <div class="grid gap-3 sm:grid-cols-3">
      {#each [
        { key: "project", emojiHint: "📐", labelKey: "workspace.teams.purpose.project", helperKey: "workspace.teams.purpose_helper.project" },
        { key: "initiative", emojiHint: "🎯", labelKey: "workspace.teams.purpose.initiative", helperKey: "workspace.teams.purpose_helper.initiative" },
        { key: "guild", emojiHint: "🌱", labelKey: "workspace.teams.purpose.guild", helperKey: "workspace.teams.purpose_helper.guild" },
      ] as opt (opt.key)}
        <button
          type="button"
          onclick={() => (purpose = opt.key as WorkspaceTeamPurpose)}
          aria-pressed={purpose === opt.key}
          class="rounded-2xl border p-4 text-left transition {purpose === opt.key
            ? 'border-neutral-900 bg-neutral-50 ring-2 ring-neutral-900/10'
            : 'border-neutral-200 bg-white hover:border-neutral-400'}"
        >
          <p class="text-2xl">{opt.emojiHint}</p>
          <p class="mt-2 text-sm font-semibold text-neutral-900">{i18n.t(opt.labelKey)}</p>
          <p class="mt-1 text-xs text-neutral-500">{i18n.t(opt.helperKey)}</p>
        </button>
      {/each}
    </div>

    {#if purpose === "project"}
      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-500">
          {i18n.t("workspace.teams.create.project")} *
        </span>
        <select
          value={projectId ?? ""}
          onchange={(e) => {
            const v = (e.target as HTMLSelectElement).value;
            projectId = v ? Number(v) : null;
          }}
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          <option value="">{projectsLoading ? i18n.t("workspace.teams.create.project_loading") : i18n.t("workspace.teams.create.project_choose")}</option>
          {#each projects as project (project.id)}
            <option value={project.id}>{project.name}</option>
          {/each}
        </select>
        {#if fieldError("project")}
          <p class="mt-1 text-xs text-rose-600">{fieldError("project")}</p>
        {/if}
      </label>
    {/if}
  </section>

  <!-- Section 3 — Visibility -->
  <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.teams.create.section_visibility")}
    </p>
    {#each [
      { key: "public", icon: "🌐", helperKey: "workspace.teams.visibility_helper.public" },
      { key: "private", icon: "🔒", helperKey: "workspace.teams.visibility_helper.private" },
      { key: "secret", icon: "👁‍🗨", helperKey: "workspace.teams.visibility_helper.secret" },
    ] as opt (opt.key)}
      <label class="flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition {visibility === opt.key
        ? 'border-neutral-900 bg-neutral-50 ring-2 ring-neutral-900/10'
        : 'border-neutral-200 bg-white hover:border-neutral-400'}">
        <input
          type="radio"
          name="visibility"
          value={opt.key}
          bind:group={visibility}
          class="mt-1 h-4 w-4 accent-neutral-900"
        />
        <span class="flex-1">
          <span class="flex items-center gap-2 text-sm font-semibold text-neutral-900">
            <span aria-hidden="true">{opt.icon}</span>
            {i18n.t(`workspace.teams.visibility.${opt.key}`)}
          </span>
          <span class="mt-1 block text-xs text-neutral-500">{i18n.t(opt.helperKey)}</span>
        </span>
      </label>
    {/each}
  </section>

  <!-- Footer -->
  <div class="flex items-center justify-between gap-3">
    <button
      type="button"
      onclick={devFill}
      class="rounded-xl border border-dashed border-neutral-300 bg-white px-3 py-1.5 text-xs font-medium text-neutral-500 hover:border-neutral-400"
      title="Dev Fill — populate fields with test data"
    >
      Dev Fill
    </button>
    <div class="flex items-center gap-2">
      <a
        href="/teams"
        class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {i18n.t("workspace.teams.create.cancel")}
      </a>
      <button
        type="button"
        onclick={submit}
        disabled={saving}
        class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-neutral-800 disabled:opacity-60"
      >
        {saving ? i18n.t("workspace.teams.create.creating") : i18n.t("workspace.teams.create.submit")}
      </button>
    </div>
  </div>
</div>
