import { registerResource } from "../index";

registerResource({
  key: "profit-centers",
  module: "settings",
  label: "Profit Center",
  labelPlural: "Profit Centers",
  endpoint: "/settings/profit-centers/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "code", label: "Code", type: "text", sortable: true },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search profit centers..." },
  ],
  formFields: [
    { key: "code", label: "Code", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
