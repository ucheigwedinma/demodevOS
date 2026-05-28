import { registerResource } from "../index";

registerResource({
  key: "domains",
  module: "documents",
  label: "Document Domain",
  labelPlural: "Document Domains",
  endpoint: "/documents/domains/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "sort_order", label: "Sort Order", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search document domains..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "code",
      label: "Code",
      type: "select",
      options: [
        { value: "LAND_TITLE", label: "Land Title" },
        { value: "REGULATORY_STATUTORY", label: "Regulatory Statutory" },
        { value: "DESIGN_ENGINEERING", label: "Design Engineering" },
        { value: "CONSTRUCTION_VENDOR", label: "Construction Vendor" },
        { value: "SALES_CLIENT", label: "Sales Client" },
        { value: "FINANCE_COMMERCIAL", label: "Finance Commercial" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "sort_order", label: "Sort Order", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
