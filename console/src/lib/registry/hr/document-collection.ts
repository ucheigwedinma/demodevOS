import { registerResource } from "../index";

registerResource({
  key: "document-collection",
  module: "hr",
  label: "Document Collection",
  labelPlural: "Document Collections",
  endpoint: "/hr/document-collection/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "document_name", label: "Document Name", type: "text", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "due_date", label: "Due Date", type: "date", sortable: true },
    { key: "submitted_date", label: "Submitted Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "VERIFIED", label: "Verified" },
        { value: "REJECTED", label: "Rejected" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "document_name", label: "Document Name", type: "text", required: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "PENDING", label: "Pending" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "VERIFIED", label: "Verified" },
        { value: "REJECTED", label: "Rejected" },
      ],
    },
    { key: "due_date", label: "Due Date", type: "date" },
  ],
});
