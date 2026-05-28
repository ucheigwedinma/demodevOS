import { registerResource } from "../index";

registerResource({
  key: "projects",
  module: "projects",
  label: "Project",
  labelPlural: "Projects",
  endpoint: "/projects/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "property_name", label: "Property", type: "text" },
    { key: "status", label: "Status", type: "badge", sortable: true },
    { key: "project_manager_name", label: "Manager", type: "text" },
    { key: "start_date", label: "Start", type: "date", sortable: true },
    { key: "budget", label: "Budget", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search projects..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "planning", label: "Planning" },
        { value: "in_progress", label: "In Progress" },
        { value: "on_hold", label: "On Hold" },
        { value: "completed", label: "Completed" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "status", label: "Status", type: "select", options: [
      { value: "planning", label: "Planning" },
      { value: "in_progress", label: "In Progress" },
      { value: "on_hold", label: "On Hold" },
      { value: "completed", label: "Completed" },
    ]},
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "target_end_date", label: "Target End Date", type: "date" },
    { key: "budget", label: "Budget", type: "currency" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
