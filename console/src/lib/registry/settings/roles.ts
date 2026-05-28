import { registerResource } from "../index";

registerResource({
  key: "roles",
  module: "settings",
  label: "Role",
  labelPlural: "Roles",
  endpoint: "/settings/roles/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "slug", label: "Slug", type: "text" },
    { key: "is_system", label: "System", type: "boolean" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search roles..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "slug", label: "Slug", type: "text", required: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
