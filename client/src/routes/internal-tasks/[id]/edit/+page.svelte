<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    InternalTaskCreatePayload,
    InternalTaskDetail,
  } from "$lib/types";
  import TaskForm from "$lib/components/internal-tasks/TaskForm.svelte";

  let id = $derived(parseInt($page.params.id ?? "0"));

  let detail = $state<InternalTaskDetail | null>(null);
  let loading = $state(true);
  let notFound = $state(false);
  let submitting = $state(false);

  onMount(load);

  async function load() {
    loading = true;
    notFound = false;
    try {
      detail = await api.get<InternalTaskDetail>(`/internal-tasks/tasks/${id}/`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) notFound = true;
      else console.error(err);
    } finally {
      loading = false;
    }
  }

  async function submit(payload: InternalTaskCreatePayload) {
    if (!detail) return;
    submitting = true;
    // Per design: team / visibility changes are creator-only. The backend
    // 403s if a non-creator tries to set them; the form already disables
    // those fields for non-creators via the `canChangeOwnership` prop.
    try {
      await api.patch<InternalTaskDetail>(`/internal-tasks/tasks/${detail.id}/`, payload);
      toast.success(i18n.t("workspace.internal_tasks.toast.saved"));
      goto(`/internal-tasks/${detail.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldMsg = Object.values(err.fieldErrors)[0]?.[0];
        const msg =
          fieldMsg ||
          (err.data?.detail as string) ||
          i18n.t("workspace.internal_tasks.toast.save_failed");
        toast.error(msg);
      } else {
        console.error(err);
        toast.error(i18n.t("workspace.internal_tasks.toast.save_failed"));
      }
    } finally {
      submitting = false;
    }
  }

  function cancel() {
    if (detail) goto(`/internal-tasks/${detail.id}`);
    else goto("/internal-tasks");
  }

  let canChangeOwnership = $derived(detail?.my_role === "creator");
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound || !detail}
  <div class="mx-auto max-w-md rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
    <p class="text-3xl">🔍</p>
    <p class="mt-3 text-base font-semibold text-neutral-800">
      {i18n.t("workspace.internal_tasks.error.not_found")}
    </p>
    <a
      href="/internal-tasks"
      class="mt-4 inline-flex items-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
    >
      {i18n.t("workspace.internal_tasks.back_to_list")}
    </a>
  </div>
{:else}
  <div class="space-y-4">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.title")}</a>
      <span class="text-neutral-300"> › </span>
      <a href={`/internal-tasks/${detail.id}`} class="hover:text-blue-700 normal-case tracking-normal">{detail.title}</a>
    </p>
    <h1 class="text-2xl font-bold tracking-wide text-neutral-800">
      {i18n.t("workspace.internal_tasks.edit_task")}
    </h1>

    <TaskForm
      initial={detail}
      mode="edit"
      {canChangeOwnership}
      onsubmit={submit}
      oncancel={cancel}
      {submitting}
    />
  </div>
{/if}
