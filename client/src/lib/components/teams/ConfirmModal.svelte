<script lang="ts">
  import Modal from "$lib/components/Modal.svelte";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * ConfirmModal — wraps the shared <Modal> with destructive vs neutral styling
   * and an optional type-the-name confirmation pattern (used for hard-delete).
   */
  interface Props {
    open: boolean;
    onclose: () => void;
    onconfirm: () => void;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    /** Reddens the confirm button when true. */
    destructive?: boolean;
    /** When set, the confirm button is disabled until the user types this exact string. */
    typeToConfirm?: string;
    typeToConfirmLabel?: string;
    busy?: boolean;
  }

  let {
    open,
    onclose,
    onconfirm,
    title,
    message,
    confirmLabel,
    cancelLabel,
    destructive = false,
    typeToConfirm,
    typeToConfirmLabel,
    busy = false,
  }: Props = $props();

  let typed = $state("");

  $effect(() => {
    if (!open) typed = "";
  });

  const canConfirm = $derived(
    !busy && (!typeToConfirm || typed === typeToConfirm),
  );

  const confirmText = $derived(confirmLabel ?? i18n.t("workspace.teams.confirm.confirm"));
  const cancelText = $derived(cancelLabel ?? i18n.t("workspace.teams.confirm.cancel"));
</script>

<Modal {open} {onclose} {title}>
  <div class="space-y-4">
    <p class="text-sm text-neutral-700">{message}</p>

    {#if typeToConfirm}
      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
          {typeToConfirmLabel ?? i18n.t("workspace.teams.confirm.type_to_confirm")}
        </span>
        <input
          type="text"
          bind:value={typed}
          autocomplete="off"
          spellcheck="false"
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          placeholder={typeToConfirm}
        />
      </label>
    {/if}

    <div class="flex items-center justify-end gap-2 pt-2">
      <button
        type="button"
        onclick={onclose}
        class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
        disabled={busy}
      >
        {cancelText}
      </button>
      <button
        type="button"
        onclick={onconfirm}
        disabled={!canConfirm}
        class="rounded-xl px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60 {destructive
          ? 'bg-rose-600 hover:bg-rose-700'
          : 'bg-neutral-900 hover:bg-neutral-800'}"
      >
        {busy ? i18n.t("workspace.teams.confirm.working") : confirmText}
      </button>
    </div>
  </div>
</Modal>
