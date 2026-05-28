<script lang="ts">
  import { ws, type EditorInfo } from "$lib/stores/websocket.svelte";
  import { onMount, onDestroy } from "svelte";

  let {
    model,
    recordId,
    onconflict,
  }: {
    model: string;
    recordId: number | string | null;
    onconflict?: (editor: EditorInfo) => void;
  } = $props();

  const editor = $derived(
    recordId != null ? ws.getEditor(model, recordId) : null
  );

  let announced = $state(false);

  // When we open a record, check who's editing and claim it
  $effect(() => {
    if (recordId != null && ws.connected) {
      ws.checkEditing(model, recordId);
      ws.startEditing(model, recordId);
      announced = true;
    }
  });

  // Notify parent when someone else starts editing
  $effect(() => {
    if (editor && onconflict) {
      onconflict(editor);
    }
  });

  onDestroy(() => {
    if (announced && recordId != null) {
      ws.stopEditing(model, recordId);
    }
  });

  function initials(name: string): string {
    return name
      .split(" ")
      .map(w => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-amber-500", "bg-purple-500",
    "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-orange-500",
  ];

  function avatarColor(userId: number): string {
    return colors[userId % colors.length];
  }
</script>

{#if editor}
  <div class="flex items-center gap-2.5 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
    <div class="h-6 w-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white {avatarColor(editor.user_id)} shrink-0">
      {initials(editor.name)}
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-xs font-medium text-amber-900 truncate">
        {editor.name} is currently editing this record
      </p>
      <p class="text-[10px] text-amber-600">
        Your changes may conflict — coordinate before saving
      </p>
    </div>
    <svg class="w-4 h-4 text-amber-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  </div>
{/if}
