<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    SupportDeskConfigurationChannelSettings,
    SupportDeskConfigurationOverview,
  } from "$lib/types";

  type ChannelKey = keyof SupportDeskConfigurationChannelSettings;

  let loading = $state(true);
  let errorMessage = $state("");
  let actionKey = $state("");

  let overview = $state<SupportDeskConfigurationOverview | null>(null);
  let channelDraft = $state<SupportDeskConfigurationChannelSettings>({
    email_enabled: true,
    in_app_enabled: true,
    sms_enabled: false,
    push_enabled: false,
  });

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function channelLabel(channel: string): string {
    if (channel === "in_app") return "In-app";
    if (channel === "sms") return "SMS";
    if (channel === "push") return "Push";
    return "Email";
  }

  function setChannelDraft(channel: ChannelKey, enabled: boolean) {
    channelDraft = { ...channelDraft, [channel]: enabled };
  }

  async function loadOverview() {
    loading = true;
    errorMessage = "";
    try {
      const data = await api.get<SupportDeskConfigurationOverview>("/support-desk/configuration/overview/");
      overview = data;
      channelDraft = { ...data.channel_settings };
    } catch (error) {
      overview = null;
      errorMessage = parseError(error, "Could not load support desk configuration.");
    } finally {
      loading = false;
    }
  }

  async function toggleSlaPolicy(policyId: number) {
    actionKey = `sla-${policyId}`;
    try {
      await api.post(`/support-desk/sla-escalations/policies/${policyId}/toggle-active/`, {});
      toast.success("SLA policy updated", "Policy activation state was changed.");
      await loadOverview();
    } catch (error) {
      toast.error("Update failed", parseError(error, "Could not update SLA policy state."));
    } finally {
      actionKey = "";
    }
  }

  async function toggleAutomationRule(ruleId: number) {
    actionKey = `rule-${ruleId}`;
    try {
      await api.post(`/support-desk/automation/rules/${ruleId}/toggle-active/`, {});
      toast.success("Automation rule updated", "Rule activation state was changed.");
      await loadOverview();
    } catch (error) {
      toast.error("Update failed", parseError(error, "Could not update automation rule state."));
    } finally {
      actionKey = "";
    }
  }

  async function toggleEmailTemplate(templateId: number, isActive: boolean) {
    actionKey = `template-${templateId}`;
    try {
      await api.patch(`/settings/notifications/templates/${templateId}/`, {
        is_active: !isActive,
      });
      toast.success("Template updated", "Email template activation state was changed.");
      await loadOverview();
    } catch (error) {
      toast.error("Update failed", parseError(error, "Could not update email template state."));
    } finally {
      actionKey = "";
    }
  }

  async function saveChannelSettings() {
    actionKey = "channel-settings";
    try {
      const updated = await api.patch<SupportDeskConfigurationChannelSettings>(
        "/settings/notifications/channels/",
        channelDraft,
      );
      channelDraft = updated;
      if (overview) {
        overview = {
          ...overview,
          channel_settings: updated,
        };
      }
      toast.success("Saved", "Notification channel settings were updated.");
      await loadOverview();
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save notification channel settings."));
    } finally {
      actionKey = "";
    }
  }

  onMount(() => {
    void loadOverview();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
  </div>
{:else if errorMessage}
  <div class="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-800">
    <h1 class="text-lg font-semibold">Configuration unavailable</h1>
    <p class="mt-2 text-sm">{errorMessage}</p>
    <button
      type="button"
      onclick={() => loadOverview()}
      class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else if overview}
  <div class="space-y-8">
    <section class="space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="max-w-3xl">
          <h1 class="text-2xl font-bold text-neutral-800">Administrative Setup</h1>
          <p class="mt-1 text-sm text-neutral-500">
            Central configuration for support taxonomies, teams, agent roles, SLA and automation controls, request types, templates, and notification rules.
          </p>
        </div>
      </div>
    </section>

    <section class="grid gap-4 md:grid-cols-3">
      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-neutral-800">Ticket Categories</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          {#each overview.ticket_categories as row}
            <span class="rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs text-neutral-700">{row.label} ({row.count})</span>
          {/each}
        </div>
      </article>

      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-neutral-800">Priority Levels</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          {#each overview.priority_levels as row}
            <span class="rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs text-neutral-700">{row.label} ({row.count})</span>
          {/each}
        </div>
      </article>

      <article class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-neutral-800">Ticket Statuses</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          {#each overview.ticket_statuses as row}
            <span class="rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs text-neutral-700">{row.label} ({row.count})</span>
          {/each}
        </div>
      </article>
    </section>

    <section class="grid gap-6 xl:grid-cols-2">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Support Teams</h2>
        <div class="mt-4 space-y-3">
          {#if overview.support_teams.length === 0}
            <p class="text-sm text-neutral-500">No support teams configured.</p>
          {:else}
            {#each overview.support_teams as team}
              <div class="flex items-center justify-between rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                <div>
                  <p class="text-sm font-semibold text-neutral-800">{team.name}</p>
                  <p class="text-xs text-neutral-500">Head: {team.head_name || "Not assigned"}</p>
                </div>
                <span class="rounded-lg px-2.5 py-1 text-xs font-medium {team.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-600'}">
                  {team.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            {/each}
          {/if}
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Agent Roles</h2>
        <div class="mt-4 space-y-3">
          {#if overview.agent_roles.length === 0}
            <p class="text-sm text-neutral-500">No roles available for this organization.</p>
          {:else}
            {#each overview.agent_roles as role}
              <div class="flex items-center justify-between rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                <div>
                  <p class="text-sm font-semibold text-neutral-800">{role.name}</p>
                  <p class="text-xs text-neutral-500">Slug: {role.slug}</p>
                </div>
                <span class="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                  {role.user_count} users
                </span>
              </div>
            {/each}
          {/if}
        </div>
      </article>
    </section>

    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-neutral-950">Request Types</h2>
      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {#each overview.request_types as requestType}
          <article class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <div class="flex items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-neutral-800">{requestType.label}</h3>
              <span class="rounded-md px-2 py-0.5 text-[11px] font-medium {requestType.approval_required ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}">
                {requestType.approval_required ? "Approval" : "No approval"}
              </span>
            </div>
            <p class="mt-2 text-xs leading-5 text-neutral-600">{requestType.description}</p>
            <p class="mt-2 text-xs font-medium text-neutral-700">SLA Target: {requestType.sla_target_hours}h</p>
          </article>
        {/each}
      </div>
    </section>

    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-lg font-semibold text-neutral-950">SLA Policies</h2>
      </div>
      <div class="mt-4 overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500">
            <tr>
              <th class="px-4 py-3">Policy</th>
              <th class="px-4 py-3">Scope</th>
              <th class="px-4 py-3">Response</th>
              <th class="px-4 py-3">Resolution</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each overview.sla_policies as policy}
              <tr>
                <td class="px-4 py-3 font-medium text-neutral-800">{policy.name}</td>
                <td class="px-4 py-3 text-neutral-700">{policy.category_display} / {policy.priority_display}</td>
                <td class="px-4 py-3 text-neutral-700">{policy.response_target_display}</td>
                <td class="px-4 py-3 text-neutral-700">{policy.resolution_target_display}</td>
                <td class="px-4 py-3">
                  <span class="rounded-lg px-2.5 py-1 text-xs font-medium {policy.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-600'}">
                    {policy.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleSlaPolicy(policy.id)}
                    disabled={actionKey === `sla-${policy.id}`}
                    class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {actionKey === `sla-${policy.id}` ? "Saving..." : policy.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-neutral-950">Automation Rules</h2>
      <div class="mt-4 overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500">
            <tr>
              <th class="px-4 py-3">Rule</th>
              <th class="px-4 py-3">Trigger</th>
              <th class="px-4 py-3">Priority</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each overview.automation_rules as rule}
              <tr>
                <td class="px-4 py-3 font-medium text-neutral-800">{rule.name}</td>
                <td class="px-4 py-3 text-neutral-700">{rule.trigger_type_display}</td>
                <td class="px-4 py-3 text-neutral-700">{rule.priority}</td>
                <td class="px-4 py-3">
                  <span class="rounded-lg px-2.5 py-1 text-xs font-medium {rule.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-600'}">
                    {rule.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleAutomationRule(rule.id)}
                    disabled={actionKey === `rule-${rule.id}`}
                    class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {actionKey === `rule-${rule.id}` ? "Saving..." : rule.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(300px,0.9fr)]">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Email Templates</h2>
        {#if overview.email_templates.length === 0}
          <p class="mt-4 text-sm text-neutral-500">No support email templates configured. Create templates from settings to standardize support communication.</p>
        {:else}
          <div class="mt-4 overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500">
                <tr>
                  <th class="px-4 py-3">Template</th>
                  <th class="px-4 py-3">Event Key</th>
                  <th class="px-4 py-3">Severity</th>
                  <th class="px-4 py-3">Status</th>
                  <th class="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 bg-white">
                {#each overview.email_templates as template}
                  <tr>
                    <td class="px-4 py-3 font-medium text-neutral-800">{template.name}</td>
                    <td class="px-4 py-3 text-neutral-700">{template.event_key}</td>
                    <td class="px-4 py-3 text-neutral-700">{template.severity_tier}</td>
                    <td class="px-4 py-3">
                      <span class="rounded-lg px-2.5 py-1 text-xs font-medium {template.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-600'}">
                        {template.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-right">
                      <button
                        type="button"
                        onclick={() => toggleEmailTemplate(template.id, template.is_active)}
                        disabled={actionKey === `template-${template.id}`}
                        class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {actionKey === `template-${template.id}` ? "Saving..." : template.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </article>

      <aside class="space-y-6">
        <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 class="text-lg font-semibold text-neutral-950">Notification Channels</h2>
          <p class="mt-1 text-sm text-neutral-500">Global dispatch channels used by support workflow notifications.</p>

          <div class="mt-5 space-y-3">
            <label class="flex items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <span class="text-sm font-medium text-neutral-800">Email</span>
              <input type="checkbox" checked={channelDraft.email_enabled} onchange={(event) => setChannelDraft("email_enabled", (event.currentTarget as HTMLInputElement).checked)} class="rounded border-neutral-300" />
            </label>
            <label class="flex items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <span class="text-sm font-medium text-neutral-800">In-app</span>
              <input type="checkbox" checked={channelDraft.in_app_enabled} onchange={(event) => setChannelDraft("in_app_enabled", (event.currentTarget as HTMLInputElement).checked)} class="rounded border-neutral-300" />
            </label>
            <label class="flex items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <span class="text-sm font-medium text-neutral-800">SMS</span>
              <input type="checkbox" checked={channelDraft.sms_enabled} onchange={(event) => setChannelDraft("sms_enabled", (event.currentTarget as HTMLInputElement).checked)} class="rounded border-neutral-300" />
            </label>
            <label class="flex items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <span class="text-sm font-medium text-neutral-800">Push</span>
              <input type="checkbox" checked={channelDraft.push_enabled} onchange={(event) => setChannelDraft("push_enabled", (event.currentTarget as HTMLInputElement).checked)} class="rounded border-neutral-300" />
            </label>
          </div>

          <button
            type="button"
            onclick={saveChannelSettings}
            disabled={actionKey === "channel-settings"}
            class="mt-5 w-full rounded-xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === "channel-settings" ? "Saving..." : "Save Channel Settings"}
          </button>
        </section>

        <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 class="text-lg font-semibold text-neutral-950">Notification Rules</h2>
          <div class="mt-4 space-y-3">
            {#if overview.notification_rules.length === 0}
              <p class="text-sm text-neutral-500">No support notification rules available.</p>
            {:else}
              {#each overview.notification_rules as rule}
                <article class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <h3 class="text-sm font-semibold text-neutral-800">{rule.label}</h3>
                      <p class="mt-1 text-xs leading-5 text-neutral-600">{rule.description}</p>
                    </div>
                    <span class="rounded-lg px-2.5 py-1 text-[11px] font-medium {rule.is_enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-neutral-200 text-neutral-700'}">
                      {rule.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>

                  <div class="mt-3 flex flex-wrap gap-2">
                    {#if rule.active_channels.length > 0}
                      {#each rule.active_channels as channel}
                        <span class="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700">{channelLabel(channel)}</span>
                      {/each}
                    {:else}
                      <span class="rounded-md bg-neutral-200 px-2 py-0.5 text-[11px] font-medium text-neutral-600">No active channel</span>
                    {/if}
                  </div>

                  <p class="mt-2 text-[11px] text-neutral-500">
                    Templates: {rule.active_templates} active / {rule.total_templates} total
                  </p>
                </article>
              {/each}
            {/if}
          </div>
        </section>
      </aside>
    </section>
  </div>
{/if}
