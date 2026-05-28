<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import TeamAvatar from "./TeamAvatar.svelte";
  import PurposeChip from "./PurposeChip.svelte";
  import VisibilityChip from "./VisibilityChip.svelte";
  import type { WorkspaceTeamListItem } from "$lib/types";

  interface Props {
    team: WorkspaceTeamListItem;
  }

  let { team }: Props = $props();
</script>

<a
  href={`/teams/${team.id}`}
  class="group relative block rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:border-neutral-400 hover:shadow {team.is_archived
    ? 'opacity-70'
    : ''}"
>
  <div class="flex items-start gap-3">
    <TeamAvatar emoji={team.emoji} color={team.color} size="md" decorative />
    <div class="min-w-0 flex-1">
      <h3 class="truncate text-base font-semibold text-neutral-900">{team.name}</h3>
      {#if team.description}
        <p class="mt-1 line-clamp-1 text-sm text-neutral-500">{team.description}</p>
      {:else}
        <p class="mt-1 text-sm italic text-neutral-400">{i18n.t("workspace.teams.no_description")}</p>
      {/if}
    </div>
    {#if team.is_archived}
      <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
        {i18n.t("workspace.teams.archived_badge")}
      </span>
    {/if}
  </div>

  <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
    <div class="flex flex-wrap items-center gap-1.5">
      <PurposeChip purpose={team.purpose} />
      <VisibilityChip visibility={team.visibility} />
      {#if team.my_role}
        <span class="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
          {i18n.t(`workspace.teams.role.${team.my_role}`)}
        </span>
      {/if}
    </div>
    <span class="text-xs tabular-nums text-neutral-500">
      {i18n.t("workspace.teams.member_count", { count: team.members_count })}
    </span>
  </div>
</a>
