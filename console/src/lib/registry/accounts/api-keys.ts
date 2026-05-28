import { registerResource } from "../index";

registerResource({
  key: "api-keys",
  module: "accounts",
  label: "API Key",
  labelPlural: "API Keys",
  endpoint: "/iam/api-keys/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "prefix", label: "Prefix", type: "text" },
    { key: "label", label: "Label", type: "text", sortable: true },
    { key: "service_account_name", label: "Service Account", type: "text" },
    { key: "status_display", label: "Status", type: "badge" },
    { key: "expires_at", label: "Expires", type: "date", sortable: true },
    { key: "last_used_at", label: "Last Used", type: "datetime" },
    { key: "created_at", label: "Created", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search API keys..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "active", label: "Active" },
        { value: "revoked", label: "Revoked" },
        { value: "expired", label: "Expired" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
