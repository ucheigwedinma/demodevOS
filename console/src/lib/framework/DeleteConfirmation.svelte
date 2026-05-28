<script lang="ts">
  import Modal from "$lib/components/ui/Modal.svelte";

  let {
    open = false,
    label = "record",
    loading = false,
    onconfirm,
    onclose,
  }: {
    open: boolean;
    label?: string;
    loading?: boolean;
    onconfirm: () => void;
    onclose: () => void;
  } = $props();
</script>

<Modal {open} {onclose} title="Delete {label}?">
  <p class="text-sm text-neutral-600 mb-6">
    Are you sure you want to delete this {label}? This action cannot be undone.
  </p>
  <div class="flex justify-end gap-3">
    <button
      onclick={onclose}
      class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
    >
      Cancel
    </button>
    <button
      onclick={onconfirm}
      disabled={loading}
      class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
    >
      {loading ? "Deleting..." : "Delete"}
    </button>
  </div>
</Modal>
