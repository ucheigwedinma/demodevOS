import { registerResource } from "../index";

registerResource({
  key: "training-plans",
  module: "hr",
  label: "Training Plan",
  labelPlural: "Training Plans",
  endpoint: "/hr/training-plans/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "department", label: "Department", type: "text" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "budget", label: "Budget", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search training plans..." },
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
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "employee", label: "Employee", type: "relation_picker", optionsEndpoint: "/hr/employee-records/" },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "budget", label: "Budget", type: "currency" },
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
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "objectives", label: "Objectives", type: "textarea", gridSpan: 2 },
  ],
});
