<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import TeamAvatar from "$lib/components/teams/TeamAvatar.svelte";
  import {
    TEAM_COLOR_TOKENS,
    TEAM_COLORS,
    TEAM_EMOJI_PICKS,
    resolveColor,
  } from "$lib/components/teams/team-colors";
  import type {
    WorkspaceTeamColor,
    WorkspaceTeamDetail,
    WorkspaceTeamVisibility,
  } from "$lib/types";

  const teamId = $derived(Number($page.params.id));

  let loading = $state(true);
  let saving = $state(false);
  let notFound = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});

  let team = $state<WorkspaceTeamDetail | null>(null);
  let originalVisibility = $state<WorkspaceTeamVisibility>("public");
  let name = $state("");
  let description = $state("");
  let visibility = $state<WorkspaceTeamVisibility>("public");
  let emoji = $state("👥");
  let color = $state<WorkspaceTeamColor>("sky");

  async function loadTeam() {
    loading = true;
    notFound = false;
    try {
      const t = await api.get<WorkspaceTeamDetail>(`/workspace/teams/${teamId}/`);
      team = t;
      name = t.name;
      description = t.description ?? "";
      visibility = t.visibility;
      originalVisibility = t.visibility;
      emoji = t.emoji ?? "👥";
      color = resolveColor(t.color);
      // Owner/admin guard — the API will enforce, but bounce early for UX.
      if (t.my_role !== "owner" && t.my_role !== "admin") {
        toast.error(i18n.t("workspace.teams.error.no_permission"));
        await goto(`/teams/${t.id}`);
      }
    } catch (err) {
      console.error("[/teams/[id]/edit]", err);
      if (err instanceof ApiError && err.status === 404) notFound = true;
    } finally {
      loading = false;
    }
  }

  onMount(loadTeam);

  function fieldError(key: string): string | null {
    const errs = fieldErrors[key];
    return errs && errs.length > 0 ? errs[0] : null;
  }

  const visibilityWarning = $derived.by(() => {
    if (visibility === originalVisibility) return null;
    if (originalVisibility === "public" && visibility === "secret") {
      return i18n.t("workspace.teams.edit.warn.public_to_secret");
    }
    if (originalVisibility === "secret" && visibility !== "secret") {
      return i18n.t("workspace.teams.edit.warn.secret_to_open");
    }
    if (visibility === "public" && originalVisibility !== "public") {
      return i18n.t("workspace.teams.edit.warn.to_public");
    }
    return null;
  });

  async function submit() {
    if (!team) return;
    fieldErrors = {};
    if (!name.trim()) {
      fieldErrors = { name: [i18n.t("workspace.teams.create.name_required")] };
      return;
    }
    saving = true;
    try {
      await api.patch(`/workspace/teams/${team.id}/`, {
        name: name.trim(),
        description: description.trim(),
        visibility,
        emoji,
        color,
      });
      toast.success(i18n.t("workspace.teams.edit.success"));
      await goto(`/teams/${team.id}`);
    } catch (err) {
      console.error("[/teams/[id]/edit submit]", err);
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
      }
      toast.error(i18n.t("workspace.teams.edit.error"));
    } finally {
      saving = false;
    }
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound || !team}
  <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-16 text-center">
    <p class="text-3xl">🔎</p>
    <h2 class="mt-3 text-lg font-semibold text-neutral-900">{i18n.t("workspace.teams.not_found.title")}</h2>
    <a href="/teams" class="mt-4 inline-block text-xs font-semibold text-neutral-700 underline hover:text-neutral-900">
      {i18n.t("workspace.teams.not_found.back")}
    </a>
  </div>
{:else}
  <div class="mx-auto max-w-3xl space-y-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
        <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.eyebrow")}</a>
        <span class="text-neutral-300"> › </span>
        <a href="/teams" class="hover:text-blue-700">{i18n.t("workspace.teams.title")}</a>
        <span class="text-neutral-300"> › </span>
        <a href={`/teams/${team.id}`} class="hover:text-blue-700 normal-case tracking-normal">{team.name}</a>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.teams.edit.title")}
      </h1>
    </div>

    <!-- Identity -->
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
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
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
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        ></textarea>
      </label>

      <div>
        <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-500">
          {i18n.t("workspace.teams.create.avatar")}
        </span>
        <div class="flex flex-col gap-4 sm:flex-row sm:items-start">
          <TeamAvatar {emoji} {color} size="xl" decorative />
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

    <!-- Visibility -->
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
      {#if visibilityWarning}
        <p class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {visibilityWarning}
        </p>
      {/if}
    </section>

    <!-- Danger zone redirect -->
    <p class="text-xs text-neutral-500">
      {i18n.t("workspace.teams.edit.danger_link_prefix")}
      <a href={`/teams/${team.id}/settings`} class="font-semibold text-neutral-700 underline hover:text-neutral-900">
        {i18n.t("workspace.teams.edit.danger_link")}
      </a>
    </p>

    <div class="flex items-center justify-end gap-2">
      <a
        href={`/teams/${team.id}`}
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
        {saving ? i18n.t("workspace.teams.edit.saving") : i18n.t("workspace.teams.edit.submit")}
      </button>
    </div>
  </div>
{/if}
