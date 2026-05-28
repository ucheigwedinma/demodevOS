import { registerResource } from "../index";

registerResource({
  key: "remote-work-logs",
  module: "hr",
  label: "Remote Work Log",
  labelPlural: "Remote Work Logs",
  endpoint: "/hr/remote-work-logs/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "date", label: "Date", type: "date", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "location", label: "Location", type: "text" },
    { key: "work_hours", label: "Work Hours", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search remote work logs..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PLANNED", label: "Planned" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "date", label: "Date", type: "date", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PLANNED", label: "Planned" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "location", label: "Location", type: "text" },
    { key: "work_hours", label: "Work Hours", type: "number" },
    { key: "tasks_completed", label: "Tasks Completed", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
