import { registerResource } from "../index";

registerResource({
  key: "demo-requests",
  module: "accounts",
  label: "Demo Request",
  labelPlural: "Demo Requests",
  endpoint: "/platform/demo-requests/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "full_name", label: "Name", type: "text", sortable: true },
    { key: "email", label: "Email", type: "text" },
    { key: "company_name", label: "Company", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "created_at", label: "Requested", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search demo requests..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "pending", label: "Pending" },
        { value: "provisioning", label: "Provisioning" },
        { value: "provisioned", label: "Provisioned" },
        { value: "failed", label: "Failed" },
      ],
    },
  ],
  canCreate: false,
  canDelete: false,
});
