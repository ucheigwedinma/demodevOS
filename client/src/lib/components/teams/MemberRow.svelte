<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import RoleSelect from "./RoleSelect.svelte";
  import type { WorkspaceTeamMembership, WorkspaceTeamRole } from "$lib/types";

  interface Props {
    membership: WorkspaceTeamMembership;
    /** Caller's role on this team — controls action visibility. */
    myRole: WorkspaceTeamRole | null;
    /** Caller's user id — to mark "(you)" and gate self-only actions. */
    myUserId?: number;
    /** Optimistic UI: dim the row while a mutation is in flight. */
    pending?: boolean;
    onRoleChange?: (next: WorkspaceTeamRole) => void;
    onRemove?: () => void;
    onTransfer?: () => void;
  }

  let {
    membership,
    myRole,
    myUserId,
    pending = false,
    onRoleChange,
    onRemove,
    onTransfer,
  }: Props = $props();

  const isMe = $derived(myUserId !== undefined && membership.user.id === myUserId);
  const isOwnerOrAdmin = $derived(myRole === "owner" || myRole === "admin");

  // An admin can edit member/guest rows but cannot touch other admins or the owner.
  // Owner can edit anything except switching the owner role (transfer endpoint).
  const canEditRole = $derived(
    isOwnerOrAdmin
      && membership.role !== "owner"
      && !(myRole === "admin" && membership.role === "admin"),
  );

  // Self-leave is always allowed for non-owners (owner has to transfer first;
  // we just hide the kick-self button for owners — they go through the danger zone).
  const canRemove = $derived(
    (isOwnerOrAdmin && membership.role !== "owner" && !(myRole === "admin" && membership.role === "admin"))
      || (isMe && membership.role !== "owner"),
  );

  // "Transfer ownership to this user" — only when caller is owner AND row is not self.
  const canTransferTo = $derived(myRole === "owner" && !isMe && membership.role !== "owner");

  let menuOpen = $state(false);
  let menuTrigger = $state<HTMLButtonElement | null>(null);

  function handleClickOutside(e: MouseEvent) {
    if (!menuOpen) return;
    if (menuTrigger && !menuTrigger.contains(e.target as Node)) {
      menuOpen = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div
  class="flex items-center gap-3 rounded-2xl border border-neutral-200 bg-white px-4 py-3 transition {pending
    ? 'opacity-60 pointer-events-none'
    : ''}"
>
  <span
    aria-hidden="true"
    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-sm font-semibold text-neutral-700"
  >
    {membership.user.initials}
  </span>

  <div class="min-w-0 flex-1">
    <div class="flex items-center gap-2">
      <p class="truncate text-sm font-semibold text-neutral-900">
        {membership.user.name}
      </p>
      {#if isMe}
        <span class="text-[10px] uppercase tracking-wider text-neutral-400">
          ({i18n.t("workspace.teams.you")})
        </span>
      {/if}
    </div>
    <p class="truncate text-xs text-neutral-500">{membership.user.email}</p>
  </div>

  <RoleSelect
    role={membership.role}
    canEdit={canEditRole}
    onChange={(next) => onRoleChange?.(next)}
  />

  {#if canRemove || canTransferTo}
    <div class="relative">
      <button
        bind:this={menuTrigger}
        type="button"
        aria-label={i18n.t("workspace.teams.member_menu")}
        class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
        onclick={(e) => {
          e.stopPropagation();
          menuOpen = !menuOpen;
        }}
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Zm0 6a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Zm0 6a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" />
        </svg>
      </button>
      {#if menuOpen}
        <div class="absolute right-0 top-full z-30 mt-1 min-w-[10rem] overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-md">
          {#if canTransferTo}
            <button
              type="button"
              class="block w-full px-3 py-2 text-left text-xs text-neutral-700 hover:bg-neutral-50"
              onclick={() => {
                menuOpen = false;
                onTransfer?.();
              }}
            >
              {i18n.t("workspace.teams.action.transfer_to_user")}
            </button>
          {/if}
          {#if canRemove}
            <button
              type="button"
              class="block w-full px-3 py-2 text-left text-xs text-rose-700 hover:bg-rose-50"
              onclick={() => {
                menuOpen = false;
                onRemove?.();
              }}
            >
              {isMe ? i18n.t("workspace.teams.action.leave") : i18n.t("workspace.teams.action.remove")}
            </button>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>
