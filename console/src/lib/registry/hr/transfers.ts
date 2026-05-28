import { registerResource } from "../index";

registerResource({
  key: "transfers",
  module: "hr",
  label: "Transfer",
  labelPlural: "Transfers",
  endpoint: "/hr/transfers/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "transfer_type", label: "Transfer Type", type: "badge" },
    { key: "from_department", label: "From Department", type: "text" },
    { key: "to_department", label: "To Department", type: "text" },
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
      key: "transfer_type",
      label: "Transfer Type",
      type: "select",
      options: [
        { value: "LATERAL", label: "Lateral" },
        { value: "RELOCATION", label: "Relocation" },
        { value: "TEMPORARY", label: "Temporary" },
        { value: "PERMANENT", label: "Permanent" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "transfer_type", label: "Transfer Type", type: "select", options: [
      { value: "LATERAL", label: "Lateral" },
      { value: "RELOCATION", label: "Relocation" },
      { value: "TEMPORARY", label: "Temporary" },
      { value: "PERMANENT", label: "Permanent" },
    ]},
    { key: "from_department", label: "From Department", type: "text" },
    { key: "to_department", label: "To Department", type: "text", required: true },
    { key: "from_location", label: "From Location", type: "text" },
    { key: "to_location", label: "To Location", type: "text" },
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
