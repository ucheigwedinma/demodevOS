import { registerResource } from "../index";

registerResource({
  key: "master-data",
  module: "settings",
  label: "Master Data Entry",
  labelPlural: "Master Data",
  endpoint: "/settings/master-data/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "category", label: "Category", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "label", label: "Label", type: "text", sortable: true },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "is_system", label: "System", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search master data..." },
    { key: "category", label: "Category", type: "select", optionsEndpoint: "/settings/master-data/categories/" },
  ],
  formFields: [
    { key: "category", label: "Category", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "label", label: "Label", type: "text", required: true },
    { key: "sort_order", label: "Sort Order", type: "number", defaultValue: 0 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
