import { registerResource } from "../index";

registerResource({
  key: "automation-rules",
  module: "support-desk",
  label: "Automation Rule",
  labelPlural: "Automation Rules",
  endpoint: "/support-desk/automation/rules/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "trigger_type", label: "Trigger Type", type: "badge" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "run_once_per_ticket", label: "Run Once", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "trigger_type", label: "Trigger Type", type: "text" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "run_once_per_ticket", label: "Run Once per Ticket", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
