import { registerResource } from "../index";

registerResource({
  key: "role-changes",
  module: "hr",
  label: "Role Change",
  labelPlural: "Role Changes",
  endpoint: "/hr/role-changes/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "change_type", label: "Change Type", type: "badge" },
    { key: "from_role", label: "From Role", type: "text" },
    { key: "to_role", label: "To Role", type: "text" },
    { key: "effective_date", label: "Effective Date", type: "date" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "EFFECTIVE", label: "Effective" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "change_type",
      label: "Change Type",
      type: "select",
      options: [
        { value: "PROMOTION", label: "Promotion" },
        { value: "LATERAL", label: "Lateral" },
        { value: "DEMOTION", label: "Demotion" },
        { value: "RESTRUCTURE", label: "Restructure" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "change_type", label: "Change Type", type: "select", options: [
      { value: "PROMOTION", label: "Promotion" },
      { value: "LATERAL", label: "Lateral" },
      { value: "DEMOTION", label: "Demotion" },
      { value: "RESTRUCTURE", label: "Restructure" },
    ]},
    { key: "from_role", label: "From Role", type: "text" },
    { key: "to_role", label: "To Role", type: "text", required: true },
    { key: "effective_date", label: "Effective Date", type: "date", required: true },
    { key: "status", label: "Status", type: "select", options: [
      { value: "PENDING", label: "Pending" },
      { value: "APPROVED", label: "Approved" },
      { value: "EFFECTIVE", label: "Effective" },
      { value: "CANCELLED", label: "Cancelled" },
    ]},
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
