import { registerResource } from "../index";

registerResource({
  key: "workflow-rules",
  module: "documents",
  label: "Workflow Rule",
  labelPlural: "Workflow Rules",
  endpoint: "/documents/control/workflow/rules/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "template", label: "Template", type: "text" },
    { key: "document_type", label: "Document Type", type: "text" },
    { key: "min_contract_value", label: "Min Contract Value", type: "currency" },
    { key: "max_contract_value", label: "Max Contract Value", type: "currency" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search workflow rules..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "template", label: "Template", type: "relation_picker", required: true, optionsEndpoint: "/documents/control/workflow/templates/" },
    { key: "document_type", label: "Document Type", type: "relation_picker", optionsEndpoint: "/documents/control/lookups/document-types/" },
    { key: "min_contract_value", label: "Min Contract Value", type: "currency" },
    { key: "max_contract_value", label: "Max Contract Value", type: "currency" },
    { key: "priority", label: "Priority", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
