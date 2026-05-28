<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { BackupDisasterRecoverySettings } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<BackupDisasterRecoverySettings>>({});

  async function loadSettings() {
    try {
      const data = await api.get<BackupDisasterRecoverySettings>("/settings/backup-dr/");
      form = data;
    } catch {
      toast.error("Load failed", "Could not load backup & DR settings.");
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
        backup_frequency_display,
        backup_region_display,
        rto_display,
        rpo_display,
        restore_test_logs,
        ...payload
      } = form as BackupDisasterRecoverySettings;
      const data = await api.patch<BackupDisasterRecoverySettings>("/settings/backup-dr/", payload);
      form = data;
      toast.success("Saved", "Backup & disaster recovery settings updated.");
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

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs ? `${mins}m ${secs}s` : `${mins}m`;
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

  const failoverConditions = [
    { key: "failover_on_db_failure" as const, label: "Database Failure", desc: "Trigger failover when primary database becomes unresponsive." },
    { key: "failover_on_network_outage" as const, label: "Network Outage", desc: "Trigger failover on sustained network connectivity loss." },
    { key: "failover_on_storage_failure" as const, label: "Storage Failure", desc: "Trigger failover when primary storage becomes unavailable." },
    { key: "failover_on_app_crash" as const, label: "Application Crash", desc: "Trigger failover when the application layer fails repeatedly." },
    { key: "failover_on_manual_trigger" as const, label: "Manual Trigger", desc: "Allow administrators to manually initiate failover." },
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
      <h2 class="text-xl font-bold text-neutral-800">Backup & Disaster Recovery</h2>
      <p class="mt-1 text-sm text-neutral-500">Configure backup schedules, recovery objectives, failover conditions, and restore testing for enterprise continuity.</p>
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

    <!-- Backup Configuration -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Backup Configuration</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="backup_freq" class="block text-sm font-medium text-neutral-700 mb-1.5">Backup Frequency</label>
          <select
            id="backup_freq"
            bind:value={form.backup_frequency}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value="hourly">Hourly</option>
            <option value="every_6h">Every 6 Hours</option>
            <option value="every_12h">Every 12 Hours</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>
        <div>
          <label for="backup_region" class="block text-sm font-medium text-neutral-700 mb-1.5">Backup Region</label>
          <select
            id="backup_region"
            bind:value={form.backup_region}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          >
            <option value="us-east-1">US East (N. Virginia)</option>
            <option value="us-west-2">US West (Oregon)</option>
            <option value="eu-west-1">EU West (Ireland)</option>
            <option value="eu-central-1">EU Central (Frankfurt)</option>
            <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
            <option value="af-south-1">Africa (Cape Town)</option>
            <option value="me-south-1">Middle East (Bahrain)</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Recovery Objectives -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Recovery Objectives</h3>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label for="rto" class="block text-sm font-medium text-neutral-700 mb-1.5">RTO — Recovery Time Objective (minutes)</label>
          <input
            id="rto"
            type="number"
            min="1"
            max="43200"
            bind:value={form.rto_minutes}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          {#if form.rto_minutes}
            <p class="text-xs text-neutral-400 mt-1">Currently: {(form as BackupDisasterRecoverySettings).rto_display}</p>
          {/if}
        </div>
        <div>
          <label for="rpo" class="block text-sm font-medium text-neutral-700 mb-1.5">RPO — Recovery Point Objective (minutes)</label>
          <input
            id="rpo"
            type="number"
            min="1"
            max="43200"
            bind:value={form.rpo_minutes}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
          />
          {#if form.rpo_minutes}
            <p class="text-xs text-neutral-400 mt-1">Currently: {(form as BackupDisasterRecoverySettings).rpo_display}</p>
          {/if}
        </div>
      </div>
      <div class="mt-4 rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
        <p class="text-xs text-neutral-500">
          <span class="font-semibold text-neutral-600">RTO</span> defines maximum acceptable downtime before services are restored.
          <span class="font-semibold text-neutral-600">RPO</span> defines maximum acceptable data loss measured in time. RPO must not exceed RTO.
        </p>
      </div>
    </section>

    <!-- Failover Trigger Conditions -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Failover Trigger Conditions</h3>
      {#each failoverConditions as cond, i}
        <div class="flex items-center justify-between py-3 {i < failoverConditions.length - 1 ? 'border-b border-neutral-100' : ''}">
          <div>
            <p class="text-sm font-medium text-neutral-800">{cond.label}</p>
            <p class="text-xs text-neutral-500 mt-0.5">{cond.desc}</p>
          </div>
          <button
            type="button"
            onclick={() => {
              (form as Record<string, unknown>)[cond.key] = !(form as Record<string, unknown>)[cond.key];
            }}
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {(form as Record<string, unknown>)[cond.key] ? 'bg-neutral-800' : 'bg-neutral-200'}"
            role="switch"
            aria-checked={(form as Record<string, unknown>)[cond.key] as boolean}
            aria-label="Toggle {cond.label}"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                     {(form as Record<string, unknown>)[cond.key] ? 'translate-x-5' : 'translate-x-0.5'}"
              style="margin-top: 2px;"
            ></span>
          </button>
        </div>
      {/each}
    </section>

    <!-- Restore Testing Logs -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-5">Restore Testing Logs</h3>
      {#if form.restore_test_logs && form.restore_test_logs.length > 0}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Date</th>
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Status</th>
                <th class="text-left font-medium text-neutral-500 pb-2 pr-4">Duration</th>
                <th class="text-left font-medium text-neutral-500 pb-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {#each form.restore_test_logs as log}
                <tr class="border-b border-neutral-50">
                  <td class="py-2.5 pr-4 text-neutral-700 whitespace-nowrap">{formatDate(log.date)}</td>
                  <td class="py-2.5 pr-4">
                    <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium
                      {log.status === 'pass' ? 'bg-emerald-50 text-emerald-700' :
                       log.status === 'fail' ? 'bg-red-50 text-red-700' :
                       'bg-amber-50 text-amber-700'}">
                      {log.status === 'pass' ? 'Passed' : log.status === 'fail' ? 'Failed' : 'Partial'}
                    </span>
                  </td>
                  <td class="py-2.5 pr-4 text-neutral-600 whitespace-nowrap">{formatDuration(log.duration_seconds)}</td>
                  <td class="py-2.5 text-neutral-500">{log.notes || "—"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center py-8">
          <svg class="mx-auto h-8 w-8 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          <p class="mt-2 text-sm text-neutral-400">No restore tests recorded yet.</p>
          <p class="text-xs text-neutral-400 mt-1">Restore test logs are populated by automated testing processes.</p>
        </div>
      {/if}
    </section>

  </div>
{/if}
