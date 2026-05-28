<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    ActivityTaskOverview,
    FollowUpTaskListItem,
    LeadActivity,
    LeadListItem,
    PaginatedResponse,
  } from "$lib/types";

  type Panel = "timeline" | "activities" | "tasks";

  type UserDirectoryItem = {
    id: number;
    full_name: string;
    email: string;
  };

  const activityPageSize = 10;
  const taskPageSize = 10;

  const activityTypeOptions = [
    { value: "call", label: "Call" },
    { value: "email", label: "Email" },
    { value: "meeting", label: "Meeting" },
    { value: "site_visit", label: "Site Visit" },
    { value: "follow_up", label: "Follow-Up" },
    { value: "note", label: "Note" },
    { value: "other", label: "Other" },
  ];

  let loading = $state(true);
  let panel = $state<Panel>("timeline");

  let overview = $state<ActivityTaskOverview | null>(null);
  let activities = $state<LeadActivity[]>([]);
  let tasks = $state<FollowUpTaskListItem[]>([]);
  let workspaceError = $state<string | null>(null);
  let activityCount = $state(0);
  let taskCount = $state(0);
  let activityPage = $state(1);
  let taskPage = $state(1);
  let leads = $state<LeadListItem[]>([]);
  let users = $state<UserDirectoryItem[]>([]);

  let activitySearch = $state("");
  let activityType = $state("");
  let activityCompleted = $state("");
  let taskStatus = $state("");

  let showActivityForm = $state(false);
  let showTaskForm = $state(false);
  let activityErrors = $state<Record<string, string[]>>({});
  let taskErrors = $state<Record<string, string[]>>({});
  let savingActivity = $state(false);
  let savingTask = $state(false);

  let activityTotalPages = $derived(Math.max(1, Math.ceil(activityCount / activityPageSize)));
  let taskTotalPages = $derived(Math.max(1, Math.ceil(taskCount / taskPageSize)));

  let activityPageNumbers = $derived.by(() => pageNumbers(activityPage, activityTotalPages));
  let taskPageNumbers = $derived.by(() => pageNumbers(taskPage, taskTotalPages));

  let activityForm = $state({
    lead: "",
    activity_type: "call",
    subject: "",
    description: "",
    scheduled_at: "",
  });

  let taskForm = $state({
    lead: "",
    due_at: "",
    assigned_to: "",
    notes: "",
  });

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const ACTIVITY_SAMPLES = [
    { activity_type: "site_visit", subject: "Site inspection — Block A Units 12-16", description: "Client wants to see finishing quality and view from upper floors. Bring brochure for Phase 3 pricing." },
    { activity_type: "call", subject: "Pricing discussion — Ikoyi 3-bed units", description: "Called client to discuss updated pricing for Ikoyi Waterfront 3-bed units. Client comparing with competitor project on Bourdillon." },
    { activity_type: "meeting", subject: "Contract review meeting with legal team", description: "Meeting with client and their solicitor to review SPA terms. Client requested clause amendments on completion timeline." },
    { activity_type: "email", subject: "Sent payment plan breakdown — Eko Atlantic", description: "Emailed detailed payment plan options (60/40 and 30/30/40) as requested during last call. Awaiting client response." },
  ];

  const TASK_SAMPLES = [
    { notes: "Follow up on payment plan discussion. Client requested 18-month instalment option." },
    { notes: "Send updated floor plans for Block B penthouse units. Client comparing with Banana Island options." },
    { notes: "Confirm site visit logistics for Friday. Client arriving from Abuja — arrange airport pickup if needed." },
    { notes: "Chase mortgage pre-approval status with GTBank relationship manager. Client expecting response this week." },
  ];

  let devIdx = $state(0);

  function devFillActivity() {
    const sample = ACTIVITY_SAMPLES[devIdx % ACTIVITY_SAMPLES.length];
    devIdx++;
    activityForm.activity_type = sample.activity_type;
    activityForm.subject = sample.subject;
    activityForm.description = sample.description;
    activityForm.scheduled_at = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 16);
    if (leads.length > 0) activityForm.lead = String(leads[devIdx % leads.length].id);
  }

  function devFillTask() {
    const sample = TASK_SAMPLES[devIdx % TASK_SAMPLES.length];
    devIdx++;
    taskForm.notes = sample.notes;
    taskForm.due_at = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 16);
    if (leads.length > 0) taskForm.lead = String(leads[devIdx % leads.length].id);
    if (users.length > 0) taskForm.assigned_to = String(users[devIdx % users.length].id);
  }

  function fmtDateTime(value: string | null): string {
    if (!value) return "\u2014";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "\u2014";
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function statusBadge(status: string): string {
    if (status === "completed") return "bg-emerald-100 text-emerald-700";
    if (status === "escalated") return "bg-rose-100 text-rose-700";
    if (status === "breached") return "bg-amber-100 text-amber-700";
    if (status === "in_progress") return "bg-sky-100 text-sky-700";
    return "bg-neutral-100 text-neutral-700";
  }

  function pageNumbers(current: number, total: number): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1);
    for (let page = start; page <= end; page += 1) pages.push(page);
    return pages;
  }

  function goToActivityPage(page: number) {
    if (page < 1 || page > activityTotalPages || page === activityPage) return;
    activityPage = page;
    void fetchActivities();
  }

  function goToTaskPage(page: number) {
    if (page < 1 || page > taskTotalPages || page === taskPage) return;
    taskPage = page;
    void fetchTasks();
  }

  function resetActivitiesPageAndFetch() {
    activityPage = 1;
    void fetchActivities();
  }

  function resetTasksPageAndFetch() {
    taskPage = 1;
    void fetchTasks();
  }

  async function fetchOverview() {
    overview = await api.get<ActivityTaskOverview>("/crm/activities-tasks/overview/");
  }

  async function fetchActivities() {
    const params: Record<string, string> = {
      page: String(activityPage),
      page_size: String(activityPageSize),
      ordering: "-created_at",
    };
    if (activitySearch.trim()) params.search = activitySearch.trim();
    if (activityType) params.activity_type = activityType;
    if (activityCompleted === "true" || activityCompleted === "false") params.is_completed = activityCompleted;
    const res = await api.get<PaginatedResponse<LeadActivity>>("/crm/activities/", params);
    const totalPages = Math.max(1, Math.ceil(res.count / activityPageSize));
    if (activityPage > totalPages) {
      activityPage = totalPages;
      return fetchActivities();
    }
    activities = res.results;
    activityCount = res.count;
  }

  async function fetchTasks() {
    const params: Record<string, string> = {
      page: String(taskPage),
      page_size: String(taskPageSize),
      ordering: "due_at",
    };
    if (taskStatus) params.status = taskStatus;
    const res = await api.get<PaginatedResponse<FollowUpTaskListItem>>("/crm/follow-up-tasks/", params);
    const totalPages = Math.max(1, Math.ceil(res.count / taskPageSize));
    if (taskPage > totalPages) {
      taskPage = totalPages;
      return fetchTasks();
    }
    tasks = res.results;
    taskCount = res.count;
  }

  async function fetchLeads() {
    const res = await api.get<PaginatedResponse<LeadListItem>>("/crm/leads/", {
      status: "active",
      page_size: "200",
      ordering: "-updated_at",
    });
    leads = res.results;
  }

  async function fetchUsers() {
    try {
      const res = await api.get<PaginatedResponse<UserDirectoryItem>>("/iam/users/", {
        status: "active",
        page_size: "200",
      });
      users = res.results;
    } catch (err) {
      console.error("[crm/activities-tasks]", err);
      users = [];
    }
  }

  async function loadAll() {
    loading = true;
    workspaceError = null;
    try {
      await Promise.all([fetchOverview(), fetchActivities(), fetchTasks(), fetchLeads(), fetchUsers()]);
    } catch (err) {
      console.error("[crm/activities-tasks]", err);
      workspaceError = err instanceof Error ? err.message : "Could not load activities and tasks workspace.";
      toast.error("Load failed", "Could not load activities and tasks workspace.");
    } finally {
      loading = false;
    }
  }

  function openActivityDrawer() {
    showActivityForm = true;
    showTaskForm = false;
    activityErrors = {};
  }

  function closeActivityDrawer() {
    showActivityForm = false;
    activityErrors = {};
  }

  function openTaskDrawer() {
    showTaskForm = true;
    showActivityForm = false;
    taskErrors = {};
  }

  function closeTaskDrawer() {
    showTaskForm = false;
    taskErrors = {};
  }

  async function submitActivity(event: Event) {
    event.preventDefault();
    savingActivity = true;
    activityErrors = {};
    try {
      const payload: Record<string, unknown> = {
        lead: Number(activityForm.lead),
        activity_type: activityForm.activity_type,
        subject: activityForm.subject.trim(),
        description: activityForm.description.trim(),
      };
      if (activityForm.scheduled_at) payload.scheduled_at = new Date(activityForm.scheduled_at).toISOString();
      await api.post("/crm/activities/", payload);

      const successMessage = activityForm.activity_type === "site_visit"
        ? "Site visit scheduled. Client and logistics notifications were triggered."
        : "Activity logged successfully.";
      toast.success("Saved", successMessage);
      closeActivityDrawer();
      activityForm = { lead: "", activity_type: "call", subject: "", description: "", scheduled_at: "" };
      await Promise.all([fetchOverview(), fetchActivities(), fetchTasks()]);
      panel = "timeline";
    } catch (error) {
      console.error("[crm/activities-tasks]", error);
      if (error instanceof ApiError) {
        activityErrors = error.fieldErrors;
      }
      toast.error("Save failed", "Could not create activity.");
    } finally {
      savingActivity = false;
    }
  }

  async function submitTask(event: Event) {
    event.preventDefault();
    savingTask = true;
    taskErrors = {};
    try {
      const payload: Record<string, unknown> = {
        lead: Number(taskForm.lead),
        due_at: new Date(taskForm.due_at).toISOString(),
        notes: taskForm.notes.trim(),
      };
      if (taskForm.assigned_to) payload.assigned_to = Number(taskForm.assigned_to);
      await api.post("/crm/follow-up-tasks/manual-create/", payload);
      toast.success("Task assigned", "Reminder workflow is now active for this task.");
      closeTaskDrawer();
      taskForm = { lead: "", due_at: "", assigned_to: "", notes: "" };
      await Promise.all([fetchOverview(), fetchTasks()]);
      panel = "tasks";
    } catch (error) {
      console.error("[crm/activities-tasks]", error);
      if (error instanceof ApiError) {
        taskErrors = error.fieldErrors;
      }
      toast.error("Save failed", "Could not assign task.");
    } finally {
      savingTask = false;
    }
  }

  async function completeTask(taskId: number) {
    try {
      await api.post(`/crm/follow-up-tasks/${taskId}/complete_task/`, {});
      toast.success("Task completed");
      await Promise.all([fetchOverview(), fetchTasks()]);
    } catch (err) {
      console.error("[crm/activities-tasks]", err);
      toast.error("Update failed", "Could not complete task.");
    }
  }

  async function escalateTask(taskId: number) {
    try {
      await api.post(`/crm/follow-up-tasks/${taskId}/escalate/`, {});
      toast.success("Task escalated");
      await Promise.all([fetchOverview(), fetchTasks()]);
    } catch (err) {
      console.error("[crm/activities-tasks]", err);
      toast.error("Update failed", "Could not escalate task.");
    }
  }

  onMount(() => {
    void loadAll();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Activities & Task Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Track calls, emails, meetings, and site visits with assignment, reminders, calendar visibility, and timeline context.
      </p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <button
        onclick={openActivityDrawer}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
      >
        Log Activity
      </button>
      <button
        onclick={openTaskDrawer}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
      >
        Assign Task
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-6">
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Activities</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview?.total_activities ?? 0}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Upcoming</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview?.scheduled_upcoming_count ?? 0}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Missed</p>
        <p class="mt-2 text-2xl font-semibold text-rose-700">{overview?.missed_activities_count ?? 0}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Open Tasks</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview?.open_task_count ?? 0}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Overdue</p>
        <p class="mt-2 text-2xl font-semibold text-amber-700">{overview?.overdue_task_count ?? 0}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Escalated</p>
        <p class="mt-2 text-2xl font-semibold text-rose-700">{overview?.escalated_task_count ?? 0}</p>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 px-5 py-4">
        <div class="flex items-center gap-2">
          <button onclick={() => (panel = "timeline")} class="rounded-md px-3 py-1.5 text-sm {panel === 'timeline' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}">Timeline</button>
          <button onclick={() => (panel = 'activities')} class="rounded-md px-3 py-1.5 text-sm {panel === 'activities' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}">Activities</button>
          <button onclick={() => (panel = 'tasks')} class="rounded-md px-3 py-1.5 text-sm {panel === 'tasks' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}">Tasks</button>
        </div>
      </div>

      {#if panel === "timeline"}
        <div class="p-5">
          <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div class="rounded-lg border border-neutral-200 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Google Sync</p>
              <p class="mt-1 text-sm font-medium {overview?.calendar_integration.google_sync_enabled ? 'text-emerald-700' : 'text-neutral-500'}">
                {overview?.calendar_integration.google_sync_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
            <div class="rounded-lg border border-neutral-200 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Outlook Sync</p>
              <p class="mt-1 text-sm font-medium {overview?.calendar_integration.outlook_sync_enabled ? 'text-emerald-700' : 'text-neutral-500'}">
                {overview?.calendar_integration.outlook_sync_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
            <div class="rounded-lg border border-neutral-200 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">iCal Sync</p>
              <p class="mt-1 text-sm font-medium {overview?.calendar_integration.ical_sync_enabled ? 'text-emerald-700' : 'text-neutral-500'}">
                {overview?.calendar_integration.ical_sync_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
          </div>

          <div class="mt-5 space-y-3">
            {#if !overview?.timeline.length}
              <p class="rounded-lg border border-dashed border-neutral-300 px-4 py-8 text-center text-sm text-neutral-500">
                No activity timeline entries yet.
              </p>
            {:else}
              {#each overview.timeline as row}
                <div class="flex items-start gap-3 rounded-lg border border-neutral-200 px-4 py-3">
                  <div class="mt-1 h-2.5 w-2.5 rounded-full {row.kind === 'activity' ? 'bg-sky-500' : 'bg-amber-500'}"></div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <p class="text-sm font-semibold text-neutral-900">{row.title}</p>
                      <span class="rounded-full px-2 py-0.5 text-[11px] font-medium {statusBadge(row.status)}">{row.status_display}</span>
                    </div>
                    <p class="mt-0.5 text-xs text-neutral-500">{row.lead_name} • {row.subtitle}</p>
                  </div>
                  <p class="text-xs text-neutral-400">{fmtDateTime(row.timestamp)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      {/if}

      {#if panel === "activities"}
        <div class="p-5">
          <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
            <input
              class="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
              placeholder="Search subject, lead..."
              bind:value={activitySearch}
              oninput={resetActivitiesPageAndFetch}
            />
            <select class="rounded-lg border border-neutral-300 px-3 py-2 text-sm" bind:value={activityType} onchange={resetActivitiesPageAndFetch}>
              <option value="">All Types</option>
              {#each activityTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
            <select class="rounded-lg border border-neutral-300 px-3 py-2 text-sm" bind:value={activityCompleted} onchange={resetActivitiesPageAndFetch}>
              <option value="">All Status</option>
              <option value="false">Pending</option>
              <option value="true">Completed</option>
            </select>
          </div>

          <div class="mt-4 overflow-x-auto">
            <table class="w-full min-w-[760px]">
              <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-3 py-2">Lead</th>
                  <th class="px-3 py-2">Type</th>
                  <th class="px-3 py-2">Subject</th>
                  <th class="px-3 py-2">Scheduled</th>
                  <th class="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if workspaceError}
                  <tr>
                    <td colspan="5" class="px-3 py-6">
                      <DataStateBanner
                        title="Couldn't load activities"
                        message={workspaceError}
                        onretry={loadAll}
                      />
                    </td>
                  </tr>
                {:else if activities.length === 0}
                  <tr><td colspan="5" class="px-3 py-10 text-center text-sm text-neutral-500">No activities found.</td></tr>
                {:else}
                  {#each activities as row}
                    <tr class="text-sm text-neutral-700">
                      <td class="px-3 py-3 font-medium text-neutral-900">{row.lead_name}</td>
                      <td class="px-3 py-3">{row.activity_type_display}</td>
                      <td class="px-3 py-3">{row.subject}</td>
                      <td class="px-3 py-3">{fmtDateTime(row.scheduled_at)}</td>
                      <td class="px-3 py-3">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {statusBadge(row.is_completed ? 'completed' : 'pending')}">
                          {row.is_completed ? "Completed" : "Pending"}
                        </span>
                      </td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-3">
            <p class="text-sm text-neutral-500">
              Showing {activityCount === 0 ? 0 : (activityPage - 1) * activityPageSize + 1}&ndash;{Math.min(activityPage * activityPageSize, activityCount)} of {activityCount}
            </p>
            {#if activityTotalPages > 1}
              <div class="flex items-center gap-1">
                <button
                  onclick={() => goToActivityPage(activityPage - 1)}
                  disabled={activityPage <= 1}
                  class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Previous activity page"
                >
                  Prev
                </button>
                {#each activityPageNumbers as pageNo}
                  <button
                    onclick={() => goToActivityPage(pageNo)}
                    class="rounded-lg border px-3 py-1.5 text-sm transition-colors {pageNo === activityPage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50'}"
                  >
                    {pageNo}
                  </button>
                {/each}
                <button
                  onclick={() => goToActivityPage(activityPage + 1)}
                  disabled={activityPage >= activityTotalPages}
                  class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Next activity page"
                >
                  Next
                </button>
              </div>
            {/if}
          </div>
        </div>
      {/if}

      {#if panel === "tasks"}
        <div class="p-5">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-neutral-900">Assigned Tasks</h3>
            <select class="rounded-lg border border-neutral-300 px-3 py-2 text-sm" bind:value={taskStatus} onchange={resetTasksPageAndFetch}>
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="breached">Breached</option>
              <option value="escalated">Escalated</option>
            </select>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[860px]">
              <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-3 py-2">Lead</th>
                  <th class="px-3 py-2">Rule</th>
                  <th class="px-3 py-2">Assignee</th>
                  <th class="px-3 py-2">Due</th>
                  <th class="px-3 py-2">Status</th>
                  <th class="px-3 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if workspaceError}
                  <tr>
                    <td colspan="6" class="px-3 py-6">
                      <DataStateBanner
                        title="Couldn't load tasks"
                        message={workspaceError}
                        onretry={loadAll}
                      />
                    </td>
                  </tr>
                {:else if tasks.length === 0}
                  <tr><td colspan="6" class="px-3 py-10 text-center text-sm text-neutral-500">No tasks found.</td></tr>
                {:else}
                  {#each tasks as task}
                    <tr class="text-sm text-neutral-700">
                      <td class="px-3 py-3 font-medium text-neutral-900">{task.lead_name}</td>
                      <td class="px-3 py-3">{task.rule_name}</td>
                      <td class="px-3 py-3">{task.assigned_to_name ?? "\u2014"}</td>
                      <td class="px-3 py-3">{fmtDateTime(task.due_at)}</td>
                      <td class="px-3 py-3">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {statusBadge(task.status)}">{task.status_display}</span>
                      </td>
                      <td class="px-3 py-3 text-right">
                        {#if task.status === "pending" || task.status === "in_progress" || task.status === "breached"}
                          <div class="inline-flex items-center gap-2">
                            <button onclick={() => completeTask(task.id)} class="text-xs font-medium text-emerald-700 hover:underline">Complete</button>
                            <button onclick={() => escalateTask(task.id)} class="text-xs font-medium text-rose-700 hover:underline">Escalate</button>
                          </div>
                        {:else}
                          <span class="text-xs text-neutral-400">&mdash;</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-3">
            <p class="text-sm text-neutral-500">
              Showing {taskCount === 0 ? 0 : (taskPage - 1) * taskPageSize + 1}&ndash;{Math.min(taskPage * taskPageSize, taskCount)} of {taskCount}
            </p>
            {#if taskTotalPages > 1}
              <div class="flex items-center gap-1">
                <button
                  onclick={() => goToTaskPage(taskPage - 1)}
                  disabled={taskPage <= 1}
                  class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Previous task page"
                >
                  Prev
                </button>
                {#each taskPageNumbers as pageNo}
                  <button
                    onclick={() => goToTaskPage(pageNo)}
                    class="rounded-lg border px-3 py-1.5 text-sm transition-colors {pageNo === taskPage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50'}"
                  >
                    {pageNo}
                  </button>
                {/each}
                <button
                  onclick={() => goToTaskPage(taskPage + 1)}
                  disabled={taskPage >= taskTotalPages}
                  class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Next task page"
                >
                  Next
                </button>
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

{#if showActivityForm}
  <button
    class="fixed inset-0 z-998 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeActivityDrawer}
    tabindex="-1"
    aria-label="Close activity drawer"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-999 w-full max-w-2xl bg-white shadow-2xl slide-over-enter flex flex-col">
    <div class="flex items-start justify-between gap-4 border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Log Sales Activity</h2>
        <p class="mt-1 text-sm text-neutral-500">Capture calls, emails, meetings, and site visits with outcomes.</p>
      </div>
      <button
        onclick={closeActivityDrawer}
        class="rounded-lg border border-neutral-200 p-1.5 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900"
        aria-label="Close activity drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <form id="activity-drawer-form" onsubmit={submitActivity} class="flex-1 overflow-y-auto px-6 py-5">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Lead</span>
          <select bind:value={activityForm.lead} class="w-full rounded-lg border border-neutral-300 px-3 py-2" required>
            <option value="" disabled>Select lead</option>
            {#each leads as lead}
              <option value={lead.id}>{lead.full_name}</option>
            {/each}
          </select>
          {#if activityErrors.lead}<p class="mt-1 text-xs text-rose-600">{activityErrors.lead[0]}</p>{/if}
        </label>
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Activity Type</span>
          <select bind:value={activityForm.activity_type} class="w-full rounded-lg border border-neutral-300 px-3 py-2">
            {#each activityTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm md:col-span-2">
          <span class="mb-1 block text-neutral-600">Subject</span>
          <input bind:value={activityForm.subject} class="w-full rounded-lg border border-neutral-300 px-3 py-2" placeholder="Enter subject" required />
          {#if activityErrors.subject}<p class="mt-1 text-xs text-rose-600">{activityErrors.subject[0]}</p>{/if}
        </label>
        <label class="text-sm md:col-span-2">
          <span class="mb-1 block text-neutral-600">Description</span>
          <textarea bind:value={activityForm.description} class="h-28 w-full rounded-lg border border-neutral-300 px-3 py-2" placeholder="Notes, outcomes, and action points"></textarea>
        </label>
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Scheduled At (Optional)</span>
          <input type="datetime-local" bind:value={activityForm.scheduled_at} class="w-full rounded-lg border border-neutral-300 px-3 py-2" />
          {#if activityErrors.scheduled_at}<p class="mt-1 text-xs text-rose-600">{activityErrors.scheduled_at[0]}</p>{/if}
        </label>
      </div>
    </form>

    <div class="flex items-center justify-end gap-2 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillActivity} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeActivityDrawer} class="rounded-lg border border-neutral-300 px-3 py-2 text-sm">
        Cancel
      </button>
      <button
        type="submit"
        form="activity-drawer-form"
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        disabled={savingActivity}
      >
        {savingActivity ? "Saving..." : "Save Activity"}
      </button>
    </div>
  </aside>
{/if}

{#if showTaskForm}
  <button
    class="fixed inset-0 z-998 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeTaskDrawer}
    tabindex="-1"
    aria-label="Close task drawer"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-999 w-full max-w-2xl bg-white shadow-2xl slide-over-enter flex flex-col">
    <div class="flex items-start justify-between gap-4 border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Assign Follow-Up Task</h2>
        <p class="mt-1 text-sm text-neutral-500">Assign responsibility, due date, and notes for follow-up execution.</p>
      </div>
      <button
        onclick={closeTaskDrawer}
        class="rounded-lg border border-neutral-200 p-1.5 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900"
        aria-label="Close task drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <form id="task-drawer-form" onsubmit={submitTask} class="flex-1 overflow-y-auto px-6 py-5">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Lead</span>
          <select bind:value={taskForm.lead} class="w-full rounded-lg border border-neutral-300 px-3 py-2" required>
            <option value="" disabled>Select lead</option>
            {#each leads as lead}
              <option value={lead.id}>{lead.full_name}</option>
            {/each}
          </select>
          {#if taskErrors.lead}<p class="mt-1 text-xs text-rose-600">{taskErrors.lead[0]}</p>{/if}
        </label>
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Due At</span>
          <input type="datetime-local" bind:value={taskForm.due_at} class="w-full rounded-lg border border-neutral-300 px-3 py-2" required />
          {#if taskErrors.due_at}<p class="mt-1 text-xs text-rose-600">{taskErrors.due_at[0]}</p>{/if}
        </label>
        <label class="text-sm">
          <span class="mb-1 block text-neutral-600">Assign To (Optional)</span>
          <select bind:value={taskForm.assigned_to} class="w-full rounded-lg border border-neutral-300 px-3 py-2">
            <option value="">Lead Owner (Default)</option>
            {#each users as user}
              <option value={user.id}>{user.full_name || user.email}</option>
            {/each}
          </select>
          {#if taskErrors.assigned_to}<p class="mt-1 text-xs text-rose-600">{taskErrors.assigned_to[0]}</p>{/if}
        </label>
        <label class="text-sm md:col-span-2">
          <span class="mb-1 block text-neutral-600">Notes</span>
          <textarea bind:value={taskForm.notes} class="h-24 w-full rounded-lg border border-neutral-300 px-3 py-2" placeholder="Task context and expected outcome"></textarea>
        </label>
      </div>
    </form>

    <div class="flex items-center justify-end gap-2 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillTask} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeTaskDrawer} class="rounded-lg border border-neutral-300 px-3 py-2 text-sm">
        Cancel
      </button>
      <button
        type="submit"
        form="task-drawer-form"
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        disabled={savingTask}
      >
        {savingTask ? "Assigning..." : "Assign Task"}
      </button>
    </div>
  </aside>
{/if}

<svelte:window
  onkeydown={(event) => {
    if (event.key !== "Escape") return;
    if (showTaskForm) {
      closeTaskDrawer();
      return;
    }
    if (showActivityForm) closeActivityDrawer();
  }}
/>

<style>
  .slide-over-enter {
    animation: slide-in-right 0.25s ease-out;
  }

  @keyframes slide-in-right {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
</style>
