import { registerResource } from "../index";

registerResource({
  key: "departments",
  module: "settings",
  label: "Department",
  labelPlural: "Departments",
  endpoint: "/settings/departments/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "division_name", label: "Division", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search departments..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "division", label: "Division", type: "relation_picker", required: true, optionsEndpoint: "/settings/divisions/" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
