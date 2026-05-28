import { registerResource } from "../index";

registerResource({
  key: "requirements",
  module: "compliance",
  label: "Requirement",
  labelPlural: "Requirements",
  endpoint: "/compliance/requirements/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "category", label: "Category", type: "badge" },
    { key: "regulatory_reference", label: "Regulatory Reference", type: "text" },
    { key: "renewal_frequency", label: "Renewal Frequency", type: "text" },
    { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search requirements..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "category", label: "Category", type: "text" },
    { key: "regulatory_reference", label: "Regulatory Reference", type: "text" },
    { key: "renewal_frequency", label: "Renewal Frequency", type: "text" },
    { key: "is_mandatory", label: "Mandatory", type: "boolean", defaultValue: true },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
