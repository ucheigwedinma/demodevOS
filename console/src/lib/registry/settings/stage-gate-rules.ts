import { registerResource } from "../index";

registerResource({
  key: "stage-gate-rules",
  module: "settings",
  label: "Stage-Gate Rule",
  labelPlural: "Stage-Gate Rules",
  endpoint: "/settings/stage-gate-rules/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "stage", label: "Stage", type: "text" },
    { key: "template_name", label: "Template", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search stage-gate rules..." },
    {
      key: "stage",
      label: "Stage",
      type: "select",
      options: [
        { value: "feasibility", label: "Feasibility" },
        { value: "design", label: "Design" },
        { value: "pre_sales", label: "Pre-Sales" },
        { value: "construction_start", label: "Construction Start" },
        { value: "handover", label: "Handover" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "stage",
      label: "Stage",
      type: "select",
      required: true,
      options: [
        { value: "feasibility", label: "Feasibility" },
        { value: "design", label: "Design" },
        { value: "pre_sales", label: "Pre-Sales" },
        { value: "construction_start", label: "Construction Start" },
        { value: "handover", label: "Handover" },
      ],
    },
    { key: "template", label: "Template", type: "relation_picker", optionsEndpoint: "/settings/project-templates/" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
