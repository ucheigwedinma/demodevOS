import { registerResource } from "../index";

registerResource({
  key: "service-accounts",
  module: "accounts",
  label: "Service Account",
  labelPlural: "Service Accounts",
  endpoint: "/iam/service-accounts/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "owner_name", label: "Owner", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "key_count", label: "Keys", type: "number" },
    { key: "created_at", label: "Created", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search service accounts..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "active", label: "Active" },
        { value: "suspended", label: "Suspended" },
        { value: "revoked", label: "Revoked" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true, placeholder: "e.g. CI/CD Pipeline" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
  actions: [],
});
