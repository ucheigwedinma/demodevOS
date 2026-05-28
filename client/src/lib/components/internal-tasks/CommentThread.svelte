<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import type { InternalTaskComment } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";

  /**
   * Comment list + new-comment textarea.
   *
   * Plain text only in v1 — server parses @mentions and returns them on the
   * created comment. We do NOT do client-side mention parsing for autocomplete
   * in v1 (UI spec calls this v2 polish; reuse UserPicker pattern then).
   *
   * Caller passes:
   *   - taskId (for POST/DELETE endpoints)
   *   - currentUserId (so "delete own" decisions don't require a roundtrip)
   *   - comments (initially loaded by the page; we manage updates in-place)
   */

  interface Props {
    taskId: number;
    currentUserId: number;
    comments: InternalTaskComment[];
  }

  let { taskId, currentUserId, comments = $bindable([]) }: Props = $props();

  let newBody = $state("");
  let posting = $state(false);
  let deletingId = $state<number | null>(null);

  async function postComment() {
    const body = newBody.trim();
    if (!body) return;
    posting = true;
    try {
      const created = await api.post<InternalTaskComment>(
        `/internal-tasks/tasks/${taskId}/comments/`,
        { body },
      );
      comments = [...comments, created];
      newBody = "";
    } catch (err) {
      const msg =
        err instanceof ApiError && (err.data?.detail as string)
          ? (err.data.detail as string)
          : i18n.t("workspace.internal_tasks.toast.comment_failed");
      toast.error(msg);
    } finally {
      posting = false;
    }
  }

  async function deleteComment(comment: InternalTaskComment) {
    if (comment.author.id !== currentUserId) return;
    const previous = comments;
    comments = comments.filter((c) => c.id !== comment.id);
    deletingId = comment.id;
    try {
      await api.delete(
        `/internal-tasks/tasks/${taskId}/comments/${comment.id}/`,
      );
    } catch (err) {
      // Rollback
      comments = previous;
      toast.error(i18n.t("workspace.internal_tasks.toast.comment_delete_failed"));
    } finally {
      deletingId = null;
    }
  }

  function relativeTime(iso: string): string {
    const d = new Date(iso);
    const diffMs = d.getTime() - Date.now();
    const absSec = Math.abs(diffMs) / 1000;
    const rtf = new Intl.RelativeTimeFormat(i18n.locale, { numeric: "auto" });
    if (absSec < 60) return rtf.format(Math.round(diffMs / 1000), "second");
    if (absSec < 3600) return rtf.format(Math.round(diffMs / 60000), "minute");
    if (absSec < 86400) return rtf.format(Math.round(diffMs / 3600000), "hour");
    if (absSec < 86400 * 14) return rtf.format(Math.round(diffMs / 86400000), "day");
    return new Intl.DateTimeFormat(i18n.locale, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(d);
  }

  function handleKeydown(e: KeyboardEvent) {
    // Cmd/Ctrl + Enter to send.
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void postComment();
    }
  }
</script>

<section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
  <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">
    {i18n.t("workspace.internal_tasks.comments.title", { count: comments.length })}
  </h2>

  {#if comments.length === 0}
    <p class="text-sm text-neutral-500">
      {i18n.t("workspace.internal_tasks.comments.empty")}
    </p>
  {:else}
    <ul class="space-y-3">
      {#each comments as comment (comment.id)}
        <li class="flex items-start gap-3">
          <span
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-700"
            aria-hidden="true"
          >
            {comment.author?.initials ?? "?"}
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="text-sm font-semibold text-neutral-900">
                {comment.author?.name ?? i18n.t("workspace.internal_tasks.comments.deactivated_user")}
              </span>
              <span class="text-[11px] text-neutral-400">
                {relativeTime(comment.created_at)}
              </span>
            </div>
            <p class="mt-0.5 whitespace-pre-wrap text-sm text-neutral-700">
              {comment.body}
            </p>
          </div>
          {#if comment.author?.id === currentUserId}
            <button
              type="button"
              onclick={() => deleteComment(comment)}
              disabled={deletingId === comment.id}
              aria-label={i18n.t("workspace.internal_tasks.comments.delete")}
              class="text-neutral-300 hover:text-rose-600 disabled:opacity-50"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
              </svg>
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}

  <div class="border-t border-neutral-200 pt-3">
    <label for="new-comment" class="sr-only">
      {i18n.t("workspace.internal_tasks.comments.compose")}
    </label>
    <textarea
      id="new-comment"
      bind:value={newBody}
      onkeydown={handleKeydown}
      rows="2"
      placeholder={i18n.t("workspace.internal_tasks.comments.placeholder")}
      class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
    ></textarea>
    <div class="mt-2 flex items-center justify-between gap-2">
      <p class="text-[11px] text-neutral-400">
        {i18n.t("workspace.internal_tasks.comments.hint")}
      </p>
      <button
        type="button"
        onclick={postComment}
        disabled={posting || !newBody.trim()}
        class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
      >
        {#if posting}
          {i18n.t("common.actions.sending")}
        {:else}
          {i18n.t("workspace.internal_tasks.comments.send")}
        {/if}
      </button>
    </div>
  </div>
</section>
