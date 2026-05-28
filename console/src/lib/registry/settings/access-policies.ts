import { registerResource } from "../index";

registerResource({
  key: "access-policies",
  module: "settings",
  label: "Access Policy",
  labelPlural: "Access Policies",
  endpoint: "/settings/access-policies/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "key", label: "Key", type: "text" },
    { key: "module", label: "Module", type: "text", sortable: true },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "priority", label: "Priority", type: "number", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search access policies..." },
    { key: "module", label: "Module", type: "select" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "key", label: "Key", type: "text", required: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "module", label: "Module", type: "text", required: true },
    { key: "sub_module", label: "Sub-Module", type: "text" },
    { key: "action", label: "Action", type: "text" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
