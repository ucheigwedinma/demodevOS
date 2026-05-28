import { registerResource } from "../index";

registerResource({
  key: "performance-goals",
  module: "hr",
  label: "Performance Goal",
  labelPlural: "Performance Goals",
  endpoint: "/hr/performance-goals/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "goal_type", label: "Goal Type", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "progress", label: "Progress", type: "number" },
    { key: "due_date", label: "Due Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "goal_type",
      label: "Goal Type",
      type: "select",
      options: [
        { value: "OKR", label: "OKR" },
        { value: "KPI", label: "KPI" },
        { value: "PROJECT", label: "Project" },
        { value: "DEVELOPMENT", label: "Development" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "goal_type", label: "Goal Type", type: "select", options: [
        { value: "OKR", label: "OKR" },
        { value: "KPI", label: "KPI" },
        { value: "PROJECT", label: "Project" },
        { value: "DEVELOPMENT", label: "Development" },
      ],
    },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "priority", label: "Priority", type: "select", options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    { key: "target_value", label: "Target Value", type: "text" },
    { key: "current_value", label: "Current Value", type: "text" },
    { key: "weight", label: "Weight", type: "number" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
