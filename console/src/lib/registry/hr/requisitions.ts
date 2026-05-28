import { registerResource } from "../index";

registerResource({
  key: "requisitions",
  module: "hr",
  label: "Requisition",
  labelPlural: "Requisitions",
  endpoint: "/hr/requisitions/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "position", label: "Position", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "headcount_requested", label: "Headcount", type: "number" },
    { key: "salary_range_min", label: "Salary Min", type: "currency" },
    { key: "salary_range_max", label: "Salary Max", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search requisitions..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING_APPROVAL", label: "Pending Approval" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "CANCELLED", label: "Cancelled" },
        { value: "FILLED", label: "Filled" },
      ],
    },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "position", label: "Position", type: "relation_picker", optionsEndpoint: "/hr/positions/" },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "requisition_type", label: "Requisition Type", type: "text" },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
    { key: "headcount_requested", label: "Headcount Requested", type: "number", defaultValue: 1 },
    { key: "salary_range_min", label: "Salary Range Min", type: "currency" },
    { key: "salary_range_max", label: "Salary Range Max", type: "currency" },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    { key: "target_start_date", label: "Target Start Date", type: "date" },
    { key: "justification", label: "Justification", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
