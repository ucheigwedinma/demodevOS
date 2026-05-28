import { registerResource } from "../index";

registerResource({
  key: "generation-records",
  module: "documents",
  label: "Generated Document",
  labelPlural: "Generated Documents",
  endpoint: "/documents/control/generation/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "generation_kind", label: "Generation Kind", type: "badge" },
    { key: "document", label: "Document", type: "text" },
    { key: "template_code", label: "Template Code", type: "text" },
    { key: "requested_by", label: "Requested By", type: "text" },
    { key: "created_at", label: "Created", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search generated documents..." },
    {
      key: "generation_kind",
      label: "Generation Kind",
      type: "select",
      options: [
        { value: "CONTRACT", label: "Contract" },
        { value: "INVOICE", label: "Invoice" },
        { value: "REPORT", label: "Report" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
