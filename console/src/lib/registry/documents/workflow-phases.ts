import { registerResource } from "../index";

registerResource({
  key: "workflow-phases",
  module: "documents",
  label: "Workflow Phase",
  labelPlural: "Workflow Phases",
  endpoint: "/documents/control/lookups/workflow-phases/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "numbering_code", label: "Numbering Code", type: "text" },
    { key: "sort_order", label: "Sort Order", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search workflow phases..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "numbering_code", label: "Numbering Code", type: "text" },
    { key: "sort_order", label: "Sort Order", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
