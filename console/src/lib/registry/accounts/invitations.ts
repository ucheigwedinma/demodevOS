import { registerResource } from "../index";

registerResource({
  key: "invitations",
  module: "accounts",
  label: "Invitation",
  labelPlural: "Invitations",
  endpoint: "/iam/users/invitations/",
  columns: [
    { key: "email", label: "Email", type: "text", sortable: true },
    { key: "invited_by_name", label: "Invited By", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "created_at", label: "Sent", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search invitations..." },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
