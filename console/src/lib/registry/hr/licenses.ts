import { registerResource } from "../index";

registerResource({
  key: "licenses",
  module: "hr",
  label: "Professional License",
  labelPlural: "Professional Licenses",
  endpoint: "/hr/licenses/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "license_type", label: "License Type", type: "text", sortable: true },
    { key: "license_number", label: "License Number", type: "text" },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "expiry_date", label: "Expiry Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "EXPIRED", label: "Expired" },
        { value: "PENDING", label: "Pending" },
        { value: "SUSPENDED", label: "Suspended" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "license_type", label: "License Type", type: "text", required: true },
    { key: "license_number", label: "License Number", type: "text", required: true },
    { key: "issuing_authority", label: "Issuing Authority", type: "text", required: true },
    { key: "jurisdiction", label: "Jurisdiction", type: "text" },
    { key: "issue_date", label: "Issue Date", type: "date", required: true },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "ACTIVE", label: "Active" },
        { value: "EXPIRED", label: "Expired" },
        { value: "PENDING", label: "Pending" },
        { value: "SUSPENDED", label: "Suspended" },
      ],
    },
    { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
