import { registerResource } from "../index";

registerResource({
  key: "escalation-tiers",
  module: "settings",
  label: "Escalation Tier",
  labelPlural: "Escalation Tiers",
  endpoint: "/settings/escalation-tiers/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "tier_level", label: "Tier Level", type: "number", sortable: true },
    { key: "response_time_minutes", label: "Response Time (min)", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search escalation tiers..." },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "info", label: "Info" },
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      required: true,
      options: [
        { value: "info", label: "Info" },
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
      ],
    },
    { key: "tier_level", label: "Tier Level", type: "number", required: true },
    { key: "response_time_minutes", label: "Response Time (minutes)", type: "number", required: true },
    { key: "requires_acknowledgment", label: "Requires Acknowledgment", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
