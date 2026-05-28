import { registerResource } from "../index";

registerResource({
  key: "properties",
  module: "properties",
  label: "Property",
  labelPlural: "Properties",
  endpoint: "/properties/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "property_type", label: "Type", type: "text" },
    { key: "classification", label: "Class", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "current_value", label: "Value", type: "currency" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search properties..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "property_type", label: "Type", type: "select", options: [
      { value: "residential", label: "Residential" },
      { value: "commercial", label: "Commercial" },
      { value: "mixed_use", label: "Mixed Use" },
      { value: "land", label: "Land" },
    ]},
    { key: "classification", label: "Classification", type: "text" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
