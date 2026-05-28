import { registerResource } from "../index";

registerResource({
  key: "vocabulary-terms",
  module: "documents",
  label: "Vocabulary Term",
  labelPlural: "Vocabulary Terms",
  endpoint: "/documents/vocabulary-terms/",
  columns: [
    { key: "term", label: "Term", type: "text", sortable: true },
    { key: "term_key", label: "Term Key", type: "text" },
    { key: "domain", label: "Domain", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "is_required", label: "Required", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search vocabulary terms..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "DEPRECATED", label: "Deprecated" },
      ],
    },
  ],
  formFields: [
    { key: "domain", label: "Domain", type: "relation_picker", required: true, optionsEndpoint: "/documents/domains/" },
    { key: "term", label: "Term", type: "text", required: true },
    { key: "term_key", label: "Term Key", type: "text", required: true },
    { key: "definition", label: "Definition", type: "textarea", gridSpan: 2 },
    { key: "usage_guidance", label: "Usage Guidance", type: "textarea", gridSpan: 2 },
    { key: "synonyms", label: "Synonyms", type: "text" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "DEPRECATED", label: "Deprecated" },
      ],
    },
    { key: "is_required", label: "Required", type: "boolean" },
  ],
});
