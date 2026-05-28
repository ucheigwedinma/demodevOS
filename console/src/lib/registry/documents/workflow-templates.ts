import { registerResource } from "../index";

registerResource({
  key: "workflow-templates",
  module: "documents",
  label: "Workflow Template",
  labelPlural: "Workflow Templates",
  endpoint: "/documents/control/workflow/templates/",
  columns: [
    { key: "code", label: "Code", type: "text" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "updated_at", label: "Updated", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search workflow templates..." },
  ],
  formFields: [
    { key: "code", label: "Code", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
