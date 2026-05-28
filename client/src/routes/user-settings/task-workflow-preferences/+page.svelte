<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserTaskDefaultView,
    UserTaskWorkflowPreferences,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserTaskWorkflowPreferences | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  async function loadPreferences() {
    loading = true;
    try {
      preferences = await api.get<UserTaskWorkflowPreferences>("/auth/task-workflow-preferences/");
    } catch (error) {
      preferences = null;
      toast.error("Load failed", parseError(error, "Could not load task and workflow preferences."));
    } finally {
      loading = false;
    }
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserTaskWorkflowPreferences>("/auth/task-workflow-preferences/", {
        default_task_view: preferences.default_task_view,
        task_reminder_minutes_before: preferences.task_reminder_minutes_before,
        task_default_due_date_offset_days: preferences.task_default_due_date_offset_days,
        auto_follow_assigned_tasks: preferences.auto_follow_assigned_tasks,
        auto_subscribe_project_updates: preferences.auto_subscribe_project_updates,
        approval_delegation_rule: preferences.approval_delegation_rule,
      });
      preferences = updated;
      toast.success("Updated", "Task and workflow preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save task and workflow preferences."));
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadPreferences();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !preferences}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Task preferences unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your task and workflow preferences.</p>
    <button
      onclick={() => loadPreferences()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Task & Workflow Preferences</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Configure default task views, reminders, task automation, and approval delegation behavior.
        </p>
      </div>
      <button
        onclick={savePreferences}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Task defaults</h2>
      <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <div>
          <p class="mb-1.5 text-sm font-medium text-neutral-700">Default task view</p>
          <div class="flex flex-wrap gap-2">
            {#each preferences.default_task_view_options as option}
              <button
                type="button"
                onclick={() => {
                  if (!preferences) return;
                  preferences.default_task_view = option.value as UserTaskDefaultView;
                }}
                class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
                  {preferences.default_task_view === option.value
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <label for="task_reminder_minutes_before" class="mb-1.5 block text-sm font-medium text-neutral-700">Task reminder timing</label>
          <select
            id="task_reminder_minutes_before"
            bind:value={preferences.task_reminder_minutes_before}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each preferences.task_reminder_timing_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="task_default_due_date_offset_days" class="mb-1.5 block text-sm font-medium text-neutral-700">Default due date offsets</label>
          <select
            id="task_default_due_date_offset_days"
            bind:value={preferences.task_default_due_date_offset_days}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each preferences.default_due_date_offset_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Task automation</h2>
      <div class="space-y-3">
        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.auto_follow_assigned_tasks}
            class="rounded border-neutral-300"
          />
          Auto-follow tasks assigned to me
        </label>

        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.auto_subscribe_project_updates}
            class="rounded border-neutral-300"
          />
          Auto-subscribe to project updates
        </label>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Approval delegation rules</h2>
      <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div>
          <label for="approval_delegation_rule" class="mb-1.5 block text-sm font-medium text-neutral-700">Rule</label>
          <select
            id="approval_delegation_rule"
            bind:value={preferences.approval_delegation_rule}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each preferences.approval_delegation_rule_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm text-neutral-700">
            Delegation assignments are managed in the workflow delegation center.
          </p>
          <a
            href={preferences.delegations_path}
            class="mt-2 inline-flex text-sm font-semibold text-neutral-700 hover:text-neutral-900"
          >
            Open Delegations
          </a>
        </div>
      </div>
    </section>
  </div>
{/if}
