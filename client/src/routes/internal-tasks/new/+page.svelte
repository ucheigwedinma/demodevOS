<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    InternalTaskCreatePayload,
    InternalTaskDetail,
  } from "$lib/types";
  import TaskForm from "$lib/components/internal-tasks/TaskForm.svelte";

  let submitting = $state(false);

  async function submit(payload: InternalTaskCreatePayload) {
    submitting = true;
    try {
      const created = await api.post<InternalTaskDetail>(
        "/internal-tasks/tasks/",
        payload,
      );
      toast.success(i18n.t("workspace.internal_tasks.toast.created"));
      goto(`/internal-tasks/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldMsg = Object.values(err.fieldErrors)[0]?.[0];
        const msg =
          fieldMsg ||
          (err.data?.detail as string) ||
          i18n.t("workspace.internal_tasks.toast.create_failed");
        toast.error(msg);
      } else {
        console.error(err);
        toast.error(i18n.t("workspace.internal_tasks.toast.create_failed"));
      }
    } finally {
      submitting = false;
    }
  }

  function cancel() {
    goto("/internal-tasks");
  }
</script>

<div class="space-y-4">
  <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
    <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.eyebrow")}</a>
    <span class="text-neutral-300"> › </span>
    <a href="/internal-tasks" class="hover:text-blue-700">{i18n.t("workspace.internal_tasks.title")}</a>
  </p>
  <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
    {i18n.t("workspace.internal_tasks.new_task")}
  </h1>

  <TaskForm mode="create" onsubmit={submit} oncancel={cancel} {submitting} />
</div>
