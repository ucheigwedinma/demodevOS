import { registerResource } from "../index";

registerResource({
  key: "certifications",
  module: "hr",
  label: "Certification",
  labelPlural: "Certifications",
  endpoint: "/hr/certifications/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "issuing_body", label: "Issuing Body", type: "text" },
    { key: "credential_id", label: "Credential ID", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "issue_date", label: "Issue Date", type: "date", sortable: true },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
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
        { value: "REVOKED", label: "Revoked" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "issuing_body", label: "Issuing Body", type: "text", required: true },
    { key: "credential_id", label: "Credential ID", type: "text" },
    { key: "issue_date", label: "Issue Date", type: "date", required: true },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "ACTIVE", label: "Active" },
        { value: "EXPIRED", label: "Expired" },
        { value: "PENDING", label: "Pending" },
        { value: "REVOKED", label: "Revoked" },
      ],
    },
    { key: "verification_url", label: "Verification URL", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
