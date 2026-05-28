import { registerResource } from "../index";

registerResource({
  key: "audits",
  module: "compliance",
  label: "Audit",
  labelPlural: "Audits",
  endpoint: "/compliance/audits/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "property", label: "Property", type: "text" },
    { key: "audit_type", label: "Audit Type", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "scheduled_date", label: "Scheduled Date", type: "date", sortable: true },
    { key: "completed_date", label: "Completed Date", type: "date" },
    { key: "overall_rating", label: "Overall Rating", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search audits..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PLANNED", label: "Planned" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "audit_type", label: "Audit Type", type: "text" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PLANNED", label: "Planned" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "scheduled_date", label: "Scheduled Date", type: "date", required: true },
    { key: "auditor", label: "Auditor", type: "text" },
    { key: "scope", label: "Scope", type: "textarea", gridSpan: 2 },
    { key: "findings", label: "Findings", type: "textarea", gridSpan: 2 },
  ],
});
