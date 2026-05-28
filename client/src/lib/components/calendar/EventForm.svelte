<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type {
    CalendarEventCreatePayload,
    CalendarEventDetail,
    CalendarEventKind,
    CalendarEventVisibility,
    UserDirectoryItem,
  } from "$lib/types";
  import UserPicker from "$lib/components/teams/UserPicker.svelte";
  import RecurrenceEditor from "./RecurrenceEditor.svelte";
  import TimeInput from "./TimeInput.svelte";
  import { KIND_TREATMENT, KIND_ICON_PATH, KIND_ORDER } from "./event-kinds";

  /**
   * Kind-aware create/edit form for CalendarEvent.
   *
   * Sections (UI spec §4.2):
   *  1. Type — kind selector (2x2 grid)
   *  2. Identity — title, description
   *  3. When — starts_at, ends_at (hidden for reminder), all_day, repeats
   *  4. Attendees — only when kind=meeting; uses UserPicker
   *  5. Where — location, meeting_link (kind-conditional)
   *  6. Reminder — single picker
   *  7. Visibility — radio
   *  8. Team — required when visibility=team
   *
   * Emits a clean payload via `onsubmit`. Validation is inline (text errors
   * appear below the offending field on submit attempt).
   */

  interface Props {
    /** Initial values (edit) or empty (create). */
    initial?: Partial<CalendarEventDetail>;
    /** "create" or "edit" — controls submit button label. */
    mode?: "create" | "edit";
    /** When true, kind selector is disabled (edit case — can't switch kinds). */
    lockKind?: boolean;
    /** Default reminder pulled from user prefs. */
    userDefaultReminder?: number;
    /** Submit handler — receives the clean payload. */
    onsubmit: (payload: CalendarEventCreatePayload) => void | Promise<void>;
    /** Cancel handler. */
    oncancel: () => void;
    /** Submission in flight — disables form + shows spinner. */
    submitting?: boolean;
  }

  let {
    initial = {},
    mode = "create",
    lockKind = false,
    userDefaultReminder = 15,
    onsubmit,
    oncancel,
    submitting = false,
  }: Props = $props();

  // ----- form state --------------------------------------------------------

  let kind = $state<CalendarEventKind>((initial.kind as CalendarEventKind) ?? "meeting");
  let title = $state<string>(initial.title ?? "");
  let description = $state<string>(initial.description ?? "");
  let location = $state<string>(initial.location ?? "");
  let meetingLink = $state<string>(initial.meeting_link ?? "");
  let startsAt = $state<string>(initial.starts_at ?? defaultStartsAt());
  let endsAt = $state<string>(initial.ends_at ?? defaultEndsAt(initial.starts_at));
  let allDay = $state<boolean>(initial.all_day ?? false);
  let timezone = $state<string>(
    initial.timezone ?? (Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"),
  );
  let recurrenceRule = $state<string>(initial.recurrence_rule ?? "");
  let recurrenceEnabled = $state<boolean>(!!initial.recurrence_rule);
  let visibility = $state<CalendarEventVisibility>(
    (initial.visibility as CalendarEventVisibility) ?? "private",
  );
  let team = $state<number | null>(initial.team ?? null);
  let reminderMode = $state<"default" | "off" | "value">(
    initial.reminder_minutes_before == null
      ? "default"
      : initial.reminder_minutes_before === 0
        ? "off"
        : "value",
  );
  let reminderMinutes = $state<number>(
    initial.reminder_minutes_before != null && initial.reminder_minutes_before > 0
      ? initial.reminder_minutes_before
      : userDefaultReminder,
  );
  let pickedAttendees = $state<UserDirectoryItem[]>([]);

  let errors = $state<Record<string, string>>({});

  // ----- helpers -----------------------------------------------------------

  function defaultStartsAt(): string {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 1);
    return d.toISOString().slice(0, 19) + "Z";
  }
  function defaultEndsAt(start: string | undefined | null): string {
    const base = start ? new Date(start) : new Date(defaultStartsAt());
    const d = new Date(base);
    d.setMinutes(d.getMinutes() + 30);
    return d.toISOString().slice(0, 19) + "Z";
  }

  // Whenever start changes & ends < start, auto-bump end.
  $effect(() => {
    if (kind === "reminder") return;
    if (!startsAt) return;
    if (!endsAt || new Date(endsAt) < new Date(startsAt)) {
      endsAt = defaultEndsAt(startsAt);
    }
  });

  // ----- validation --------------------------------------------------------

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!title.trim()) e.title = i18n.t("workspace.calendar.form.errors.title_required");
    if (!startsAt) e.starts_at = i18n.t("workspace.calendar.form.errors.starts_required");
    if (kind !== "reminder") {
      if (!endsAt) e.ends_at = i18n.t("workspace.calendar.form.errors.ends_required");
      else if (new Date(endsAt) < new Date(startsAt))
        e.ends_at = i18n.t("workspace.calendar.form.errors.ends_after_starts");
    }
    if (visibility === "team" && !team) e.team = i18n.t("workspace.calendar.form.errors.team_required");
    errors = e;
    return Object.keys(e).length === 0;
  }

  function submit() {
    if (!validate()) return;
    const externalEmails: string[] = []; // v1: external emails not wired in UI
    const reminder: number | null =
      reminderMode === "default" ? null : reminderMode === "off" ? 0 : reminderMinutes;
    const payload: CalendarEventCreatePayload = {
      title: title.trim(),
      description,
      location: kind === "focus" ? "" : location,
      meeting_link: kind === "out_of_office" || kind === "reminder" ? "" : meetingLink,
      external_attendee_emails: externalEmails,
      kind,
      visibility,
      team,
      starts_at: startsAt,
      ends_at: kind === "reminder" ? null : endsAt,
      all_day: allDay,
      timezone,
      recurrence_rule: recurrenceEnabled ? recurrenceRule : "",
      reminder_minutes_before: reminder,
    };
    onsubmit(payload);
  }

  function devFill() {
    title = "Demo: weekly sync";
    description = "Auto-populated by Dev Fill.";
    location = "Conference Room 3";
    meetingLink = "https://example.com/meeting";
    kind = "meeting";
    visibility = "private";
  }

  // Reminder presets
  const REMINDER_PRESETS = [
    { value: "default", label_key: "workspace.calendar.form.reminder.default" },
    { value: "off", label_key: "workspace.calendar.form.reminder.off" },
    { value: 5, label_key: "workspace.calendar.form.reminder.5min" },
    { value: 15, label_key: "workspace.calendar.form.reminder.15min" },
    { value: 30, label_key: "workspace.calendar.form.reminder.30min" },
    { value: 60, label_key: "workspace.calendar.form.reminder.1hr" },
    { value: 1440, label_key: "workspace.calendar.form.reminder.1day" },
  ];

  function setReminderPreset(value: string | number) {
    if (value === "default") {
      reminderMode = "default";
    } else if (value === "off") {
      reminderMode = "off";
    } else {
      reminderMode = "value";
      reminderMinutes = value as number;
    }
  }

  function currentReminderValue(): string | number {
    if (reminderMode === "default") return "default";
    if (reminderMode === "off") return "off";
    return reminderMinutes;
  }
</script>

<form
  class="space-y-6"
  onsubmit={(e) => {
    e.preventDefault();
    submit();
  }}
>
  <!-- Section 1: Kind -->
  <section class="rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.form.section.type")}
    </h2>
    <p class="mt-1 text-sm text-neutral-500">
      {i18n.t("workspace.calendar.form.type_helper")}
    </p>
    <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {#each KIND_ORDER as k}
        {@const t = KIND_TREATMENT[k]}
        <button
          type="button"
          disabled={lockKind && k !== kind}
          onclick={() => (kind = k)}
          class="flex flex-col items-center justify-center gap-2 rounded-2xl border px-4 py-4 text-center transition disabled:cursor-not-allowed disabled:opacity-50 {kind === k ? 'border-neutral-900 bg-neutral-50 ring-2 ring-neutral-900/10' : 'border-neutral-200 bg-white hover:border-neutral-400'}"
        >
          <span class="inline-flex h-10 w-10 items-center justify-center rounded-xl {t.block}">
            <svg
              class="h-5 w-5 {t.iconColor}"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d={KIND_ICON_PATH[k]} />
            </svg>
          </span>
          <span class="text-sm font-semibold text-neutral-900">
            {i18n.t(`workspace.calendar.kind.${k}`)}
          </span>
        </button>
      {/each}
    </div>
  </section>

  <!-- Section 2: Identity -->
  <section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.form.section.identity")}
    </h2>
    <div>
      <label for="evt-title" class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.form.title")} *
      </label>
      <input
        id="evt-title"
        type="text"
        bind:value={title}
        placeholder={i18n.t("workspace.calendar.form.title_placeholder")}
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
      {#if errors.title}
        <p class="mt-1 text-xs text-rose-600">{errors.title}</p>
      {/if}
    </div>
    <div>
      <label for="evt-desc" class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.form.description")}
      </label>
      <textarea
        id="evt-desc"
        bind:value={description}
        rows="3"
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      ></textarea>
    </div>
  </section>

  <!-- Section 3: When -->
  <section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.form.section.when")}
    </h2>
    <label class="inline-flex cursor-pointer items-center gap-2">
      <input type="checkbox" bind:checked={allDay} class="h-4 w-4 accent-neutral-900" />
      <span class="text-sm text-neutral-700">{i18n.t("workspace.calendar.form.all_day")}</span>
    </label>
    <TimeInput
      label={i18n.t("workspace.calendar.form.starts_at")}
      bind:value={startsAt}
      {timezone}
      dateOnly={allDay}
      id="evt-starts"
    />
    {#if errors.starts_at}
      <p class="text-xs text-rose-600">{errors.starts_at}</p>
    {/if}
    {#if kind !== "reminder"}
      <TimeInput
        label={i18n.t("workspace.calendar.form.ends_at")}
        bind:value={endsAt}
        {timezone}
        dateOnly={allDay}
        id="evt-ends"
      />
      {#if errors.ends_at}
        <p class="text-xs text-rose-600">{errors.ends_at}</p>
      {/if}
    {/if}

    <label class="inline-flex cursor-pointer items-center gap-2 pt-2">
      <input type="checkbox" bind:checked={recurrenceEnabled} class="h-4 w-4 accent-neutral-900" />
      <span class="text-sm text-neutral-700">{i18n.t("workspace.calendar.form.repeats")}</span>
    </label>
    {#if recurrenceEnabled}
      <RecurrenceEditor bind:rule={recurrenceRule} />
    {/if}
  </section>

  <!-- Section 4: Attendees (kind=meeting only) -->
  {#if kind === "meeting"}
    <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5">
      <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.form.section.attendees")}
      </h2>
      <UserPicker multiple bind:selected={pickedAttendees} />
      <p class="text-xs text-neutral-500">
        {i18n.t("workspace.calendar.form.attendees_helper")}
      </p>
    </section>
  {/if}

  <!-- Section 5: Where -->
  {#if kind !== "focus"}
    <section class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
      <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.form.section.where")}
      </h2>
      <div>
        <label for="evt-loc" class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
          {i18n.t("workspace.calendar.form.location")}
        </label>
        <input
          id="evt-loc"
          type="text"
          bind:value={location}
          class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        />
      </div>
      {#if kind === "meeting"}
        <div>
          <label for="evt-link" class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
            {i18n.t("workspace.calendar.form.meeting_link")}
          </label>
          <input
            id="evt-link"
            type="url"
            bind:value={meetingLink}
            class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
        </div>
      {/if}
    </section>
  {/if}

  <!-- Section 6: Reminder -->
  {#if kind !== "out_of_office"}
    <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5">
      <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.form.section.reminder")}
      </h2>
      <div class="flex flex-wrap gap-2">
        {#each REMINDER_PRESETS as preset}
          {@const isActive = currentReminderValue() === preset.value}
          <button
            type="button"
            onclick={() => setReminderPreset(preset.value)}
            class="rounded-full border px-3 py-1 text-xs font-semibold {isActive ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
          >
            {i18n.t(preset.label_key)}
          </button>
        {/each}
      </div>
    </section>
  {/if}

  <!-- Section 7: Visibility -->
  <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5">
    <h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.form.section.visibility")}
    </h2>
    {#each ["private", "team", "org"] as v}
      <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200 bg-white p-3 hover:border-neutral-400">
        <input
          type="radio"
          name="visibility"
          value={v}
          bind:group={visibility}
          class="mt-0.5 h-4 w-4 accent-neutral-900"
        />
        <span>
          <span class="block text-sm font-semibold text-neutral-900">
            {i18n.t(`workspace.calendar.visibility.${v}`)}
          </span>
          <span class="mt-0.5 block text-xs text-neutral-500">
            {i18n.t(`workspace.calendar.visibility.${v}_helper`)}
          </span>
        </span>
      </label>
    {/each}
    {#if errors.team}
      <p class="text-xs text-rose-600">{errors.team}</p>
    {/if}
  </section>

  <!-- Footer actions -->
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
        {#if submitting}{i18n.t("common.actions.saving")}{:else if mode === "create"}{i18n.t("workspace.calendar.form.create")}{:else}{i18n.t("workspace.calendar.form.save")}{/if}
      </button>
    </div>
  </div>
</form>
