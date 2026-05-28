import { registerResource } from "../index";

registerResource({
  key: "retention-policies",
  module: "documents",
  label: "Retention Policy",
  labelPlural: "Retention Policies",
  endpoint: "/documents/control/lookups/retention-policies/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "retention_years", label: "Retention Years", type: "number" },
    { key: "is_indefinite", label: "Indefinite", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search retention policies..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "retention_years", label: "Retention Years", type: "number" },
    { key: "is_indefinite", label: "Indefinite", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
