<script lang="ts">
  import type {
    InternalTaskCreatePayload,
    InternalTaskDetail,
    InternalTaskPriority,
    InternalTaskStatus,
    InternalTaskVisibility,
    InternalTaskChecklistItem,
    UserDirectoryItem,
  } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import UserPicker from "$lib/components/teams/UserPicker.svelte";
  import { STATUS_ORDER, STATUS_TREATMENT } from "./task-status";
  import { PRIORITY_ORDER, PRIORITY_TREATMENT } from "./task-priority";
  import ChecklistEditor from "./ChecklistEditor.svelte";
  import TagInput from "./TagInput.svelte";

  /**
   * Create + edit form. Sections per UI spec §:
   *   1. Identity (title, description)
   *   2. Status / Priority
   *   3. Assignment (assignee picker)
   *   4. Visibility (radio: private / team / org; team picker conditional)
   *   5. Schedule (due_date)
   *   6. Tags + Checklist
   *
   * Validation:
   *   - title required (max 200, trimmed)
   *   - visibility=team requires team to be set (we surface a friendly
   *     error since the server will 400 if it's not)
   */

  interface Props {
    initial?: Partial<InternalTaskDetail>;
    mode?: "create" | "edit";
    /** True when the current user is creator (controls whether team/visibility editable). */
    canChangeOwnership?: boolean;
    onsubmit: (payload: InternalTaskCreatePayload) => void | Promise<void>;
    oncancel: () => void;
    submitting?: boolean;
  }

  let {
    initial = {},
    mode = "create",
    canChangeOwnership = true,
    onsubmit,
    oncancel,
    submitting = false,
  }: Props = $props();

  // ----- form state ----------------------------------------------------------

  let title = $state(initial.title ?? "");
  let description = $state(initial.description ?? "");
  let status = $state<InternalTaskStatus>(initial.status ?? "todo");
  let priority = $state<InternalTaskPriority>(initial.priority ?? "medium");
  let visibility = $state<InternalTaskVisibility>(initial.visibility ?? "private");
  let team = $state<number | null>(initial.team ?? null);
  let dueDate = $state<string>(initial.due_date ?? "");
  let tags = $state<string[]>(initial.tags ?? []);
  let checklist = $state<InternalTaskChecklistItem[]>(initial.checklist_items ?? []);

  // Assignee — assignee may be the embedded user object on detail, but on
  // create we want the id. Track as a UserPicker selection (single).
  let pickedAssignees = $state<UserDirectoryItem[]>(
    initial.assignee
      ? [
          {
            id: initial.assignee.id,
            profile_id: 0,
            full_name: initial.assignee.name,
            email: initial.assignee.email,
            phone: "",
            job_title: "",
            department_name: "",
            role_name: "",
            user_status: "active",
            user_status_display: "Active",
            last_login: null,
            mfa_enabled: false,
            identity_type: "human",
            identity_type_display: "Human",
          } as UserDirectoryItem,
        ]
      : [],
  );

  let errors = $state<Record<string, string>>({});

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!title.trim()) e.title = i18n.t("workspace.internal_tasks.form.errors.title_required");
    if (visibility === "team" && team == null) {
      e.team = i18n.t("workspace.internal_tasks.form.errors.team_required");
    }
    errors = e;
    return Object.keys(e).length === 0;
  }

  function submit() {
    if (!validate()) return;
    const payload: InternalTaskCreatePayload = {
      title: title.trim(),
      description,
      status,
      priority,
      visibility,
      team,
      assignee: pickedAssignees[0]?.id ?? null,
      due_date: dueDate || null,
      tags,
      checklist_items: checklist,
    };
    onsubmit(payload);
  }

  function devFill() {
    title = "Submit Q3 board pack";
    description = "Coordinate with finance + legal; final draft by EOW.";
    priority = "high";
    tags = ["board", "q3"];
    checklist = [
      { label: "Draft", checked: false },
      { label: "Review with Joan", checked: false },
      { label: "Send to chair", checked: false },
    ];
  }
</script>

<form
  class="space-y-6"
  onsubmit={(e) => {
    e.preventDefault();
    submit();
  }}
>
  <!-- Section 1: Identity -->
  <section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.internal_tasks.form.section.identity")}
    </h2>
    <div>
      <label
        for="task-title"
        class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400"
      >
        {i18n.t("workspace.internal_tasks.form.title")} *
      </label>
      <input
        id="task-title"
        type="text"
        bind:value={title}
        placeholder={i18n.t("workspace.internal_tasks.form.title_placeholder")}
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
      {#if errors.title}
        <p class="mt-1 text-xs text-rose-600">{errors.title}</p>
      {/if}
    </div>
    <div>
      <label
        for="task-desc"
        class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400"
      >
        {i18n.t("workspace.internal_tasks.form.description")}
      </label>
      <textarea
        id="task-desc"
        bind:value={description}
        rows="3"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      ></textarea>
    </div>
  </section>

  <!-- Section 2: Status + Priority -->
  <section class="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-5 sm:grid-cols-2">
    <div>
      <h2 class="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.internal_tasks.form.section.status")}
      </h2>
      <div class="flex flex-wrap gap-2">
        {#each STATUS_ORDER as s}
          {@const t = STATUS_TREATMENT[s]}
          <button
            type="button"
            onclick={() => (status = s)}
            class="rounded-full border px-3 py-1 text-xs font-semibold {status === s ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
          >
            {i18n.t(t.labelKey)}
          </button>
        {/each}
      </div>
    </div>
    <div>
      <h2 class="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.internal_tasks.form.section.priority")}
      </h2>
      <div class="flex flex-wrap gap-2">
        {#each PRIORITY_ORDER as p}
          {@const t = PRIORITY_TREATMENT[p]}
          <button
            type="button"
            onclick={() => (priority = p)}
            class="rounded-full border px-3 py-1 text-xs font-semibold {priority === p ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
          >
            {i18n.t(t.labelKey)}
          </button>
        {/each}
      </div>
    </div>
  </section>

  <!-- Section 3: Assignment -->
  <section class="space-y-2 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.internal_tasks.form.section.assignment")}
    </h2>
    <p class="text-xs text-neutral-500">
      {i18n.t("workspace.internal_tasks.form.assignee_helper")}
    </p>
    <UserPicker bind:selected={pickedAssignees} />
    {#if pickedAssignees.length === 0}
      <p class="text-xs text-neutral-400">
        {i18n.t("workspace.internal_tasks.form.assignee_empty")}
      </p>
    {/if}
  </section>

  <!-- Section 4: Visibility -->
  <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.internal_tasks.form.section.visibility")}
    </h2>
    {#each ["private", "team", "org"] as v}
      <label
        class="flex cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200 bg-white p-3 hover:border-neutral-400 {!canChangeOwnership && mode === 'edit' ? 'opacity-60' : ''}"
      >
        <input
          type="radio"
          name="visibility"
          value={v}
          bind:group={visibility}
          disabled={!canChangeOwnership && mode === "edit"}
          class="mt-0.5 h-4 w-4 accent-neutral-900"
        />
        <span>
          <span class="block text-sm font-semibold text-neutral-900">
            {i18n.t(`workspace.internal_tasks.visibility.${v}`)}
          </span>
          <span class="mt-0.5 block text-xs text-neutral-500">
            {i18n.t(`workspace.internal_tasks.visibility.${v}_helper`)}
          </span>
        </span>
      </label>
    {/each}
    {#if errors.team}
      <p class="text-xs text-rose-600">{errors.team}</p>
    {/if}
  </section>

  <!-- Section 5: Schedule -->
  <section class="space-y-2 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.internal_tasks.form.section.schedule")}
    </h2>
    <label
      for="task-due"
      class="block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400"
    >
      {i18n.t("workspace.internal_tasks.form.due_date")}
    </label>
    <input
      id="task-due"
      type="date"
      bind:value={dueDate}
      class="rounded-2xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
    />
  </section>

  <!-- Section 6: Tags + Checklist -->
  <section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
    <div>
      <h2 class="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.internal_tasks.form.section.tags")}
      </h2>
      <TagInput bind:tags />
    </div>
    <div>
      <h2 class="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.internal_tasks.form.section.checklist")}
      </h2>
      <ChecklistEditor bind:items={checklist} />
    </div>
  </section>

  <!-- Footer -->
  <div class="sticky bottom-0 -mx-1 flex flex-wrap items-center justify-between gap-2 border-t border-neutral-200 bg-neutral-50 px-1 py-3">
    <button
      type="button"
      onclick={devFill}
      class="rounded-lg border border-dashed border-neutral-300 bg-white px-3 py-2 text-xs font-semibold text-neutral-500 hover:border-neutral-400"
    >
      Dev Fill
    </button>
    <div class="flex items-center gap-2">
      <button
        type="button"
        onclick={oncancel}
        disabled={submitting}
        class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {i18n.t("common.actions.cancel")}
      </button>
      <button
        type="submit"
        disabled={submitting}
        class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
      >
        {#if submitting}{i18n.t("common.actions.saving")}{:else if mode === "create"}{i18n.t("workspace.internal_tasks.form.create")}{:else}{i18n.t("workspace.internal_tasks.form.save")}{/if}
      </button>
    </div>
  </div>
</form>
