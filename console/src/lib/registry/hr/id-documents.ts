import { registerResource } from "../index";

registerResource({
  key: "id-documents",
  module: "hr",
  label: "ID Document",
  labelPlural: "ID Documents",
  endpoint: "/hr/id-documents/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "document_type", label: "Document Type", type: "text" },
    { key: "document_number", label: "Document Number", type: "text" },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search ID documents..." },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "document_type", label: "Document Type", type: "text", required: true },
    { key: "document_number", label: "Document Number", type: "text", required: true },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "issuing_country", label: "Issuing Country", type: "text" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
