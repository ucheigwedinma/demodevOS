import { registerResource } from "../index";

registerResource({
  key: "organizations",
  module: "accounts",
  label: "Organization",
  labelPlural: "Organizations",
  endpoint: "/platform/organizations/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "industry", label: "Industry", type: "text" },
    { key: "size", label: "Size", type: "text" },
    { key: "created_at", label: "Created", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search organizations..." },
  ],
  canCreate: false,
  canDelete: false,
  superAdminOnly: true,
});
