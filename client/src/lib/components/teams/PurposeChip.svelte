<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { WorkspaceTeamPurpose } from "$lib/types";

  interface Props {
    purpose: WorkspaceTeamPurpose;
  }

  let { purpose }: Props = $props();

  const labelKey = $derived(`workspace.teams.purpose.${purpose}`);
</script>

<span
  class="inline-flex items-center rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600"
>
  {i18n.t(labelKey)}
</span>
