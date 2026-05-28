<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    NotificationChannelSettings,
    NotificationWorkflowCatalogItem,
    NotificationWorkflowCatalogResponse,
    NotificationTemplateChannel,
    NotificationTemplateDetail,
    NotificationTemplateListItem,
    PaginatedResponse,
    SlaSeverityLevel,
    SlaSeverityTier,
  } from "$lib/types";

  type TierEdit = {
    response_time_hours: number;
    escalation_path_text: string;
    notification_channels: Record<NotificationTemplateChannel, boolean>;
    is_active: boolean;
  };

  type TemplateForm = {
    id: number | null;
    code: string;
    name: string;
    description: string;
    channel: NotificationTemplateChannel;
    event_key: string;
    severity_tier: SlaSeverityLevel;
    subject: string;
    body_text: string;
    body_html: string;
    variables_text: string;
    is_active: boolean;
  };

  const CHANNEL_OPTIONS: Array<{ value: NotificationTemplateChannel; label: string }> = [
    { value: "email", label: "Email" },
    { value: "in_app", label: "In-App" },
    { value: "sms", label: "SMS" },
    { value: "push", label: "Push" },
  ];

  const SEVERITY_OPTIONS: Array<{ value: SlaSeverityLevel; label: string }> = [
    { value: "info", label: "Info" },
    { value: "review", label: "Review" },
    { value: "action_required", label: "Action Required" },
    { value: "escalation", label: "Escalation" },
  ];

  const SEVERITY_BADGE: Record<SlaSeverityLevel, string> = {
    info: "bg-sky-50 text-sky-700",
    review: "bg-amber-50 text-amber-700",
    action_required: "bg-orange-50 text-orange-700",
    escalation: "bg-red-50 text-red-700",
  };

  let loading = $state(true);
  let channelsSaving = $state(false);
  let templateSaving = $state(false);
  let deletingTemplateId = $state<number | null>(null);

  let channelSettings = $state<NotificationChannelSettings | null>(null);
  let tiers = $state<SlaSeverityTier[]>([]);
  let tierEdits = $state<Record<number, TierEdit>>({});

  let templates = $state<NotificationTemplateListItem[]>([]);
  let templateSearch = $state("");
  let templateChannelFilter = $state<"" | NotificationTemplateChannel>("");
  let workflowEvents = $state<NotificationWorkflowCatalogItem[]>([]);
  let workflowModuleFilter = $state("");

  let showEditor = $state(false);
  let templateForm = $state<TemplateForm>(emptyTemplateForm());
  let editorDialog = $state<HTMLDivElement | null>(null);

  const workflowModules = $derived.by(() => {
    return Array.from(new Set(workflowEvents.map((event) => event.module))).sort();
  });

  const filteredWorkflowEvents = $derived.by(() => {
    if (!workflowModuleFilter) return workflowEvents;
    return workflowEvents.filter((event) => event.module === workflowModuleFilter);
  });

  const selectedWorkflowEvent = $derived.by(() => {
    const key = templateForm.event_key.trim().toLowerCase();
    return workflowEvents.find((event) => event.key === key) ?? null;
  });

  function emptyTemplateForm(): TemplateForm {
    return {
      id: null,
      code: "",
      name: "",
      description: "",
      channel: "email",
      event_key: "",
      severity_tier: "review",
      subject: "",
      body_text: "",
      body_html: "",
      variables_text: "",
      is_active: true,
    };
  }

  function channelMap(list: NotificationTemplateChannel[]): Record<NotificationTemplateChannel, boolean> {
    return {
      email: list.includes("email"),
      in_app: list.includes("in_app"),
      sms: list.includes("sms"),
      push: list.includes("push"),
    };
  }

  function channelList(map: Record<NotificationTemplateChannel, boolean>): NotificationTemplateChannel[] {
    return CHANNEL_OPTIONS.filter((c) => map[c.value]).map((c) => c.value);
  }

  function buildTierEditMap(items: SlaSeverityTier[]): Record<number, TierEdit> {
    const map: Record<number, TierEdit> = {};
    for (const tier of items) {
      map[tier.id] = {
        response_time_hours: tier.response_time_hours,
        escalation_path_text: tier.escalation_path.join(", "),
        notification_channels: channelMap(tier.notification_channels),
        is_active: tier.is_active,
      };
    }
    return map;
  }

  async function loadChannels() {
    channelSettings = await api.get<NotificationChannelSettings>("/settings/notifications/channels/");
  }

  async function loadTiers() {
    const res = await api.get<PaginatedResponse<SlaSeverityTier>>("/settings/notifications/sla-tiers/", {
      ordering: "sort_order",
      page_size: "20",
    });
    tiers = res.results;
    tierEdits = buildTierEditMap(res.results);
  }

  async function loadTemplates() {
    const params: Record<string, string> = {
      ordering: "-updated_at",
      page_size: "200",
    };
    if (templateSearch.trim()) params.search = templateSearch.trim();
    if (templateChannelFilter) params.channel = templateChannelFilter;

    const res = await api.get<PaginatedResponse<NotificationTemplateListItem>>(
      "/settings/notifications/templates/",
      params,
    );
    templates = res.results;
  }

  async function loadWorkflowCatalog() {
    const res = await api.get<NotificationWorkflowCatalogResponse>(
      "/settings/notifications/workflow-catalog/",
    );
    workflowEvents = res.events;
  }

  async function loadAll() {
    loading = true;
    try {
      await Promise.all([loadChannels(), loadTiers(), loadTemplates(), loadWorkflowCatalog()]);
    } catch {
      toast.error("Load failed", "Could not load notification settings.");
    } finally {
      loading = false;
    }
  }

  async function saveChannels() {
    if (!channelSettings) return;
    channelsSaving = true;
    try {
      const { id, created_at, updated_at, ...payload } = channelSettings;
      channelSettings = await api.patch<NotificationChannelSettings>(
        "/settings/notifications/channels/",
        payload,
      );
      toast.success("Saved", "Notification channels updated.");
    } catch {
      toast.error("Save failed", "Could not update notification channels.");
    } finally {
      channelsSaving = false;
    }
  }

  async function saveTier(tierId: number) {
    const edit = tierEdits[tierId];
    if (!edit) return;
    try {
      const escalationPath = edit.escalation_path_text
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      await api.patch(`/settings/notifications/sla-tiers/${tierId}/`, {
        response_time_hours: Number(edit.response_time_hours || 0),
        escalation_path: escalationPath,
        notification_channels: channelList(edit.notification_channels),
        is_active: edit.is_active,
      });
      toast.success("Saved", "SLA tier updated.");
      await loadTiers();
    } catch (err) {
      if (err instanceof ApiError) {
        const first = Object.values(err.fieldErrors).flat()[0] || "Could not update SLA tier.";
        toast.error("Save failed", first);
      } else {
        toast.error("Save failed", "Could not update SLA tier.");
      }
    }
  }

  async function openTemplateEditor(id: number | null) {
    if (id === null) {
      templateForm = emptyTemplateForm();
      showEditor = true;
      requestAnimationFrame(() => editorDialog?.focus());
      return;
    }

    try {
      const detail = await api.get<NotificationTemplateDetail>(`/settings/notifications/templates/${id}/`);
      templateForm = {
        id: detail.id,
        code: detail.code,
        name: detail.name,
        description: detail.description,
        channel: detail.channel,
        event_key: detail.event_key,
        severity_tier: detail.severity_tier,
        subject: detail.subject,
        body_text: detail.body_text,
        body_html: detail.body_html,
        variables_text: detail.variables.join(", "),
        is_active: detail.is_active,
      };
      showEditor = true;
      requestAnimationFrame(() => editorDialog?.focus());
    } catch {
      toast.error("Load failed", "Could not load template details.");
    }
  }

  function channelLabel(value: NotificationTemplateChannel): string {
    return CHANNEL_OPTIONS.find((channel) => channel.value === value)?.label ?? value;
  }

  function moduleLabel(value: string): string {
    if (!value) return "General";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function eventLabel(eventKey: string): string {
    return workflowEvents.find((item) => item.key === eventKey)?.label ?? eventKey;
  }

  function openTemplateEditorForWorkflow(
    event: NotificationWorkflowCatalogItem,
    channel: NotificationTemplateChannel,
  ) {
    templateForm = {
      ...emptyTemplateForm(),
      name: `${event.label} (${channelLabel(channel)})`,
      channel,
      event_key: event.key,
      severity_tier: event.default_severity_tier || "review",
      variables_text: event.variables.join(", "),
    };
    showEditor = true;
    requestAnimationFrame(() => editorDialog?.focus());
  }

  function closeTemplateEditor() {
    showEditor = false;
    templateForm = emptyTemplateForm();
  }

  function parseVariables(raw: string): string[] {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function saveTemplate() {
    if (!templateForm.name.trim() || !templateForm.event_key.trim() || !templateForm.body_text.trim()) {
      toast.error("Validation", "Name, event key, and body text are required.");
      return;
    }

    const payload = {
      code: templateForm.code.trim(),
      name: templateForm.name.trim(),
      description: templateForm.description.trim(),
      channel: templateForm.channel,
      event_key: templateForm.event_key.trim(),
      severity_tier: templateForm.severity_tier,
      subject: templateForm.subject.trim(),
      body_text: templateForm.body_text,
      body_html: templateForm.body_html,
      variables: parseVariables(templateForm.variables_text),
      is_active: templateForm.is_active,
    };

    templateSaving = true;
    try {
      if (templateForm.id) {
        await api.patch(`/settings/notifications/templates/${templateForm.id}/`, payload);
      } else {
        await api.post("/settings/notifications/templates/", payload);
      }
      toast.success("Saved", "Template saved successfully.");
      closeTemplateEditor();
      await Promise.all([loadTemplates(), loadWorkflowCatalog()]);
    } catch (err) {
      if (err instanceof ApiError) {
        const first = Object.values(err.fieldErrors).flat()[0] || "Could not save template.";
        toast.error("Save failed", first);
      } else {
        toast.error("Save failed", "Could not save template.");
      }
    } finally {
      templateSaving = false;
    }
  }

  async function deleteTemplate(template: NotificationTemplateListItem) {
    if (template.is_system) {
      toast.error("Protected", "System templates cannot be deleted.");
      return;
    }
    if (!confirm(`Delete template \"${template.name}\"?`)) return;

    deletingTemplateId = template.id;
    try {
      await api.delete(`/settings/notifications/templates/${template.id}/`);
      toast.success("Deleted", "Template removed.");
      await Promise.all([loadTemplates(), loadWorkflowCatalog()]);
    } catch {
      toast.error("Delete failed", "Could not delete template.");
    } finally {
      deletingTemplateId = null;
    }
  }

  function tierLabel(level: SlaSeverityLevel): string {
    return SEVERITY_OPTIONS.find((opt) => opt.value === level)?.label ?? level;
  }

  $effect(() => {
    loadAll();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Workflow Notifications</h2>
      <p class="mt-1 text-sm text-neutral-500">
        Centralize workflow event templates, delivery channels, and SLA severity behavior.
      </p>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold text-neutral-800">Notification Channels</h3>
          <p class="text-xs text-neutral-500 mt-1">Global delivery channel toggles.</p>
        </div>
        <button
          onclick={saveChannels}
          disabled={channelsSaving}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {channelsSaving ? "Saving..." : "Save Channels"}
        </button>
      </div>

      {#if channelSettings}
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <label class="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2.5 cursor-pointer">
            <input type="checkbox" bind:checked={channelSettings.email_enabled} class="rounded border-neutral-300" />
            <span class="text-sm text-neutral-700">Email</span>
          </label>
          <label class="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2.5 cursor-pointer">
            <input type="checkbox" bind:checked={channelSettings.in_app_enabled} class="rounded border-neutral-300" />
            <span class="text-sm text-neutral-700">In-App</span>
          </label>
          <label class="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2.5 cursor-pointer">
            <input type="checkbox" bind:checked={channelSettings.sms_enabled} class="rounded border-neutral-300" />
            <span class="text-sm text-neutral-700">SMS</span>
          </label>
          <label class="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2.5 cursor-pointer">
            <input type="checkbox" bind:checked={channelSettings.push_enabled} class="rounded border-neutral-300" />
            <span class="text-sm text-neutral-700">Push</span>
          </label>
        </div>
      {/if}
    </section>

    <!-- Category Controls -->
    {#if channelSettings}
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h3 class="text-sm font-semibold text-neutral-800">Notification Categories</h3>
            <p class="text-xs text-neutral-500 mt-1">Enable or disable entire notification categories for your organization.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {#each Object.entries(channelSettings.category_overrides || {}) as [key, config]}
            {@const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            {@const enabled = typeof config === "object" && config !== null ? (config as Record<string, unknown>).enabled !== false : true}
            <label class="flex items-center gap-3 rounded-lg border px-3 py-2.5 cursor-pointer transition-colors {enabled ? 'border-neutral-200 bg-white' : 'border-neutral-100 bg-neutral-50'}">
              <input
                type="checkbox"
                checked={enabled}
                onchange={() => {
                  const prev = channelSettings!.category_overrides || {};
                  const current = typeof prev[key] === "object" && prev[key] !== null ? { ...(prev[key] as { enabled: boolean; channels: string[] }) } : { enabled: true, channels: ["in_app", "email"] };
                  current.enabled = !enabled;
                  channelSettings!.category_overrides = { ...prev, [key]: current as { enabled: boolean; channels: string[] } };
                }}
                class="rounded border-neutral-300"
              />
              <span class="text-sm {enabled ? 'text-neutral-700' : 'text-neutral-400'}">{label}</span>
            </label>
          {/each}
        </div>
      </section>

      <!-- Muted Event Keys -->
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <div class="mb-4">
          <h3 class="text-sm font-semibold text-neutral-800">Muted Automation Events</h3>
          <p class="text-xs text-neutral-500 mt-1">Silence specific automation event notifications org-wide. These events will still execute but won't generate notifications.</p>
        </div>

        {#if (channelSettings.muted_event_keys || []).length > 0}
          <div class="flex flex-wrap gap-2 mb-3">
            {#each channelSettings.muted_event_keys as eventKey, i}
              <span class="inline-flex items-center gap-1.5 rounded-md bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-600">
                {eventKey}
                <button
                  type="button"
                  onclick={() => {
                    channelSettings!.muted_event_keys = (channelSettings!.muted_event_keys || []).filter((_: string, idx: number) => idx !== i);
                  }}
                  class="text-neutral-400 hover:text-red-500 transition-colors"
                  aria-label="Unmute {eventKey}"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            {/each}
          </div>
        {:else}
          <p class="text-xs text-neutral-400 mb-3">No events are currently muted. All automation notifications are active.</p>
        {/if}

        <div class="flex gap-2">
          <input
            type="text"
            placeholder="Enter event key to mute (e.g. project_cost_sync)"
            class="flex-1 rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            onkeydown={(e) => {
              if (e.key === "Enter") {
                const input = e.currentTarget as HTMLInputElement;
                const val = input.value.trim();
                const keys = channelSettings!.muted_event_keys || [];
                if (val && !keys.includes(val)) {
                  channelSettings!.muted_event_keys = [...keys, val];
                  input.value = "";
                }
              }
            }}
          />
          <button
            type="button"
            onclick={(e) => {
              const input = (e.currentTarget as HTMLElement).previousElementSibling as HTMLInputElement;
              const val = input?.value.trim();
              const keys = channelSettings!.muted_event_keys || [];
              if (val && !keys.includes(val)) {
                channelSettings!.muted_event_keys = [...keys, val];
                input.value = "";
              }
            }}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Add
          </button>
        </div>

        {#if workflowEvents.length > 0}
          <details class="mt-3">
            <summary class="text-xs text-neutral-500 cursor-pointer hover:text-neutral-700">Browse available event keys</summary>
            <div class="mt-2 max-h-48 overflow-y-auto rounded-lg border border-neutral-100 bg-neutral-50 p-3">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
                {#each workflowEvents as event}
                  {@const muted = (channelSettings?.muted_event_keys || []).includes(event.key)}
                  <button
                    type="button"
                    onclick={() => {
                      const keys = channelSettings!.muted_event_keys || [];
                      if (!keys.includes(event.key)) {
                        channelSettings!.muted_event_keys = [...keys, event.key];
                      }
                    }}
                    class="text-left text-xs px-2 py-1 rounded hover:bg-white transition-colors {muted ? 'text-neutral-300 line-through' : 'text-neutral-600'}"
                    disabled={muted}
                  >
                    <span class="font-mono">{event.key}</span>
                    <span class="text-neutral-400 ml-1">({event.module})</span>
                  </button>
                {/each}
              </div>
            </div>
          </details>
        {/if}
      </section>
    {/if}

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800">SLA Severity Tiers</h3>
      <p class="text-xs text-neutral-500 mt-1 mb-4">Each tier controls response time, escalation path, and channels.</p>

      <div class="space-y-4">
        {#each tiers as tier (tier.id)}
          {@const edit = tierEdits[tier.id]}
          <div class="rounded-lg border border-neutral-200 p-4">
            <div class="flex items-center justify-between mb-3">
              <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${SEVERITY_BADGE[tier.level]}`}>
                {tier.level_display}
              </span>
              <label class="flex items-center gap-2 text-xs text-neutral-600">
                <input type="checkbox" bind:checked={edit.is_active} class="rounded border-neutral-300" />
                Active
              </label>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div>
                <label for={`response-${tier.id}`} class="block text-xs font-medium text-neutral-600 mb-1">Response Time (hours)</label>
                <input
                  id={`response-${tier.id}`}
                  type="number"
                  min="1"
                  bind:value={edit.response_time_hours}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
                />
              </div>

              <div class="lg:col-span-2">
                <label for={`escalation-${tier.id}`} class="block text-xs font-medium text-neutral-600 mb-1">Escalation Path</label>
                <input
                  id={`escalation-${tier.id}`}
                  type="text"
                  bind:value={edit.escalation_path_text}
                  placeholder="manager, operations_head"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
                />
              </div>
            </div>

            <div class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
              {#each CHANNEL_OPTIONS as channel}
                <label class="flex items-center gap-2 rounded-lg border border-neutral-200 px-2.5 py-2 cursor-pointer">
                  <input type="checkbox" bind:checked={edit.notification_channels[channel.value]} class="rounded border-neutral-300" />
                  <span class="text-xs text-neutral-700">{channel.label}</span>
                </label>
              {/each}
            </div>

            <div class="mt-3 flex justify-end">
              <button
                onclick={() => saveTier(tier.id)}
                class="rounded-lg border border-neutral-200 px-3.5 py-2 text-xs font-semibold text-neutral-700 hover:bg-neutral-50"
              >
                Save {tierLabel(tier.level)}
              </button>
            </div>
          </div>
        {/each}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h3 class="text-sm font-semibold text-neutral-800">Workflow Template Coverage</h3>
          <p class="text-xs text-neutral-500 mt-1">
            Manage notification consistency by configuring templates per workflow event.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <label for="workflow-module-filter" class="text-xs font-medium text-neutral-600">Module</label>
          <select
            id="workflow-module-filter"
            bind:value={workflowModuleFilter}
            class="rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
          >
            <option value="">All modules</option>
            {#each workflowModules as module}
              <option value={module}>{moduleLabel(module)}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {#if filteredWorkflowEvents.length === 0}
          <div class="rounded-lg border border-dashed border-neutral-300 px-4 py-6 text-sm text-neutral-500">
            No workflow events match the selected filter.
          </div>
        {:else}
          {#each filteredWorkflowEvents as event (event.key)}
            <article class="rounded-lg border border-neutral-200 p-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold text-neutral-800">{event.label}</h4>
                  <p class="mt-1 text-xs text-neutral-500">{event.description}</p>
                  <p class="mt-1 text-[11px] uppercase tracking-wide text-neutral-400">{moduleLabel(event.module)}</p>
                </div>
                <span class="rounded-full border border-neutral-200 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
                  {event.active_template_count}/{event.template_count} active
                </span>
              </div>

              <div class="mt-3 flex flex-wrap gap-1.5">
                {#if event.active_channels.length === 0}
                  <span class="rounded bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700">No active channels</span>
                {:else}
                  {#each event.active_channels as channel}
                    <span class="rounded bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-700">
                      Active {channelLabel(channel)}
                    </span>
                  {/each}
                {/if}
              </div>

              <div class="mt-3 flex flex-wrap gap-2">
                <button
                  onclick={() => openTemplateEditorForWorkflow(event, "email")}
                  class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                >
                  Email Template
                </button>
                <button
                  onclick={() => openTemplateEditorForWorkflow(event, "in_app")}
                  class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                >
                  In-App Template
                </button>
              </div>
            </article>
          {/each}
        {/if}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold text-neutral-800">Template Builder & Editor Center</h3>
          <p class="text-xs text-neutral-500 mt-1">
            Build channel templates and map them to workflow event keys.
          </p>
        </div>
        <button
          onclick={() => openTemplateEditor(null)}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          New Template
        </button>
      </div>

      <div class="flex flex-wrap gap-2 mb-3">
        <input
          type="text"
          bind:value={templateSearch}
          placeholder="Search code/name/event"
          class="w-64 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
        />
        <select
          bind:value={templateChannelFilter}
          class="rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="">All channels</option>
          {#each CHANNEL_OPTIONS as channel}
            <option value={channel.value}>{channel.label}</option>
          {/each}
        </select>
        <button
          onclick={loadTemplates}
          class="rounded-lg border border-neutral-200 px-3.5 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          Apply
        </button>
      </div>

      <div class="overflow-x-auto rounded-lg border border-neutral-200">
        <table class="w-full min-w-[840px] text-sm">
          <thead>
            <tr class="bg-neutral-50 border-b border-neutral-200 text-left">
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Code</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Name</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Channel</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Event Key</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Tier</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</th>
              <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-neutral-500 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#if templates.length === 0}
              <tr>
                <td colspan="7" class="px-4 py-12 text-center text-sm text-neutral-500">No templates found.</td>
              </tr>
            {:else}
              {#each templates as template (template.id)}
                <tr class="border-b border-neutral-100">
                  <td class="px-4 py-3 font-mono text-xs text-neutral-700">{template.code}</td>
                  <td class="px-4 py-3 text-neutral-800 font-medium">{template.name}</td>
                  <td class="px-4 py-3 text-neutral-600">{template.channel_display}</td>
                  <td class="px-4 py-3 text-neutral-600">
                    <div class="font-medium text-neutral-700">{eventLabel(template.event_key)}</div>
                    <div class="font-mono text-xs text-neutral-500">{template.event_key}</div>
                  </td>
                  <td class="px-4 py-3">
                    <span class={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${SEVERITY_BADGE[template.severity_tier]}`}>
                      {template.severity_tier_display}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-neutral-600">{template.is_active ? "Active" : "Inactive"}</td>
                  <td class="px-4 py-3 text-right space-x-2">
                    <button
                      onclick={() => openTemplateEditor(template.id)}
                      class="rounded border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                    >
                      Edit
                    </button>
                    <button
                      onclick={() => deleteTemplate(template)}
                      disabled={deletingTemplateId === template.id || template.is_system}
                      class="rounded border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-40"
                    >
                      {deletingTemplateId === template.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </section>

    {#if showEditor}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-800/55 p-4"
        tabindex="-1"
        onclick={(e) => {
          if (e.currentTarget === e.target) closeTemplateEditor();
        }}
        onkeydown={(e) => {
          if (e.key === "Escape") closeTemplateEditor();
        }}
      >
        <div
          bind:this={editorDialog}
          tabindex="-1"
          role="dialog"
          aria-modal="true"
          aria-labelledby="template-editor-title"
          class="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl border border-neutral-200 bg-white p-6 shadow-xl outline-none"
        >
          <div class="flex items-center justify-between mb-4">
            <h4 id="template-editor-title" class="text-sm font-semibold text-neutral-800">
              {templateForm.id ? "Edit Template" : "New Template"}
            </h4>
            <button
              onclick={closeTemplateEditor}
              class="text-sm text-neutral-500 hover:text-neutral-800"
            >
              Close
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label for="tpl-code" class="block text-xs font-medium text-neutral-600 mb-1">Code</label>
              <input id="tpl-code" type="text" bind:value={templateForm.code} placeholder="auto if blank" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label for="tpl-name" class="block text-xs font-medium text-neutral-600 mb-1">Name</label>
              <input id="tpl-name" type="text" bind:value={templateForm.name} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label for="tpl-channel" class="block text-xs font-medium text-neutral-600 mb-1">Channel</label>
              <select id="tpl-channel" bind:value={templateForm.channel} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm">
                {#each CHANNEL_OPTIONS as channel}
                  <option value={channel.value}>{channel.label}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="tpl-tier" class="block text-xs font-medium text-neutral-600 mb-1">SLA Tier</label>
              <select id="tpl-tier" bind:value={templateForm.severity_tier} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm">
                {#each SEVERITY_OPTIONS as tier}
                  <option value={tier.value}>{tier.label}</option>
                {/each}
              </select>
            </div>
            <div class="md:col-span-2">
              <label for="tpl-event" class="block text-xs font-medium text-neutral-600 mb-1">Event Key</label>
              <input
                id="tpl-event"
                type="text"
                bind:value={templateForm.event_key}
                list="workflow-event-keys"
                placeholder="support_ticket_assigned"
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
              />
              <datalist id="workflow-event-keys">
                {#each workflowEvents as event}
                  <option value={event.key}>{event.label}</option>
                {/each}
              </datalist>
              {#if selectedWorkflowEvent}
                <p class="mt-1 text-xs text-neutral-500">
                  {selectedWorkflowEvent.label} ({moduleLabel(selectedWorkflowEvent.module)})
                </p>
              {:else}
                <p class="mt-1 text-xs text-amber-600">
                  This key is not in the workflow catalog. It will be treated as a custom event.
                </p>
              {/if}
            </div>
            <div class="md:col-span-2">
              <label for="tpl-description" class="block text-xs font-medium text-neutral-600 mb-1">Description</label>
              <textarea id="tpl-description" rows="2" bind:value={templateForm.description} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"></textarea>
            </div>
            <div class="md:col-span-2">
              <label for="tpl-subject" class="block text-xs font-medium text-neutral-600 mb-1">Subject (required for Email)</label>
              <input id="tpl-subject" type="text" bind:value={templateForm.subject} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" />
            </div>
            <div class="md:col-span-2">
              <label for="tpl-text" class="block text-xs font-medium text-neutral-600 mb-1">Body Text</label>
              <textarea id="tpl-text" rows="5" bind:value={templateForm.body_text} placeholder={"Use placeholders like {{project_name}}"} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono"></textarea>
            </div>
            <div class="md:col-span-2">
              <label for="tpl-html" class="block text-xs font-medium text-neutral-600 mb-1">Body HTML (optional)</label>
              <textarea id="tpl-html" rows="5" bind:value={templateForm.body_html} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono"></textarea>
            </div>
            <div class="md:col-span-2">
              <label for="tpl-vars" class="block text-xs font-medium text-neutral-600 mb-1">Variables (comma-separated)</label>
              <input id="tpl-vars" type="text" bind:value={templateForm.variables_text} placeholder="project_name, due_date, owner_name" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" />
            </div>
            <div class="md:col-span-2">
              <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
                <input type="checkbox" bind:checked={templateForm.is_active} class="rounded border-neutral-300" />
                Template is active
              </label>
            </div>
          </div>

          <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <p class="text-xs font-semibold text-neutral-600 mb-2">Variable Tokens</p>
            <div class="flex flex-wrap gap-2">
              {#each parseVariables(templateForm.variables_text) as variable}
                <span class="inline-flex rounded bg-white border border-neutral-200 px-2 py-1 text-xs font-mono text-neutral-700">{`{{${variable}}}`}</span>
              {/each}
              {#if parseVariables(templateForm.variables_text).length === 0}
                <span class="text-xs text-neutral-500">No variables defined.</span>
              {/if}
            </div>
            {#if selectedWorkflowEvent && selectedWorkflowEvent.variables.length > 0}
              <div class="mt-3 border-t border-neutral-200 pt-3">
                <p class="mb-2 text-xs font-semibold text-neutral-600">Catalog Variables</p>
                <div class="flex flex-wrap gap-2">
                  {#each selectedWorkflowEvent.variables as variable}
                    <span class="inline-flex rounded border border-neutral-200 bg-white px-2 py-1 text-xs font-mono text-neutral-600">{`{{${variable}}}`}</span>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <div class="mt-4 flex items-center justify-end gap-2">
            <button
              onclick={closeTemplateEditor}
              class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
            >
              Cancel
            </button>
            <button
              onclick={saveTemplate}
              disabled={templateSaving}
              class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
            >
              {templateSaving ? "Saving..." : "Save Template"}
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}
