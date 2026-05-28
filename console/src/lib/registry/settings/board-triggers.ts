import { registerResource } from "../index";

registerResource({
  key: "board-triggers",
  module: "settings",
  label: "Board Trigger",
  labelPlural: "Board Triggers",
  endpoint: "/settings/board-notification-triggers/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "trigger_type", label: "Trigger Type", type: "text" },
    { key: "cooldown_hours", label: "Cooldown (hrs)", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search board triggers..." },
    {
      key: "trigger_type",
      label: "Trigger Type",
      type: "select",
      options: [
        { value: "severity_threshold", label: "Severity Threshold" },
        { value: "concurrent_issues", label: "Concurrent Issues" },
        { value: "financial_impact", label: "Financial Impact" },
        { value: "regulatory_breach", label: "Regulatory Breach" },
        { value: "escalation_exhausted", label: "Escalation Exhausted" },
        { value: "manual", label: "Manual" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "trigger_type",
      label: "Trigger Type",
      type: "select",
      required: true,
      options: [
        { value: "severity_threshold", label: "Severity Threshold" },
        { value: "concurrent_issues", label: "Concurrent Issues" },
        { value: "financial_impact", label: "Financial Impact" },
        { value: "regulatory_breach", label: "Regulatory Breach" },
        { value: "escalation_exhausted", label: "Escalation Exhausted" },
        { value: "manual", label: "Manual" },
      ],
    },
    { key: "cooldown_hours", label: "Cooldown (hours)", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
