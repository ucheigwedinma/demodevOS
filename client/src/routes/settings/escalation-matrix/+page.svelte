<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    EscalationMatrixSettings,
    EscalationTier,
    AutoEscalationRule,
    BoardNotificationTrigger,
    PaginatedResponse,
  } from "$lib/types";

  type Tab = "global" | "tiers" | "rules" | "triggers";
  let activeTab = $state<Tab>("global");

  // --- Global Settings ---
  let settings = $state<EscalationMatrixSettings | null>(null);
  let loadingSettings = $state(true);
  let savingSettings = $state(false);

  // --- Escalation Tiers ---
  let tiers = $state<EscalationTier[]>([]);
  let loadingTiers = $state(true);
  let showTierForm = $state(false);
  let editingTierId = $state<number | null>(null);
  let tierForm = $state({
    severity: "medium" as "info" | "low" | "medium" | "high" | "critical",
    tier_level: 1,
    name: "",
    description: "",
    response_time_minutes: 60,
    escalate_to_roles: [] as string[],
    notification_channels: [] as string[],
    requires_acknowledgment: false,
    is_active: true,
  });
  let tierRoleInput = $state("");
  let tierChannelInput = $state("");

  // --- Auto-Escalation Rules ---
  let rules = $state<AutoEscalationRule[]>([]);
  let loadingRules = $state(true);
  let showRuleForm = $state(false);
  let editingRuleId = $state<number | null>(null);
  let ruleForm = $state({
    name: "",
    description: "",
    rule_type: "time_based" as "time_based" | "parallel",
    source_tier: null as number | null,
    target_tier: null as number | null,
    escalate_after_minutes: 60 as number | null,
    condition_type: "no_response" as "no_response" | "no_resolution" | "threshold_breach" | "severity_match",
    condition_threshold: null as number | null,
    notify_original_assignee: true,
    trigger_severity: "" as "info" | "low" | "medium" | "high" | "critical" | "",
    parallel_notify_roles: [] as string[],
    parallel_notify_emails: [] as string[],
    parallel_channels: [] as string[],
    is_active: true,
  });
  let ruleParallelRoleInput = $state("");
  let ruleParallelEmailInput = $state("");
  let ruleParallelChannelInput = $state("");

  // --- Board Notification Triggers ---
  let triggers = $state<BoardNotificationTrigger[]>([]);
  let loadingTriggers = $state(true);
  let showTriggerForm = $state(false);
  let editingTriggerId = $state<number | null>(null);
  let triggerForm = $state({
    name: "",
    description: "",
    trigger_type: "severity_threshold" as "severity_threshold" | "concurrent_issues" | "financial_impact" | "regulatory_breach" | "escalation_exhausted" | "manual",
    severity_threshold: "" as "info" | "low" | "medium" | "high" | "critical" | "",
    concurrent_issue_count: null as number | null,
    financial_threshold_amount: "" as string,
    notification_message_template: "",
    recipients: [] as string[],
    notification_channels: [] as string[],
    cooldown_hours: 24,
    is_active: true,
  });
  let triggerRecipientInput = $state("");
  let triggerChannelInput = $state("");

  // --- Chip inputs for global settings ---
  let crisisChannelInput = $state("");
  let boardRecipientInput = $state("");

  const severityOptions = [
    { value: "info", label: "Info" },
    { value: "low", label: "Low" },
    { value: "medium", label: "Medium" },
    { value: "high", label: "High" },
    { value: "critical", label: "Critical" },
  ];

  const channelOptions = [
    { value: "email", label: "Email" },
    { value: "in_app", label: "In-App" },
    { value: "sms", label: "SMS" },
    { value: "push", label: "Push" },
  ];

  const conditionTypeOptions = [
    { value: "no_response", label: "No Response" },
    { value: "no_resolution", label: "No Resolution" },
    { value: "threshold_breach", label: "Threshold Breach" },
    { value: "severity_match", label: "Severity Match" },
  ];

  const triggerTypeOptions = [
    { value: "severity_threshold", label: "Severity Threshold" },
    { value: "concurrent_issues", label: "Concurrent Issues" },
    { value: "financial_impact", label: "Financial Impact" },
    { value: "regulatory_breach", label: "Regulatory Breach" },
    { value: "escalation_exhausted", label: "Escalation Exhausted" },
    { value: "manual", label: "Manual" },
  ];

  onMount(async () => {
    await Promise.all([loadSettings(), loadTiers(), loadRules(), loadTriggers()]);
  });

  // ========== Global Settings ==========

  async function loadSettings() {
    loadingSettings = true;
    try {
      settings = await api.get<EscalationMatrixSettings>("/settings/escalation-matrix/");
    } catch {
      toast.error("Error", "Could not load escalation matrix settings");
    } finally {
      loadingSettings = false;
    }
  }

  async function saveSettings() {
    if (!settings) return;
    savingSettings = true;
    try {
      const { id, created_at, updated_at, crisis_activation_severity_display, board_severity_threshold_display, ...payload } = settings;
      settings = await api.patch<EscalationMatrixSettings>("/settings/escalation-matrix/", payload);
      toast.success("Saved", "Escalation matrix settings updated");
    } catch (err: any) {
      toast.error("Error", err.data?.detail || "Could not save settings");
    } finally {
      savingSettings = false;
    }
  }

  function addCrisisChannel(value: string) {
    if (!settings) return;
    const v = value.trim().toLowerCase();
    if (v && ["email", "in_app", "sms", "push"].includes(v) && !settings.crisis_notification_channels.includes(v)) {
      settings.crisis_notification_channels = [...settings.crisis_notification_channels, v];
    }
    crisisChannelInput = "";
  }

  function removeCrisisChannel(ch: string) {
    if (!settings) return;
    settings.crisis_notification_channels = settings.crisis_notification_channels.filter((c) => c !== ch);
  }

  function addBoardRecipient(value: string) {
    if (!settings) return;
    const v = value.trim();
    if (v && !settings.board_notification_recipients.includes(v)) {
      settings.board_notification_recipients = [...settings.board_notification_recipients, v];
    }
    boardRecipientInput = "";
  }

  function removeBoardRecipient(email: string) {
    if (!settings) return;
    settings.board_notification_recipients = settings.board_notification_recipients.filter((r) => r !== email);
  }

  // ========== Escalation Tiers ==========

  async function loadTiers() {
    loadingTiers = true;
    try {
      const res = await api.get<PaginatedResponse<EscalationTier>>("/settings/escalation-tiers/", { page_size: "100" });
      tiers = res.results;
    } catch {
      toast.error("Error", "Could not load escalation tiers");
    } finally {
      loadingTiers = false;
    }
  }

  function resetTierForm() {
    tierForm = {
      severity: "medium",
      tier_level: 1,
      name: "",
      description: "",
      response_time_minutes: 60,
      escalate_to_roles: [],
      notification_channels: [],
      requires_acknowledgment: false,
      is_active: true,
    };
    tierRoleInput = "";
    tierChannelInput = "";
    editingTierId = null;
    showTierForm = false;
  }

  function editTier(tier: EscalationTier) {
    editingTierId = tier.id;
    tierForm = {
      severity: tier.severity,
      tier_level: tier.tier_level,
      name: tier.name,
      description: tier.description,
      response_time_minutes: tier.response_time_minutes,
      escalate_to_roles: [...tier.escalate_to_roles],
      notification_channels: [...tier.notification_channels],
      requires_acknowledgment: tier.requires_acknowledgment,
      is_active: tier.is_active,
    };
    showTierForm = true;
  }

  async function saveTier() {
    if (!tierForm.name.trim()) {
      toast.error("Validation Error", "Tier name is required");
      return;
    }
    try {
      if (editingTierId) {
        await api.patch(`/settings/escalation-tiers/${editingTierId}/`, tierForm);
        toast.success("Updated", "Escalation tier updated");
      } else {
        await api.post("/settings/escalation-tiers/", tierForm);
        toast.success("Created", "Escalation tier created");
      }
      resetTierForm();
      await loadTiers();
    } catch (err: any) {
      toast.error("Error", err.data?.detail || "Could not save tier");
    }
  }

  async function deleteTier(id: number, name: string) {
    if (!confirm(`Delete escalation tier "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/settings/escalation-tiers/${id}/`);
      toast.success("Deleted", "Escalation tier deleted");
      await loadTiers();
    } catch {
      toast.error("Error", "Could not delete tier. It may be referenced by rules.");
    }
  }

  function addTierRole(value: string) {
    const v = value.trim();
    if (v && !tierForm.escalate_to_roles.includes(v)) {
      tierForm.escalate_to_roles = [...tierForm.escalate_to_roles, v];
    }
    tierRoleInput = "";
  }

  function removeTierRole(role: string) {
    tierForm.escalate_to_roles = tierForm.escalate_to_roles.filter((r) => r !== role);
  }

  function addTierChannel(value: string) {
    const v = value.trim().toLowerCase();
    if (v && ["email", "in_app", "sms", "push"].includes(v) && !tierForm.notification_channels.includes(v)) {
      tierForm.notification_channels = [...tierForm.notification_channels, v];
    }
    tierChannelInput = "";
  }

  function removeTierChannel(ch: string) {
    tierForm.notification_channels = tierForm.notification_channels.filter((c) => c !== ch);
  }

  // ========== Auto-Escalation Rules ==========

  async function loadRules() {
    loadingRules = true;
    try {
      const res = await api.get<PaginatedResponse<AutoEscalationRule>>("/settings/auto-escalation-rules/", { page_size: "100" });
      rules = res.results;
    } catch {
      toast.error("Error", "Could not load auto-escalation rules");
    } finally {
      loadingRules = false;
    }
  }

  function resetRuleForm() {
    ruleForm = {
      name: "",
      description: "",
      rule_type: "time_based",
      source_tier: null,
      target_tier: null,
      escalate_after_minutes: 60,
      condition_type: "no_response",
      condition_threshold: null,
      notify_original_assignee: true,
      trigger_severity: "",
      parallel_notify_roles: [],
      parallel_notify_emails: [],
      parallel_channels: [],
      is_active: true,
    };
    ruleParallelRoleInput = "";
    ruleParallelEmailInput = "";
    ruleParallelChannelInput = "";
    editingRuleId = null;
    showRuleForm = false;
  }

  function editRule(rule: AutoEscalationRule) {
    editingRuleId = rule.id;
    ruleForm = {
      name: rule.name,
      description: rule.description,
      rule_type: rule.rule_type,
      source_tier: rule.source_tier,
      target_tier: rule.target_tier,
      escalate_after_minutes: rule.escalate_after_minutes,
      condition_type: rule.condition_type,
      condition_threshold: rule.condition_threshold,
      notify_original_assignee: rule.notify_original_assignee,
      trigger_severity: rule.trigger_severity,
      parallel_notify_roles: [...rule.parallel_notify_roles],
      parallel_notify_emails: [...rule.parallel_notify_emails],
      parallel_channels: [...rule.parallel_channels],
      is_active: rule.is_active,
    };
    showRuleForm = true;
  }

  async function saveRule() {
    if (!ruleForm.name.trim()) {
      toast.error("Validation Error", "Rule name is required");
      return;
    }
    try {
      if (editingRuleId) {
        await api.patch(`/settings/auto-escalation-rules/${editingRuleId}/`, ruleForm);
        toast.success("Updated", "Auto-escalation rule updated");
      } else {
        await api.post("/settings/auto-escalation-rules/", ruleForm);
        toast.success("Created", "Auto-escalation rule created");
      }
      resetRuleForm();
      await loadRules();
    } catch (err: any) {
      toast.error("Error", err.data?.detail || "Could not save rule");
    }
  }

  async function deleteRule(id: number, name: string) {
    if (!confirm(`Delete auto-escalation rule "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/settings/auto-escalation-rules/${id}/`);
      toast.success("Deleted", "Auto-escalation rule deleted");
      await loadRules();
    } catch {
      toast.error("Error", "Could not delete rule");
    }
  }

  function addRuleParallelRole(value: string) {
    const v = value.trim();
    if (v && !ruleForm.parallel_notify_roles.includes(v)) {
      ruleForm.parallel_notify_roles = [...ruleForm.parallel_notify_roles, v];
    }
    ruleParallelRoleInput = "";
  }

  function removeRuleParallelRole(role: string) {
    ruleForm.parallel_notify_roles = ruleForm.parallel_notify_roles.filter((r) => r !== role);
  }

  function addRuleParallelEmail(value: string) {
    const v = value.trim();
    if (v && !ruleForm.parallel_notify_emails.includes(v)) {
      ruleForm.parallel_notify_emails = [...ruleForm.parallel_notify_emails, v];
    }
    ruleParallelEmailInput = "";
  }

  function removeRuleParallelEmail(email: string) {
    ruleForm.parallel_notify_emails = ruleForm.parallel_notify_emails.filter((e) => e !== email);
  }

  function addRuleParallelChannel(value: string) {
    const v = value.trim().toLowerCase();
    if (v && ["email", "in_app", "sms", "push"].includes(v) && !ruleForm.parallel_channels.includes(v)) {
      ruleForm.parallel_channels = [...ruleForm.parallel_channels, v];
    }
    ruleParallelChannelInput = "";
  }

  function removeRuleParallelChannel(ch: string) {
    ruleForm.parallel_channels = ruleForm.parallel_channels.filter((c) => c !== ch);
  }

  // ========== Board Notification Triggers ==========

  async function loadTriggers() {
    loadingTriggers = true;
    try {
      const res = await api.get<PaginatedResponse<BoardNotificationTrigger>>("/settings/board-notification-triggers/", { page_size: "100" });
      triggers = res.results;
    } catch {
      toast.error("Error", "Could not load board notification triggers");
    } finally {
      loadingTriggers = false;
    }
  }

  function resetTriggerForm() {
    triggerForm = {
      name: "",
      description: "",
      trigger_type: "severity_threshold",
      severity_threshold: "",
      concurrent_issue_count: null,
      financial_threshold_amount: "",
      notification_message_template: "",
      recipients: [],
      notification_channels: [],
      cooldown_hours: 24,
      is_active: true,
    };
    triggerRecipientInput = "";
    triggerChannelInput = "";
    editingTriggerId = null;
    showTriggerForm = false;
  }

  function editTrigger(trigger: BoardNotificationTrigger) {
    editingTriggerId = trigger.id;
    triggerForm = {
      name: trigger.name,
      description: trigger.description,
      trigger_type: trigger.trigger_type,
      severity_threshold: trigger.severity_threshold,
      concurrent_issue_count: trigger.concurrent_issue_count,
      financial_threshold_amount: trigger.financial_threshold_amount || "",
      notification_message_template: trigger.notification_message_template,
      recipients: [...trigger.recipients],
      notification_channels: [...trigger.notification_channels],
      cooldown_hours: trigger.cooldown_hours,
      is_active: trigger.is_active,
    };
    showTriggerForm = true;
  }

  async function saveTrigger() {
    if (!triggerForm.name.trim()) {
      toast.error("Validation Error", "Trigger name is required");
      return;
    }
    try {
      const payload: any = { ...triggerForm };
      if (!payload.financial_threshold_amount) payload.financial_threshold_amount = null;
      if (editingTriggerId) {
        await api.patch(`/settings/board-notification-triggers/${editingTriggerId}/`, payload);
        toast.success("Updated", "Board notification trigger updated");
      } else {
        await api.post("/settings/board-notification-triggers/", payload);
        toast.success("Created", "Board notification trigger created");
      }
      resetTriggerForm();
      await loadTriggers();
    } catch (err: any) {
      toast.error("Error", err.data?.detail || "Could not save trigger");
    }
  }

  async function deleteTrigger(id: number, name: string) {
    if (!confirm(`Delete board trigger "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/settings/board-notification-triggers/${id}/`);
      toast.success("Deleted", "Board notification trigger deleted");
      await loadTriggers();
    } catch {
      toast.error("Error", "Could not delete trigger");
    }
  }

  function addTriggerRecipient(value: string) {
    const v = value.trim();
    if (v && !triggerForm.recipients.includes(v)) {
      triggerForm.recipients = [...triggerForm.recipients, v];
    }
    triggerRecipientInput = "";
  }

  function removeTriggerRecipient(email: string) {
    triggerForm.recipients = triggerForm.recipients.filter((r) => r !== email);
  }

  function addTriggerChannel(value: string) {
    const v = value.trim().toLowerCase();
    if (v && ["email", "in_app", "sms", "push"].includes(v) && !triggerForm.notification_channels.includes(v)) {
      triggerForm.notification_channels = [...triggerForm.notification_channels, v];
    }
    triggerChannelInput = "";
  }

  function removeTriggerChannel(ch: string) {
    triggerForm.notification_channels = triggerForm.notification_channels.filter((c) => c !== ch);
  }

  function getTierName(id: number | null): string {
    if (!id) return "-";
    const tier = tiers.find((t) => t.id === id);
    return tier ? tier.name : `Tier #${id}`;
  }

  function getConditionSummary(trigger: BoardNotificationTrigger): string {
    switch (trigger.trigger_type) {
      case "severity_threshold":
        return trigger.severity_threshold_display ? `Severity >= ${trigger.severity_threshold_display}` : "Severity threshold";
      case "concurrent_issues":
        return trigger.concurrent_issue_count ? `>= ${trigger.concurrent_issue_count} concurrent` : "Concurrent issues";
      case "financial_impact":
        return trigger.financial_threshold_amount ? `>= ${currency.formatCompact(trigger.financial_threshold_amount)}` : "Financial impact";
      case "regulatory_breach":
        return "Regulatory breach detected";
      case "escalation_exhausted":
        return "All escalation tiers exhausted";
      case "manual":
        return "Manually triggered";
      default:
        return trigger.trigger_type_display;
    }
  }
</script>

<div class="max-w-4xl">
  <div class="mb-8">
    <h2 class="text-xl font-bold text-neutral-800">Escalation Matrix</h2>
    <p class="text-sm text-neutral-500 mt-1">
      Configure escalation tiers, auto-escalation rules, crisis mode, and board notification triggers.
    </p>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 border-b border-neutral-200 mb-6">
    {#each [
      { key: "global" as Tab, label: "Global Settings" },
      { key: "tiers" as Tab, label: "Escalation Tiers" },
      { key: "rules" as Tab, label: "Auto-Escalation Rules" },
      { key: "triggers" as Tab, label: "Board Triggers" },
    ] as tab}
      <button
        onclick={() => (activeTab = tab.key)}
        class="px-4 py-2.5 text-sm font-medium transition-colors {activeTab === tab.key
          ? 'border-b-2 border-neutral-800 text-neutral-800'
          : 'text-neutral-400 hover:text-neutral-600'}"
      >
        {tab.label}
      </button>
    {/each}
  </div>

  <!-- ==================== Tab 1: Global Settings ==================== -->
  {#if activeTab === "global"}
    {#if loadingSettings}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else if settings}
      <div class="space-y-6">
        <!-- Global Escalation Configuration -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">Global Escalation Configuration</h3>
          <div class="space-y-4">
            <!-- Escalation Enabled -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">Escalation Enabled</p>
                <p class="text-xs text-neutral-400">Enable or disable the escalation system globally</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.escalation_enabled = !settings!.escalation_enabled}
                class="w-10 h-5 rounded-full transition-colors {settings.escalation_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.escalation_enabled ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Default Response Time -->
            <div>
              <label for="default-response-time" class="block text-sm font-medium text-neutral-700 mb-1.5">Default Response Time (minutes)</label>
              <input
                id="default-response-time"
                type="number"
                min="1"
                bind:value={settings.default_response_time_minutes}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Max Escalation Levels -->
            <div>
              <label for="max-escalation-levels" class="block text-sm font-medium text-neutral-700 mb-1.5">Max Escalation Levels</label>
              <input
                id="max-escalation-levels"
                type="number"
                min="1"
                bind:value={settings.max_escalation_levels}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Auto-Escalation Enabled -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">Auto-Escalation Enabled</p>
                <p class="text-xs text-neutral-400">Automatically escalate issues based on rules</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.auto_escalation_enabled = !settings!.auto_escalation_enabled}
                class="w-10 h-5 rounded-full transition-colors {settings.auto_escalation_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.auto_escalation_enabled ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Require Acknowledgment -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">Require Acknowledgment</p>
                <p class="text-xs text-neutral-400">Require recipients to acknowledge escalations</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.require_acknowledgment = !settings!.require_acknowledgment}
                class="w-10 h-5 rounded-full transition-colors {settings.require_acknowledgment ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.require_acknowledgment ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
          </div>
        </div>

        <!-- Crisis Mode Activation -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">Crisis Mode Activation</h3>
          <div class="space-y-4">
            <!-- Crisis Mode Enabled -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">Crisis Mode Enabled</p>
                <p class="text-xs text-neutral-400">Enable automatic crisis mode activation</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.crisis_mode_enabled = !settings!.crisis_mode_enabled}
                class="w-10 h-5 rounded-full transition-colors {settings.crisis_mode_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.crisis_mode_enabled ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Activation Severity -->
            <div>
              <label for="crisis-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Activation Severity</label>
              <select
                id="crisis-severity"
                bind:value={settings.crisis_activation_severity}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              >
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <!-- Activation Threshold -->
            <div>
              <label for="crisis-threshold" class="block text-sm font-medium text-neutral-700 mb-1.5">Activation Threshold (concurrent issues)</label>
              <input
                id="crisis-threshold"
                type="number"
                min="1"
                bind:value={settings.crisis_activation_threshold}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Notification Channels -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Notification Channels</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each settings.crisis_notification_channels as ch}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {ch}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeCrisisChannel(ch)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <select
                bind:value={crisisChannelInput}
                onchange={() => { addCrisisChannel(crisisChannelInput); }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              >
                <option value="">Add channel...</option>
                {#each channelOptions.filter((o) => !settings!.crisis_notification_channels.includes(o.value)) as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <!-- War Room Enabled -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">War Room Enabled</p>
                <p class="text-xs text-neutral-400">Activate a virtual war room during crisis mode</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.crisis_war_room_enabled = !settings!.crisis_war_room_enabled}
                class="w-10 h-5 rounded-full transition-colors {settings.crisis_war_room_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.crisis_war_room_enabled ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Auto-Deactivate Hours -->
            <div>
              <label for="crisis-deactivate" class="block text-sm font-medium text-neutral-700 mb-1.5">Auto-Deactivate After (hours)</label>
              <input
                id="crisis-deactivate"
                type="number"
                min="1"
                bind:value={settings.crisis_auto_deactivate_hours}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Board Notification Defaults -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">Board Notification Defaults</h3>
          <div class="space-y-4">
            <!-- Board Notifications Enabled -->
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-700">Board Notifications Enabled</p>
                <p class="text-xs text-neutral-400">Send notifications to board members for critical issues</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => settings!.board_notification_enabled = !settings!.board_notification_enabled}
                class="w-10 h-5 rounded-full transition-colors {settings.board_notification_enabled ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {settings.board_notification_enabled ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Severity Threshold -->
            <div>
              <label for="board-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Severity Threshold</label>
              <select
                id="board-severity"
                bind:value={settings.board_severity_threshold}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              >
                <option value="critical_only">Critical Only</option>
                <option value="high_and_above">High & Critical</option>
              </select>
            </div>
            <!-- Board Recipients -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Board Recipients</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each settings.board_notification_recipients as email}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {email}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeBoardRecipient(email)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <input
                type="text"
                bind:value={boardRecipientInput}
                placeholder="Type email and press Enter"
                onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addBoardRecipient(boardRecipientInput); } }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Cooldown Hours -->
            <div>
              <label for="board-cooldown" class="block text-sm font-medium text-neutral-700 mb-1.5">Cooldown Hours</label>
              <input
                id="board-cooldown"
                type="number"
                min="0"
                bind:value={settings.board_notification_cooldown_hours}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Save Button -->
        <div class="flex justify-end">
          <button
            onclick={saveSettings}
            disabled={savingSettings}
            class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
          >
            {savingSettings ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ==================== Tab 2: Escalation Tiers ==================== -->
  {#if activeTab === "tiers"}
    <div class="space-y-4">
      <div class="flex items-center justify-end">
        <button
          onclick={() => { resetTierForm(); showTierForm = true; }}
          class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
        >
          + Add Tier
        </button>
      </div>

      {#if loadingTiers}
        <div class="flex items-center justify-center py-12">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if tiers.length === 0 && !showTierForm}
        <div class="text-center py-12">
          <p class="text-sm text-neutral-400">No escalation tiers defined yet.</p>
        </div>
      {:else}
        {#if tiers.length > 0}
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Severity</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Tier Level</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Name</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Response Time</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Roles</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Channels</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Active</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each tiers as tier}
                    <tr>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{tier.severity_display}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{tier.tier_level}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100 font-medium">{tier.name}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{tier.response_time_minutes}m</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">
                        <div class="flex flex-wrap gap-1">
                          {#each tier.escalate_to_roles as role}
                            <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">{role}</span>
                          {/each}
                          {#if tier.escalate_to_roles.length === 0}
                            <span class="text-neutral-400">-</span>
                          {/if}
                        </div>
                      </td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">
                        <div class="flex flex-wrap gap-1">
                          {#each tier.notification_channels as ch}
                            <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">{ch}</span>
                          {/each}
                          {#if tier.notification_channels.length === 0}
                            <span class="text-neutral-400">-</span>
                          {/if}
                        </div>
                      </td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {tier.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                          {tier.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <div class="flex items-center gap-3">
                          <button onclick={() => editTier(tier)} class="text-neutral-400 hover:text-neutral-700">Edit</button>
                          <button onclick={() => deleteTier(tier.id, tier.name)} class="text-neutral-400 hover:text-red-600">Delete</button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      {/if}

      {#if showTierForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">
            {editingTierId ? "Edit Escalation Tier" : "New Escalation Tier"}
          </h3>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label for="tier-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Severity</label>
                <select
                  id="tier-severity"
                  bind:value={tierForm.severity}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  {#each severityOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
              <div>
                <label for="tier-level" class="block text-sm font-medium text-neutral-700 mb-1.5">Tier Level</label>
                <input
                  id="tier-level"
                  type="number"
                  min="1"
                  max="10"
                  bind:value={tierForm.tier_level}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
              <div>
                <label for="tier-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name</label>
                <input
                  id="tier-name"
                  type="text"
                  bind:value={tierForm.name}
                  placeholder="e.g., Level 1 Support"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
            </div>
            <div>
              <label for="tier-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
              <textarea
                id="tier-desc"
                bind:value={tierForm.description}
                rows="2"
                placeholder="Describe this escalation tier..."
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none resize-none"
              ></textarea>
            </div>
            <div>
              <label for="tier-response" class="block text-sm font-medium text-neutral-700 mb-1.5">Response Time (minutes)</label>
              <input
                id="tier-response"
                type="number"
                min="1"
                bind:value={tierForm.response_time_minutes}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Escalate to Roles (chips) -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Escalate to Roles</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each tierForm.escalate_to_roles as role}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {role}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeTierRole(role)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <input
                type="text"
                bind:value={tierRoleInput}
                placeholder="Type role slug and press Enter"
                onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTierRole(tierRoleInput); } }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Notification Channels (chips) -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Notification Channels</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each tierForm.notification_channels as ch}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {ch}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeTierChannel(ch)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <select
                bind:value={tierChannelInput}
                onchange={() => { addTierChannel(tierChannelInput); }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              >
                <option value="">Add channel...</option>
                {#each channelOptions.filter((o) => !tierForm.notification_channels.includes(o.value)) as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <!-- Toggles -->
            <div class="flex items-center gap-8">
              <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-neutral-700">Requires Acknowledgment</span>
                <!-- svelte-ignore a11y_consider_explicit_label -->
                <button
                  type="button"
                  onclick={() => tierForm.requires_acknowledgment = !tierForm.requires_acknowledgment}
                  class="w-10 h-5 rounded-full transition-colors {tierForm.requires_acknowledgment ? 'bg-neutral-800' : 'bg-neutral-200'}"
                >
                  <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {tierForm.requires_acknowledgment ? 'translate-x-5' : 'translate-x-0.5'}"></div>
                </button>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-neutral-700">Active</span>
                <!-- svelte-ignore a11y_consider_explicit_label -->
                <button
                  type="button"
                  onclick={() => tierForm.is_active = !tierForm.is_active}
                  class="w-10 h-5 rounded-full transition-colors {tierForm.is_active ? 'bg-neutral-800' : 'bg-neutral-200'}"
                >
                  <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {tierForm.is_active ? 'translate-x-5' : 'translate-x-0.5'}"></div>
                </button>
              </div>
            </div>
            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                onclick={resetTierForm}
                class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onclick={saveTier}
                class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
              >
                {editingTierId ? "Save Changes" : "Create Tier"}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- ==================== Tab 3: Auto-Escalation Rules ==================== -->
  {#if activeTab === "rules"}
    <div class="space-y-4">
      <div class="flex items-center justify-end">
        <button
          onclick={() => { resetRuleForm(); showRuleForm = true; }}
          class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
        >
          + Add Rule
        </button>
      </div>

      {#if loadingRules}
        <div class="flex items-center justify-center py-12">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if rules.length === 0 && !showRuleForm}
        <div class="text-center py-12">
          <p class="text-sm text-neutral-400">No auto-escalation rules defined yet.</p>
        </div>
      {:else}
        {#if rules.length > 0}
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Name</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Type</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Source / Target / Trigger</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Condition</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Active</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each rules as rule}
                    <tr>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100 font-medium">{rule.name}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{rule.rule_type_display}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">
                        {#if rule.rule_type === "time_based"}
                          {rule.source_tier_name || "-"} &rarr; {rule.target_tier_name || "-"}
                        {:else}
                          {rule.trigger_severity_display || "-"}
                        {/if}
                      </td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">
                        {#if rule.rule_type === "time_based"}
                          {rule.condition_type_display}{rule.escalate_after_minutes ? ` (${rule.escalate_after_minutes}m)` : ""}
                        {:else}
                          Parallel notification
                        {/if}
                      </td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {rule.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                          {rule.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <div class="flex items-center gap-3">
                          <button onclick={() => editRule(rule)} class="text-neutral-400 hover:text-neutral-700">Edit</button>
                          <button onclick={() => deleteRule(rule.id, rule.name)} class="text-neutral-400 hover:text-red-600">Delete</button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      {/if}

      {#if showRuleForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">
            {editingRuleId ? "Edit Auto-Escalation Rule" : "New Auto-Escalation Rule"}
          </h3>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="rule-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name</label>
                <input
                  id="rule-name"
                  type="text"
                  bind:value={ruleForm.name}
                  placeholder="e.g., Critical No-Response Escalation"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
              <div>
                <label for="rule-type" class="block text-sm font-medium text-neutral-700 mb-1.5">Rule Type</label>
                <select
                  id="rule-type"
                  bind:value={ruleForm.rule_type}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  <option value="time_based">Time Based</option>
                  <option value="parallel">Parallel</option>
                </select>
              </div>
            </div>
            <div>
              <label for="rule-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
              <textarea
                id="rule-desc"
                bind:value={ruleForm.description}
                rows="2"
                placeholder="Describe this rule..."
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none resize-none"
              ></textarea>
            </div>

            {#if ruleForm.rule_type === "time_based"}
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label for="rule-source" class="block text-sm font-medium text-neutral-700 mb-1.5">Source Tier</label>
                  <select
                    id="rule-source"
                    bind:value={ruleForm.source_tier}
                    class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                  >
                    <option value={null}>Select tier...</option>
                    {#each tiers as tier}
                      <option value={tier.id}>#{tier.id} - {tier.name}</option>
                    {/each}
                  </select>
                </div>
                <div>
                  <label for="rule-target" class="block text-sm font-medium text-neutral-700 mb-1.5">Target Tier</label>
                  <select
                    id="rule-target"
                    bind:value={ruleForm.target_tier}
                    class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                  >
                    <option value={null}>Select tier...</option>
                    {#each tiers as tier}
                      <option value={tier.id}>#{tier.id} - {tier.name}</option>
                    {/each}
                  </select>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label for="rule-escalate-after" class="block text-sm font-medium text-neutral-700 mb-1.5">Escalate After (minutes)</label>
                  <input
                    id="rule-escalate-after"
                    type="number"
                    min="1"
                    bind:value={ruleForm.escalate_after_minutes}
                    class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                  />
                </div>
                <div>
                  <label for="rule-condition" class="block text-sm font-medium text-neutral-700 mb-1.5">Condition Type</label>
                  <select
                    id="rule-condition"
                    bind:value={ruleForm.condition_type}
                    class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                  >
                    {#each conditionTypeOptions as opt}
                      <option value={opt.value}>{opt.label}</option>
                    {/each}
                  </select>
                </div>
                <div>
                  <label for="rule-threshold" class="block text-sm font-medium text-neutral-700 mb-1.5">Condition Threshold</label>
                  <input
                    id="rule-threshold"
                    type="number"
                    min="0"
                    bind:value={ruleForm.condition_threshold}
                    placeholder="Optional"
                    class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                  />
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-neutral-700">Notify Original Assignee</span>
                <!-- svelte-ignore a11y_consider_explicit_label -->
                <button
                  type="button"
                  onclick={() => ruleForm.notify_original_assignee = !ruleForm.notify_original_assignee}
                  class="w-10 h-5 rounded-full transition-colors {ruleForm.notify_original_assignee ? 'bg-neutral-800' : 'bg-neutral-200'}"
                >
                  <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {ruleForm.notify_original_assignee ? 'translate-x-5' : 'translate-x-0.5'}"></div>
                </button>
              </div>
            {:else}
              <!-- Parallel rule type -->
              <div>
                <label for="rule-trigger-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Trigger Severity</label>
                <select
                  id="rule-trigger-severity"
                  bind:value={ruleForm.trigger_severity}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  <option value="">Select severity...</option>
                  {#each severityOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
              <!-- Parallel Notify Roles -->
              <div>
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">Parallel Notify Roles</label>
                <div class="flex flex-wrap gap-2 mb-2">
                  {#each ruleForm.parallel_notify_roles as role}
                    <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                      {role}
                      <!-- svelte-ignore a11y_consider_explicit_label -->
                      <button type="button" onclick={() => removeRuleParallelRole(role)} class="text-neutral-400 hover:text-neutral-700">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </span>
                  {/each}
                </div>
                <input
                  type="text"
                  bind:value={ruleParallelRoleInput}
                  placeholder="Type role slug and press Enter"
                  onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addRuleParallelRole(ruleParallelRoleInput); } }}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
              <!-- Parallel Notify Emails -->
              <div>
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">Parallel Notify Emails</label>
                <div class="flex flex-wrap gap-2 mb-2">
                  {#each ruleForm.parallel_notify_emails as email}
                    <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                      {email}
                      <!-- svelte-ignore a11y_consider_explicit_label -->
                      <button type="button" onclick={() => removeRuleParallelEmail(email)} class="text-neutral-400 hover:text-neutral-700">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </span>
                  {/each}
                </div>
                <input
                  type="text"
                  bind:value={ruleParallelEmailInput}
                  placeholder="Type email and press Enter"
                  onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addRuleParallelEmail(ruleParallelEmailInput); } }}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
              <!-- Parallel Channels -->
              <div>
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">Parallel Channels</label>
                <div class="flex flex-wrap gap-2 mb-2">
                  {#each ruleForm.parallel_channels as ch}
                    <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                      {ch}
                      <!-- svelte-ignore a11y_consider_explicit_label -->
                      <button type="button" onclick={() => removeRuleParallelChannel(ch)} class="text-neutral-400 hover:text-neutral-700">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </span>
                  {/each}
                </div>
                <select
                  bind:value={ruleParallelChannelInput}
                  onchange={() => { addRuleParallelChannel(ruleParallelChannelInput); }}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  <option value="">Add channel...</option>
                  {#each channelOptions.filter((o) => !ruleForm.parallel_channels.includes(o.value)) as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            {/if}

            <!-- Active toggle -->
            <div class="flex items-center gap-3">
              <span class="text-sm font-medium text-neutral-700">Active</span>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => ruleForm.is_active = !ruleForm.is_active}
                class="w-10 h-5 rounded-full transition-colors {ruleForm.is_active ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {ruleForm.is_active ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                onclick={resetRuleForm}
                class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onclick={saveRule}
                class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
              >
                {editingRuleId ? "Save Changes" : "Create Rule"}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- ==================== Tab 4: Board Notification Triggers ==================== -->
  {#if activeTab === "triggers"}
    <div class="space-y-4">
      <div class="flex items-center justify-end">
        <button
          onclick={() => { resetTriggerForm(); showTriggerForm = true; }}
          class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
        >
          + Add Trigger
        </button>
      </div>

      {#if loadingTriggers}
        <div class="flex items-center justify-center py-12">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if triggers.length === 0 && !showTriggerForm}
        <div class="text-center py-12">
          <p class="text-sm text-neutral-400">No board notification triggers defined yet.</p>
        </div>
      {:else}
        {#if triggers.length > 0}
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Name</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Type</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Condition Summary</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Cooldown</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Active</th>
                    <th class="px-4 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider border-b border-neutral-200">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each triggers as trigger}
                    <tr>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100 font-medium">{trigger.name}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{trigger.trigger_type_display}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{getConditionSummary(trigger)}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700 border-b border-neutral-100">{trigger.cooldown_hours}h</td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {trigger.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                          {trigger.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td class="px-4 py-3 text-sm border-b border-neutral-100">
                        <div class="flex items-center gap-3">
                          <button onclick={() => editTrigger(trigger)} class="text-neutral-400 hover:text-neutral-700">Edit</button>
                          <button onclick={() => deleteTrigger(trigger.id, trigger.name)} class="text-neutral-400 hover:text-red-600">Delete</button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      {/if}

      {#if showTriggerForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">
            {editingTriggerId ? "Edit Board Notification Trigger" : "New Board Notification Trigger"}
          </h3>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="trigger-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name</label>
                <input
                  id="trigger-name"
                  type="text"
                  bind:value={triggerForm.name}
                  placeholder="e.g., Critical Severity Board Alert"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
              <div>
                <label for="trigger-type" class="block text-sm font-medium text-neutral-700 mb-1.5">Trigger Type</label>
                <select
                  id="trigger-type"
                  bind:value={triggerForm.trigger_type}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  {#each triggerTypeOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            </div>
            <div>
              <label for="trigger-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
              <textarea
                id="trigger-desc"
                bind:value={triggerForm.description}
                rows="2"
                placeholder="Describe this trigger..."
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none resize-none"
              ></textarea>
            </div>

            <!-- Conditional fields based on trigger_type -->
            {#if triggerForm.trigger_type === "severity_threshold"}
              <div>
                <label for="trigger-severity" class="block text-sm font-medium text-neutral-700 mb-1.5">Severity</label>
                <select
                  id="trigger-severity"
                  bind:value={triggerForm.severity_threshold}
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                >
                  <option value="">Select severity...</option>
                  {#each severityOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            {/if}
            {#if triggerForm.trigger_type === "concurrent_issues"}
              <div>
                <label for="trigger-concurrent" class="block text-sm font-medium text-neutral-700 mb-1.5">Concurrent Issue Count</label>
                <input
                  id="trigger-concurrent"
                  type="number"
                  min="1"
                  bind:value={triggerForm.concurrent_issue_count}
                  placeholder="e.g., 5"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
            {/if}
            {#if triggerForm.trigger_type === "financial_impact"}
              <div>
                <label for="trigger-financial" class="block text-sm font-medium text-neutral-700 mb-1.5">Financial Threshold Amount</label>
                <input
                  id="trigger-financial"
                  type="number"
                  min="0"
                  step="0.01"
                  bind:value={triggerForm.financial_threshold_amount}
                  placeholder="e.g., 100000"
                  class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
                />
              </div>
            {/if}

            <!-- Notification Message Template -->
            <div>
              <label for="trigger-template" class="block text-sm font-medium text-neutral-700 mb-1.5">Notification Message Template</label>
              <textarea
                id="trigger-template"
                bind:value={triggerForm.notification_message_template}
                rows="3"
                placeholder="Template for the notification message..."
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none resize-none"
              ></textarea>
            </div>
            <!-- Recipients (chips) -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Recipients</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each triggerForm.recipients as email}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {email}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeTriggerRecipient(email)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <input
                type="text"
                bind:value={triggerRecipientInput}
                placeholder="Type email and press Enter"
                onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTriggerRecipient(triggerRecipientInput); } }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Notification Channels (chips) -->
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">Notification Channels</label>
              <div class="flex flex-wrap gap-2 mb-2">
                {#each triggerForm.notification_channels as ch}
                  <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
                    {ch}
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button type="button" onclick={() => removeTriggerChannel(ch)} class="text-neutral-400 hover:text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </span>
                {/each}
              </div>
              <select
                bind:value={triggerChannelInput}
                onchange={() => { addTriggerChannel(triggerChannelInput); }}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              >
                <option value="">Add channel...</option>
                {#each channelOptions.filter((o) => !triggerForm.notification_channels.includes(o.value)) as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <!-- Cooldown Hours -->
            <div>
              <label for="trigger-cooldown" class="block text-sm font-medium text-neutral-700 mb-1.5">Cooldown Hours</label>
              <input
                id="trigger-cooldown"
                type="number"
                min="0"
                bind:value={triggerForm.cooldown_hours}
                class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none"
              />
            </div>
            <!-- Active toggle -->
            <div class="flex items-center gap-3">
              <span class="text-sm font-medium text-neutral-700">Active</span>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                type="button"
                onclick={() => triggerForm.is_active = !triggerForm.is_active}
                class="w-10 h-5 rounded-full transition-colors {triggerForm.is_active ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div class="w-4 h-4 rounded-full bg-white shadow transition-transform {triggerForm.is_active ? 'translate-x-5' : 'translate-x-0.5'}"></div>
              </button>
            </div>
            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                onclick={resetTriggerForm}
                class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onclick={saveTrigger}
                class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
              >
                {editingTriggerId ? "Save Changes" : "Create Trigger"}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
