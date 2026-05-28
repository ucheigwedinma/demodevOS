import { registerResource } from "../index";

registerResource({
  key: "kpi-assignments",
  module: "settings",
  label: "KPI Assignment",
  labelPlural: "KPI Assignments",
  endpoint: "/settings/kpi-assignments/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "kpi_name", label: "KPI", type: "text", sortable: true },
    { key: "role_name", label: "Role", type: "text" },
    { key: "department_name", label: "Department", type: "text" },
    { key: "target_value", label: "Target", type: "number" },
    { key: "weight", label: "Weight", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search KPI assignments..." },
  ],
  formFields: [
    { key: "kpi", label: "KPI", type: "relation_picker", required: true, optionsEndpoint: "/settings/kpi-definitions/" },
    { key: "role", label: "Role", type: "relation_picker", optionsEndpoint: "/settings/roles/" },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "target_value", label: "Target Value", type: "number" },
    { key: "weight", label: "Weight", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
