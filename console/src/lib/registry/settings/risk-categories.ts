import { registerResource } from "../index";

registerResource({
  key: "risk-categories",
  module: "settings",
  label: "Risk Category",
  labelPlural: "Risk Categories",
  endpoint: "/settings/risk-categories/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "category_type", label: "Type", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search risk categories..." },
    {
      key: "category_type",
      label: "Type",
      type: "select",
      options: [
        { value: "financial", label: "Financial" },
        { value: "regulatory", label: "Regulatory" },
        { value: "construction", label: "Construction" },
        { value: "market", label: "Market" },
        { value: "operational", label: "Operational" },
        { value: "environmental", label: "Environmental" },
        { value: "legal", label: "Legal" },
        { value: "technical", label: "Technical" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "category_type",
      label: "Type",
      type: "select",
      required: true,
      options: [
        { value: "financial", label: "Financial" },
        { value: "regulatory", label: "Regulatory" },
        { value: "construction", label: "Construction" },
        { value: "market", label: "Market" },
        { value: "operational", label: "Operational" },
        { value: "environmental", label: "Environmental" },
        { value: "legal", label: "Legal" },
        { value: "technical", label: "Technical" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
