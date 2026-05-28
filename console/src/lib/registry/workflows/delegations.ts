import { registerResource } from "../index";

registerResource({
  key: "delegations",
  module: "workflows",
  label: "Delegation",
  labelPlural: "Delegations",
  endpoint: "/workflows/delegations/",
  columns: [
    { key: "delegator", label: "Delegator", type: "text" },
    { key: "delegate", label: "Delegate", type: "text" },
    { key: "role_scope", label: "Role Scope", type: "text" },
    { key: "starts_at", label: "Starts At", type: "datetime", sortable: true },
    { key: "ends_at", label: "Ends At", type: "datetime" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search delegations..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "EXPIRED", label: "Expired" },
        { value: "REVOKED", label: "Revoked" },
      ],
    },
  ],
  formFields: [
    { key: "delegator", label: "Delegator", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "delegate", label: "Delegate", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "starts_at", label: "Starts At", type: "datetime", required: true },
    { key: "ends_at", label: "Ends At", type: "datetime", required: true },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
