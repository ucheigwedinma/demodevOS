import { registerResource } from "../index";

registerResource({
  key: "integration-governance",
  module: "settings",
  label: "Integration Governance",
  labelPlural: "Sync frequency, conflict resolution, and error routing",
  endpoint: "/settings/integration-governance/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "sync", label: "Sync Settings" },
    { key: "conflict", label: "Conflict Resolution" },
    { key: "error", label: "Error Routing" },
  ],
  formFields: [
    { key: "sync_enabled", label: "Sync Enabled", type: "boolean", defaultValue: true, section: "sync" },
    { key: "default_sync_frequency", label: "Default Sync Frequency", type: "text", section: "sync" },
    { key: "sync_retry_attempts", label: "Retry Attempts", type: "number", defaultValue: 3, section: "sync" },
    { key: "sync_retry_delay_seconds", label: "Retry Delay (seconds)", type: "number", defaultValue: 60, section: "sync" },
    { key: "conflict_resolution_strategy", label: "Resolution Strategy", type: "text", section: "conflict" },
    { key: "conflict_auto_resolve", label: "Auto-Resolve Conflicts", type: "boolean", section: "conflict" },
    { key: "primary_source_of_truth", label: "Primary Source of Truth", type: "text", section: "conflict" },
    { key: "error_routing_email", label: "Route to Email", type: "boolean", section: "error" },
    { key: "error_routing_webhook", label: "Route to Webhook", type: "boolean", section: "error" },
    { key: "error_routing_in_app", label: "Route to In-App", type: "boolean", defaultValue: true, section: "error" },
    { key: "error_severity_threshold", label: "Severity Threshold", type: "text", section: "error" },
  ],
});
