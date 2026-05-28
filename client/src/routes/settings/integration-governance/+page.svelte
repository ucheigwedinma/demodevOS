<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { IntegrationGovernanceSettings } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<IntegrationGovernanceSettings>>({});
  let newEmail = $state("");

  async function loadSettings() {
    try {
      const data = await api.get<IntegrationGovernanceSettings>("/settings/integration-governance/");
      form = data;
    } catch {
      toast.error("Load failed", "Could not load integration governance settings.");
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      const {
        id,
        created_at,
        updated_at,
        default_sync_frequency_display,
        conflict_resolution_strategy_display,
        primary_source_of_truth_display,
        error_severity_threshold_display,
        sla_max_response_time_display,
        sla_max_sync_latency_display,
        version_compatibility_log,
        ...payload
      } = form as IntegrationGovernanceSettings;
      const data = await api.patch<IntegrationGovernanceSettings>("/settings/integration-governance/", payload);
      form = data;
      toast.success("Saved", "Integration governance settings updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  function addEmail() {
    const email = newEmail.trim();
    if (!email) return;
    if (!form.error_email_recipients) form.error_email_recipients = [];
    if (!form.error_email_recipients.includes(email)) {
      form.error_email_recipients = [...form.error_email_recipients, email];
    }
    newEmail = "";
  }

  function removeEmail(email: string) {
    if (!form.error_email_recipients) return;
    form.error_email_recipients = form.error_email_recipients.filter((e) => e !== email);
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  $effect(() => {
    loadSettings();
  });

  const errorRoutingChannels = [
    { key: "error_routing_email" as const, label: "Email", desc: "Send error notifications to configured email recipients." },
    { key: "error_routing_in_app" as const, label: "In-App", desc: "Display error alerts in the platform notification center." },
    { key: "error_routing_webhook" as const, label: "Webhook", desc: "POST error payloads to an external webhook endpoint." },
    { key: "error_routing_syslog" as const, label: "Syslog", desc: "Forward error logs to your syslog infrastructure." },
  ];
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Integration Governance</h2>
      <p class="mt-1 text-sm text-neutral-500">Configure data sync, conflict resolution, source-of-truth designation, error routing, SLA monitoring, and version compatibility.</p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <div class="space-y-6 max-w-3xl">

    <!-- Data Sync Configuration -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Data Sync Configuration</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="sync_freq" class="block text-sm font-medium text-neutral-700 mb-1.5">Default Sync Frequency</label>
          <select
            id="sync_freq"
            bind:value={form.default_sync_frequency}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value="real_time">Real-Time</option>
            <option value="every_5m">Every 5 Minutes</option>
            <option value="every_15m">Every 15 Minutes</option>
            <option value="every_30m">Every 30 Minutes</option>
            <option value="hourly">Hourly</option>
            <option value="every_6h">Every 6 Hours</option>
            <option value="daily">Daily</option>
          </select>
        </div>
        <div>
          <label for="retry_attempts" class="block text-sm font-medium text-neutral-700 mb-1.5">Retry Attempts</label>
          <input
            id="retry_attempts"
            type="number"
            min="0"
            max="10"
            bind:value={form.sync_retry_attempts}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
        <div>
          <label for="retry_delay" class="block text-sm font-medium text-neutral-700 mb-1.5">Retry Delay (seconds)</label>
          <input
            id="retry_delay"
            type="number"
            min="5"
            max="3600"
            bind:value={form.sync_retry_delay_seconds}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
        <div class="flex items-end">
          <div class="flex items-center justify-between w-full py-2.5">
            <span class="text-sm font-medium text-neutral-700">Sync Enabled</span>
            <button
              type="button"
              onclick={() => { form.sync_enabled = !form.sync_enabled; }}
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                     {form.sync_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              role="switch"
              aria-checked={form.sync_enabled as boolean}
              aria-label="Toggle sync enabled"
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                       {form.sync_enabled ? 'translate-x-5' : 'translate-x-0.5'}"
                style="margin-top: 2px;"
              ></span>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Conflict Resolution -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Conflict Resolution</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="conflict_strategy" class="block text-sm font-medium text-neutral-700 mb-1.5">Resolution Strategy</label>
          <select
            id="conflict_strategy"
            bind:value={form.conflict_resolution_strategy}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value="source_wins">Source System Wins</option>
            <option value="target_wins">Target System Wins</option>
            <option value="most_recent">Most Recent Timestamp Wins</option>
            <option value="manual_review">Queue for Manual Review</option>
          </select>
        </div>
        <div>
          <label for="escalation_hours" class="block text-sm font-medium text-neutral-700 mb-1.5">Escalation After (hours)</label>
          <input
            id="escalation_hours"
            type="number"
            min="1"
            max="720"
            bind:value={form.conflict_escalation_after_hours}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
      </div>
      <div class="mt-4 space-y-3">
        {#each [
          { key: "conflict_auto_resolve" as const, label: "Auto-Resolve Conflicts", desc: "Automatically apply the selected resolution strategy without manual intervention." },
          { key: "conflict_notify_on_resolution" as const, label: "Notify on Resolution", desc: "Send notifications when data conflicts are detected and resolved." },
        ] as toggle}
          <div class="flex items-center justify-between py-2">
            <div>
              <p class="text-sm font-medium text-neutral-800">{toggle.label}</p>
              <p class="text-xs text-neutral-500 mt-0.5">{toggle.desc}</p>
            </div>
            <button
              type="button"
              onclick={() => { (form as Record<string, unknown>)[toggle.key] = !(form as Record<string, unknown>)[toggle.key]; }}
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                     {(form as Record<string, unknown>)[toggle.key] ? 'bg-neutral-800' : 'bg-neutral-200'}"
              role="switch"
              aria-checked={(form as Record<string, unknown>)[toggle.key] as boolean}
              aria-label="Toggle {toggle.label}"
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                       {(form as Record<string, unknown>)[toggle.key] ? 'translate-x-5' : 'translate-x-0.5'}"
                style="margin-top: 2px;"
              ></span>
            </button>
          </div>
        {/each}
      </div>
    </section>

    <!-- Source of Truth Designation -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Source of Truth Designation</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="source_of_truth" class="block text-sm font-medium text-neutral-700 mb-1.5">Primary Source of Truth</label>
          <select
            id="source_of_truth"
            bind:value={form.primary_source_of_truth}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value="erp">ERP System</option>
            <option value="crm">CRM Platform</option>
            <option value="property_management">Property Management System</option>
            <option value="finance_system">Finance & Accounting</option>
            <option value="project_management">Project Management</option>
            <option value="custom">Custom / External</option>
          </select>
        </div>
        <div class="flex items-end">
          <div class="flex items-center justify-between w-full py-2.5">
            <div>
              <span class="text-sm font-medium text-neutral-700">Allow Source Override</span>
              <p class="text-xs text-neutral-500 mt-0.5">Allow downstream systems to override source-of-truth data.</p>
            </div>
            <button
              type="button"
              onclick={() => { form.source_override_allowed = !form.source_override_allowed; }}
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                     {form.source_override_allowed ? 'bg-neutral-800' : 'bg-neutral-200'}"
              role="switch"
              aria-checked={form.source_override_allowed as boolean}
              aria-label="Toggle source override"
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                       {form.source_override_allowed ? 'translate-x-5' : 'translate-x-0.5'}"
                style="margin-top: 2px;"
              ></span>
            </button>
          </div>
        </div>
      </div>
      <div class="mt-4 rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
        <p class="text-xs text-neutral-500">
          The <span class="font-semibold text-neutral-600">source of truth</span> is the authoritative system for shared data.
          When conflicts arise, data from this system takes precedence unless overrides are explicitly allowed.
        </p>
      </div>
    </section>

    <!-- Error Log Routing -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Error Log Routing</h3>

      <div class="mb-4">
        <label for="error_severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Minimum Severity Threshold</label>
        <select
          id="error_severity"
          bind:value={form.error_severity_threshold}
          class="w-full max-w-xs rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
        >
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-3">Routing Destinations</p>
      {#each errorRoutingChannels as channel, i}
        <div class="flex items-center justify-between py-3 {i < errorRoutingChannels.length - 1 ? 'border-b border-neutral-100' : ''}">
          <div>
            <p class="text-sm font-medium text-neutral-800">{channel.label}</p>
            <p class="text-xs text-neutral-500 mt-0.5">{channel.desc}</p>
          </div>
          <button
            type="button"
            onclick={() => { (form as Record<string, unknown>)[channel.key] = !(form as Record<string, unknown>)[channel.key]; }}
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {(form as Record<string, unknown>)[channel.key] ? 'bg-neutral-800' : 'bg-neutral-200'}"
            role="switch"
            aria-checked={(form as Record<string, unknown>)[channel.key] as boolean}
            aria-label="Toggle {channel.label}"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                     {(form as Record<string, unknown>)[channel.key] ? 'translate-x-5' : 'translate-x-0.5'}"
              style="margin-top: 2px;"
            ></span>
          </button>
        </div>
      {/each}

      {#if form.error_routing_webhook}
        <div class="mt-4">
          <label for="webhook_url" class="block text-sm font-medium text-neutral-700 mb-1.5">Webhook URL</label>
          <input
            id="webhook_url"
            type="url"
            placeholder="https://example.com/webhook"
            bind:value={form.error_webhook_url}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
      {/if}

      {#if form.error_routing_email}
        <div class="mt-4">
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Email Recipients</label>
          <div class="flex gap-2">
            <input
              type="email"
              placeholder="admin@example.com"
              bind:value={newEmail}
              onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addEmail(); } }}
              class="flex-1 rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
            <button
              type="button"
              onclick={addEmail}
              class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Add
            </button>
          </div>
          {#if form.error_email_recipients && form.error_email_recipients.length > 0}
            <div class="flex flex-wrap gap-2 mt-3">
              {#each form.error_email_recipients as email}
                <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700">
                  {email}
                  <button
                    type="button"
                    onclick={() => removeEmail(email)}
                    class="text-neutral-400 hover:text-neutral-700 transition-colors"
                    aria-label="Remove {email}"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <!-- Integration SLA Monitoring -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Integration SLA Monitoring</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label for="sla_uptime" class="block text-sm font-medium text-neutral-700 mb-1.5">Target Uptime (%)</label>
          <input
            id="sla_uptime"
            type="number"
            min="90"
            max="100"
            step="0.01"
            bind:value={form.sla_target_uptime_pct}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
        </div>
        <div>
          <label for="sla_response" class="block text-sm font-medium text-neutral-700 mb-1.5">Max Response Time (ms)</label>
          <input
            id="sla_response"
            type="number"
            min="100"
            max="60000"
            bind:value={form.sla_max_response_time_ms}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          {#if form.sla_max_response_time_ms}
            <p class="text-xs text-neutral-400 mt-1">Currently: {(form as IntegrationGovernanceSettings).sla_max_response_time_display}</p>
          {/if}
        </div>
        <div>
          <label for="sla_latency" class="block text-sm font-medium text-neutral-700 mb-1.5">Max Sync Latency (sec)</label>
          <input
            id="sla_latency"
            type="number"
            min="10"
            max="86400"
            bind:value={form.sla_max_sync_latency_seconds}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          {#if form.sla_max_sync_latency_seconds}
            <p class="text-xs text-neutral-400 mt-1">Currently: {(form as IntegrationGovernanceSettings).sla_max_sync_latency_display}</p>
          {/if}
        </div>
      </div>
      <div class="mt-4 flex items-center justify-between py-2">
        <div>
          <p class="text-sm font-medium text-neutral-800">Alert on SLA Breach</p>
          <p class="text-xs text-neutral-500 mt-0.5">Send notifications when integration SLA thresholds are exceeded.</p>
        </div>
        <button
          type="button"
          onclick={() => { form.sla_alert_on_breach = !form.sla_alert_on_breach; }}
          class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                 {form.sla_alert_on_breach ? 'bg-neutral-800' : 'bg-neutral-200'}"
          role="switch"
          aria-checked={form.sla_alert_on_breach as boolean}
          aria-label="Toggle SLA breach alerts"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                   {form.sla_alert_on_breach ? 'translate-x-5' : 'translate-x-0.5'}"
            style="margin-top: 2px;"
          ></span>
        </button>
      </div>
    </section>

    <!-- Version Compatibility Tracking -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Version Compatibility Tracking</h3>
      {#if form.version_compatibility_log && form.version_compatibility_log.length > 0}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Integration</th>
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Current</th>
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Min Compatible</th>
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Status</th>
                <th class="text-left font-medium text-neutral-500 pb-2">Last Checked</th>
              </tr>
            </thead>
            <tbody>
              {#each form.version_compatibility_log as entry}
                <tr class="border-b border-neutral-50">
                  <td class="py-2.5 pr-4 text-neutral-700 font-medium">{entry.integration_name}</td>
                  <td class="py-2.5 pr-4 text-neutral-600 font-mono text-xs">{entry.current_version}</td>
                  <td class="py-2.5 pr-4 text-neutral-600 font-mono text-xs">{entry.min_compatible_version}</td>
                  <td class="py-2.5 pr-4">
                    <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium
                      {entry.status === 'compatible' ? 'bg-emerald-50 text-emerald-700' :
                       entry.status === 'deprecated' ? 'bg-amber-50 text-amber-700' :
                       entry.status === 'incompatible' ? 'bg-red-50 text-red-700' :
                       'bg-neutral-100 text-neutral-600'}">
                      {entry.status === 'compatible' ? 'Compatible' :
                       entry.status === 'deprecated' ? 'Deprecated' :
                       entry.status === 'incompatible' ? 'Incompatible' : 'Unknown'}
                    </span>
                  </td>
                  <td class="py-2.5 text-neutral-500 whitespace-nowrap">{formatDate(entry.last_checked)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center py-8">
          <svg class="mx-auto h-8 w-8 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
          <p class="mt-2 text-sm text-neutral-400">No integrations tracked yet.</p>
          <p class="text-xs text-neutral-400 mt-1">Version compatibility data is populated automatically by the integration monitoring service.</p>
        </div>
      {/if}
    </section>

  </div>
{/if}
