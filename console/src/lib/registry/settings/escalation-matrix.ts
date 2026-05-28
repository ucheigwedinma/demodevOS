import { registerResource } from "../index";

registerResource({
  key: "escalation-matrix",
  module: "settings",
  label: "Escalation Matrix",
  labelPlural: "Global escalation, crisis mode, and board notification settings",
  endpoint: "/settings/escalation-matrix/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "general", label: "General" },
    { key: "crisis", label: "Crisis Mode" },
    { key: "board", label: "Board Notifications" },
  ],
  formFields: [
    { key: "escalation_enabled", label: "Escalation Enabled", type: "boolean", defaultValue: true, section: "general" },
    { key: "default_response_time_minutes", label: "Default Response Time (minutes)", type: "number", defaultValue: 60, section: "general" },
    { key: "max_escalation_levels", label: "Max Escalation Levels", type: "number", defaultValue: 3, section: "general" },
    { key: "auto_escalation_enabled", label: "Auto-Escalation Enabled", type: "boolean", defaultValue: true, section: "general" },
    { key: "require_acknowledgment", label: "Require Acknowledgment", type: "boolean", section: "general" },
    { key: "crisis_mode_enabled", label: "Crisis Mode Enabled", type: "boolean", section: "crisis" },
    { key: "crisis_activation_severity", label: "Activation Severity", type: "text", section: "crisis" },
    { key: "crisis_activation_threshold", label: "Activation Threshold", type: "number", section: "crisis" },
    { key: "crisis_war_room_enabled", label: "War Room Enabled", type: "boolean", section: "crisis" },
    { key: "board_notification_enabled", label: "Board Notification Enabled", type: "boolean", section: "board" },
    { key: "board_severity_threshold", label: "Severity Threshold", type: "text", section: "board" },
    { key: "board_notification_cooldown_hours", label: "Notification Cooldown (hours)", type: "number", defaultValue: 24, section: "board" },
  ],
});
