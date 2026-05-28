<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { WorkspaceTeamRole } from "$lib/types";

  interface Props {
    role: WorkspaceTeamRole;
  }

  let { role }: Props = $props();

  // Owner = warm amber (leadership). Admin/member/guest = neutral with
  // progressively softer treatment to read as a hierarchy. Guest's dashed
  // border signals "limited access".
  const styleClass = $derived(
    role === "owner"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : role === "admin"
      ? "border-neutral-300 bg-neutral-100 text-neutral-700"
      : role === "member"
      ? "border-neutral-200 bg-white text-neutral-600"
      : "border-dashed border-neutral-300 bg-neutral-50 text-neutral-500",
  );
</script>

<span
  class="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider {styleClass}"
>
  {i18n.t(`workspace.teams.role.${role}`)}
</span>
