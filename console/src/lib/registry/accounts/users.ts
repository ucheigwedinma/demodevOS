import { registerResource } from "../index";

registerResource({
  key: "users",
  module: "accounts",
  label: "User",
  labelPlural: "Users",
  endpoint: "/iam/users/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "full_name", label: "Name", type: "text", sortable: true },
    { key: "email", label: "Email", type: "text", sortable: true },
    { key: "role_display", label: "Role", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "date_joined", label: "Joined", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search users..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "active", label: "Active" },
        { value: "suspended", label: "Suspended" },
        { value: "inactive", label: "Inactive" },
      ],
    },
  ],
  formFields: [
    { key: "email", label: "Email", type: "text", required: true, placeholder: "user@example.com" },
    { key: "first_name", label: "First Name", type: "text", required: true },
    { key: "last_name", label: "Last Name", type: "text", required: true },
    { key: "role", label: "Role", type: "select", options: [
      { value: "admin", label: "Admin" },
      { value: "manager", label: "Manager" },
      { value: "member", label: "Member" },
    ]},
  ],
  canDelete: true,
  actions: [
    { key: "suspend", label: "Suspend", variant: "danger", endpoint: "/iam/users/{id}/suspend/", method: "POST", confirmMessage: "Suspend this user?" },
    { key: "activate", label: "Activate", variant: "primary", endpoint: "/iam/users/{id}/activate/", method: "POST" },
  ],
});
