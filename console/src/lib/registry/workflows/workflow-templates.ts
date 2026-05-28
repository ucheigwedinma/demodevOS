import { registerResource } from "../index";

registerResource({
  key: "workflow-templates",
  module: "workflows",
  label: "Workflow Template",
  labelPlural: "Workflow Templates",
  endpoint: "/workflows/templates/",
  columns: [
    { key: "code", label: "Code", type: "text", sortable: true },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "default_step_mode", label: "Step Mode", type: "text" },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "code", label: "Code", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "default_step_mode",
      label: "Default Step Mode",
      type: "select",
      options: [
        { value: "SEQUENTIAL", label: "Sequential" },
        { value: "PARALLEL", label: "Parallel" },
      ],
    },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
