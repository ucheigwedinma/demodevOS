import { registerResource } from "../index";

registerResource({
  key: "onboarding-tasks",
  module: "hr",
  label: "Onboarding Task",
  labelPlural: "Onboarding Tasks",
  endpoint: "/hr/onboarding-tasks/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "employee", label: "Employee", type: "text" },
    { key: "category", label: "Category", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "is_required", label: "Required", type: "boolean" },
    { key: "due_date", label: "Due Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "SKIPPED", label: "Skipped" },
      ],
    },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "DOCUMENTATION", label: "Documentation" },
        { value: "TRAINING", label: "Training" },
        { value: "ACCESS", label: "Access" },
        { value: "INTRODUCTION", label: "Introduction" },
        { value: "COMPLIANCE", label: "Compliance" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "template", label: "Template", type: "relation_picker", optionsEndpoint: "/hr/onboarding-templates/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "category", label: "Category", type: "select", options: [
        { value: "DOCUMENTATION", label: "Documentation" },
        { value: "TRAINING", label: "Training" },
        { value: "ACCESS", label: "Access" },
        { value: "INTRODUCTION", label: "Introduction" },
        { value: "COMPLIANCE", label: "Compliance" },
        { value: "OTHER", label: "Other" },
      ],
    },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "SKIPPED", label: "Skipped" },
      ],
    },
    { key: "assigned_to", label: "Assigned To", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "is_required", label: "Required", type: "boolean", defaultValue: true },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
