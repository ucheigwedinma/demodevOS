import { registerResource } from "../index";

registerResource({
  key: "auto-escalation-rules",
  module: "settings",
  label: "Auto-Escalation Rule",
  labelPlural: "Auto-Escalation Rules",
  endpoint: "/settings/auto-escalation-rules/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "rule_type", label: "Rule Type", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search auto-escalation rules..." },
    {
      key: "rule_type",
      label: "Rule Type",
      type: "select",
      options: [
        { value: "time_based", label: "Time Based" },
        { value: "parallel", label: "Parallel" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "rule_type",
      label: "Rule Type",
      type: "select",
      required: true,
      options: [
        { value: "time_based", label: "Time Based" },
        { value: "parallel", label: "Parallel" },
      ],
    },
    { key: "escalate_after_minutes", label: "Escalate After (minutes)", type: "number" },
    { key: "notify_original_assignee", label: "Notify Original Assignee", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
