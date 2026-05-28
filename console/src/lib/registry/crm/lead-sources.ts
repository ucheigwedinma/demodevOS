import { registerResource } from "../index";

registerResource({
  key: "lead-sources",
  module: "crm",
  label: "Lead Source",
  labelPlural: "Lead Sources",
  endpoint: "/crm/sources/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search lead sources..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
