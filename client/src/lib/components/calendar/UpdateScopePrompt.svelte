<script lang="ts">
  import Modal from "$lib/components/Modal.svelte";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Modal asking the creator how to apply changes to a recurring event:
   *   - this only
   *   - this and future
   *   - all events in the series
   *
   * Default selection is "this and future" — least surprising (preserves past,
   * updates future). The selected scope is returned via `onConfirm(scope)`.
   *
   * NEVER show this for non-recurring events (caller's responsibility).
   */

  export type UpdateScope = "this" | "future" | "all";

  interface Props {
    open: boolean;
    onclose: () => void;
    onconfirm: (scope: UpdateScope) => void;
    /** Title key override (defaults to "Apply changes to:"). */
    titleKey?: string;
  }

  let { open, onclose, onconfirm, titleKey }: Props = $props();

  let scope = $state<UpdateScope>("future");

  function confirm() {
    onconfirm(scope);
  }

  let title = $derived(i18n.t(titleKey ?? "workspace.calendar.scope.title"));
</script>

<Modal {open} {onclose} {title}>
  <div class="space-y-3">
    <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200 bg-white p-4 hover:border-neutral-400">
      <input
        type="radio"
        name="scope"
        value="this"
        bind:group={scope}
        class="mt-0.5 h-4 w-4 accent-neutral-900"
      />
      <span>
        <span class="block text-sm font-semibold text-neutral-900">
          {i18n.t("workspace.calendar.scope.this")}
        </span>
        <span class="mt-1 block text-xs text-neutral-500">
          {i18n.t("workspace.calendar.scope.this_helper")}
        </span>
      </span>
    </label>

    <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200 bg-white p-4 hover:border-neutral-400">
      <input
        type="radio"
        name="scope"
        value="future"
        bind:group={scope}
        class="mt-0.5 h-4 w-4 accent-neutral-900"
      />
      <span>
        <span class="block text-sm font-semibold text-neutral-900">
          {i18n.t("workspace.calendar.scope.future")}
        </span>
        <span class="mt-1 block text-xs text-neutral-500">
          {i18n.t("workspace.calendar.scope.future_helper")}
        </span>
      </span>
    </label>

    <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200 bg-white p-4 hover:border-neutral-400">
      <input
        type="radio"
        name="scope"
        value="all"
        bind:group={scope}
        class="mt-0.5 h-4 w-4 accent-neutral-900"
      />
      <span>
        <span class="block text-sm font-semibold text-neutral-900">
          {i18n.t("workspace.calendar.scope.all")}
        </span>
        <span class="mt-1 block text-xs text-neutral-500">
          {i18n.t("workspace.calendar.scope.all_helper")}
        </span>
      </span>
    </label>
  </div>
  <div class="mt-5 flex justify-end gap-2">
    <button
      type="button"
      onclick={onclose}
      class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
    >
      {i18n.t("common.actions.cancel")}
    </button>
    <button
      type="button"
      onclick={confirm}
      class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
    >
      {i18n.t("workspace.calendar.scope.apply")}
    </button>
  </div>
</Modal>
