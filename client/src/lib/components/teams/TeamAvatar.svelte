<script lang="ts">
  import { TEAM_COLORS, resolveColor } from "./team-colors";
  import type { WorkspaceTeamColor } from "$lib/types";

  /**
   * TeamAvatar — square Linear-style disc with a centered emoji on a
   * palette-token background. The square (`rounded-xl`) shape distinguishes
   * teams from people (round avatars) at a glance.
   *
   * Sizes:
   *   sm  → h-7  w-7  (28px)  used inline in chips
   *   md  → h-10 w-10 (40px)  default — TeamCard, MemberRow's team chip
   *   lg  → h-14 w-14 (56px)  detail page header
   *   xl  → h-20 w-20 (80px)  create-wizard preview
   */
  interface Props {
    emoji?: string;
    color?: WorkspaceTeamColor | string | null;
    size?: "sm" | "md" | "lg" | "xl";
    teamName?: string;
    decorative?: boolean;
  }

  let {
    emoji = "👥",
    color = "sky",
    size = "md",
    teamName,
    decorative = false,
  }: Props = $props();

  const sizeClass = $derived(
    size === "sm"
      ? "h-7 w-7 text-base rounded-lg"
      : size === "lg"
      ? "h-14 w-14 text-3xl rounded-xl"
      : size === "xl"
      ? "h-20 w-20 text-5xl rounded-2xl"
      : "h-10 w-10 text-xl rounded-xl",
  );

  const discClass = $derived(TEAM_COLORS[resolveColor(color)].disc);

  // ARIA: when decorative=true (paired with the team name in the same focusable
  // element), hide from screen readers. Otherwise announce the team name.
  const ariaLabel = $derived(decorative ? undefined : teamName ? `${teamName} icon` : "Team icon");
</script>

<span
  class="inline-flex shrink-0 items-center justify-center {sizeClass} {discClass}"
  role={decorative ? "presentation" : "img"}
  aria-label={ariaLabel}
  aria-hidden={decorative}
>
  {emoji}
</span>
