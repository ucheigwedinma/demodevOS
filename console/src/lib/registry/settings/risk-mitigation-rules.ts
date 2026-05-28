import { registerResource } from "../index";

registerResource({
  key: "risk-mitigation-rules",
  module: "settings",
  label: "Risk Mitigation Rule",
  labelPlural: "Risk Mitigation Rules",
  endpoint: "/settings/risk-mitigation-rules/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "risk_category_name", label: "Risk Category", type: "text", sortable: true },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "response_time_hours", label: "Response Time (hrs)", type: "number" },
    { key: "escalation_required", label: "Escalation Required", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search mitigation rules..." },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
      ],
    },
  ],
  formFields: [
    { key: "risk_category", label: "Risk Category", type: "relation_picker", required: true, optionsEndpoint: "/settings/risk-categories/" },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      required: true,
      options: [
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
      ],
    },
    { key: "assign_to_role", label: "Assign to Role", type: "relation_picker", optionsEndpoint: "/settings/roles/" },
    { key: "response_time_hours", label: "Response Time (hours)", type: "number" },
    { key: "escalation_required", label: "Escalation Required", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
