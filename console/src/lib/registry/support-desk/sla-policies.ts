import { registerResource } from "../index";

registerResource({
  key: "sla-policies",
  module: "support-desk",
  label: "SLA Policy",
  labelPlural: "SLA Policies",
  endpoint: "/support-desk/sla-escalations/policies/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "category", label: "Category", type: "text" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "response_target_hours", label: "Response Target (hrs)", type: "number" },
    { key: "resolution_target_hours", label: "Resolution Target (hrs)", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "category", label: "Category", type: "text" },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    { key: "response_target_hours", label: "Response Target (hours)", type: "number", required: true },
    { key: "resolution_target_hours", label: "Resolution Target (hours)", type: "number", required: true },
    { key: "escalate_after_hours", label: "Escalate After (hours)", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
