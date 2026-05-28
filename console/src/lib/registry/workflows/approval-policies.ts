import { registerResource } from "../index";

registerResource({
  key: "approval-policies",
  module: "workflows",
  label: "Approval Policy",
  labelPlural: "Approval Policies",
  endpoint: "/workflows/policies/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "policy_type", label: "Policy Type", type: "badge" },
    { key: "content_type", label: "Content Type", type: "text" },
    { key: "min_amount", label: "Min Amount", type: "currency" },
    { key: "max_amount", label: "Max Amount", type: "currency" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "policy_type", label: "Policy Type", type: "text" },
    { key: "amount_field", label: "Amount Field", type: "text" },
    { key: "min_amount", label: "Min Amount", type: "currency" },
    { key: "max_amount", label: "Max Amount", type: "currency" },
    { key: "template", label: "Template", type: "relation_picker", optionsEndpoint: "/workflows/templates/" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
