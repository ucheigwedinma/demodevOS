import { registerResource } from "../index";

registerResource({
  key: "onboarding-templates",
  module: "hr",
  label: "Onboarding Template",
  labelPlural: "Onboarding Templates",
  endpoint: "/hr/onboarding-templates/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "department", label: "Department", type: "text" },
    { key: "position", label: "Position", type: "text" },
    { key: "task_count", label: "Task Count", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "position", label: "Position", type: "relation_picker", optionsEndpoint: "/hr/positions/" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
