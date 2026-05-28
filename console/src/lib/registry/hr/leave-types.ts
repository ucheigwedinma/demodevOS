import { registerResource } from "../index";

registerResource({
  key: "leave-types",
  module: "hr",
  label: "Leave Type",
  labelPlural: "Leave Types",
  endpoint: "/hr/leave-types/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "default_days_per_year", label: "Days/Year", type: "number" },
    { key: "is_paid", label: "Paid", type: "boolean" },
    { key: "requires_approval", label: "Requires Approval", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "default_days_per_year", label: "Default Days per Year", type: "number", required: true },
    { key: "is_paid", label: "Paid", type: "boolean", defaultValue: true },
    { key: "is_carry_over_allowed", label: "Carry Over Allowed", type: "boolean" },
    { key: "max_carry_over_days", label: "Max Carry Over Days", type: "number" },
    { key: "requires_approval", label: "Requires Approval", type: "boolean", defaultValue: true },
    { key: "requires_attachment", label: "Requires Attachment", type: "boolean" },
    { key: "min_days_notice", label: "Min Days Notice", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
