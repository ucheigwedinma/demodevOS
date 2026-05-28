import { registerResource } from "../index";

registerResource({
  key: "training-records",
  module: "hr",
  label: "Training Record",
  labelPlural: "Training Records",
  endpoint: "/hr/training-records/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "provider", label: "Provider", type: "text" },
    { key: "delivery_method", label: "Delivery Method", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "score", label: "Score", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ENROLLED", label: "Enrolled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "FAILED", label: "Failed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "delivery_method",
      label: "Delivery Method",
      type: "select",
      options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "ONLINE", label: "Online" },
        { value: "HYBRID", label: "Hybrid" },
        { value: "SELF_PACED", label: "Self-Paced" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "provider", label: "Provider", type: "text" },
    {
      key: "delivery_method", label: "Delivery Method", type: "select", options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "ONLINE", label: "Online" },
        { value: "HYBRID", label: "Hybrid" },
        { value: "SELF_PACED", label: "Self-Paced" },
      ],
    },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "duration_hours", label: "Duration (Hours)", type: "number" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "ENROLLED", label: "Enrolled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "FAILED", label: "Failed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "score", label: "Score", type: "number" },
    { key: "cost", label: "Cost", type: "currency" },
    { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
