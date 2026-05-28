import { registerResource } from "../index";

registerResource({
  key: "policy-acknowledgements",
  module: "hr",
  label: "Policy Acknowledgement",
  labelPlural: "Policy Acknowledgements",
  endpoint: "/hr/policy-acknowledgements/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "policy", label: "Policy", type: "text" },
    { key: "acknowledged", label: "Acknowledged", type: "boolean" },
    { key: "acknowledged_date", label: "Acknowledged Date", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
