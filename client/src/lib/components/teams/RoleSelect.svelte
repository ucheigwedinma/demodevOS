<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import RoleChip from "./RoleChip.svelte";
  import type { WorkspaceTeamRole } from "$lib/types";

  /**
   * RoleSelect — clickable chip that opens a small popover with the four
   * roles. Owner is hidden from the picker (transferring ownership is a
   * dedicated action — see /teams/[id]/settings).
   */
  interface Props {
    role: WorkspaceTeamRole;
    canEdit?: boolean;
    onChange?: (next: WorkspaceTeamRole) => void;
  }

  let { role = $bindable(), canEdit = false, onChange }: Props = $props();

  let open = $state(false);
  let triggerEl = $state<HTMLButtonElement | null>(null);

  const choices: WorkspaceTeamRole[] = ["admin", "member", "guest"];

  function handleSelect(next: WorkspaceTeamRole) {
    open = false;
    if (next === role) return;
    role = next;
    onChange?.(next);
  }

  function handleClickOutside(e: MouseEvent) {
    if (!open) return;
    if (triggerEl && !triggerEl.contains(e.target as Node)) {
      open = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="relative inline-block">
  {#if canEdit}
    <button
      bind:this={triggerEl}
      type="button"
      class="cursor-pointer focus:outline-none focus:ring-2 focus:ring-neutral-800/10 rounded-full"
      aria-haspopup="listbox"
      aria-expanded={open}
      onclick={(e) => {
        e.stopPropagation();
        open = !open;
      }}
    >
      <RoleChip {role} />
    </button>

    {#if open}
      <div
        role="listbox"
        class="absolute right-0 top-full z-30 mt-1 min-w-[8rem] overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-md"
      >
        {#if role === "owner"}
          <p class="px-3 py-2 text-[10px] uppercase tracking-wider text-neutral-400">
            {i18n.t("workspace.teams.role_select.owner_hint")}
          </p>
        {/if}
        {#each choices as choice (choice)}
          <button
            type="button"
            role="option"
            aria-selected={role === choice}
            onclick={() => handleSelect(choice)}
            class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-neutral-50 {role ===
            choice
              ? 'bg-neutral-50 font-semibold'
              : ''}"
          >
            <span class="text-neutral-700">{i18n.t(`workspace.teams.role.${choice}`)}</span>
            {#if role === choice}
              <svg class="h-4 w-4 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  {:else}
    <RoleChip {role} />
  {/if}
</div>
