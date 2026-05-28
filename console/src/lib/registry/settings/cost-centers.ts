import { registerResource } from "../index";

registerResource({
  key: "cost-centers",
  module: "settings",
  label: "Cost Center",
  labelPlural: "Cost Centers",
  endpoint: "/settings/cost-centers/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "code", label: "Code", type: "text", sortable: true },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "department_name", label: "Department", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search cost centers..." },
  ],
  formFields: [
    { key: "code", label: "Code", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
