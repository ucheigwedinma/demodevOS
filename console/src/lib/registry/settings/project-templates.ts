import { registerResource } from "../index";

registerResource({
  key: "project-templates",
  module: "settings",
  label: "Project Template",
  labelPlural: "Project Templates",
  endpoint: "/settings/project-templates/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "template_type", label: "Type", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "is_system", label: "System", type: "boolean" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search project templates..." },
    {
      key: "template_type",
      label: "Type",
      type: "select",
      options: [
        { value: "residential", label: "Residential" },
        { value: "mixed_use", label: "Mixed Use" },
        { value: "commercial", label: "Commercial" },
        { value: "infrastructure", label: "Infrastructure" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "template_type",
      label: "Type",
      type: "select",
      required: true,
      options: [
        { value: "residential", label: "Residential" },
        { value: "mixed_use", label: "Mixed Use" },
        { value: "commercial", label: "Commercial" },
        { value: "infrastructure", label: "Infrastructure" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
