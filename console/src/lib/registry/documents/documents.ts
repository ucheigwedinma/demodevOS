import { registerResource } from "../index";

registerResource({
  key: "documents",
  module: "documents",
  label: "Document",
  labelPlural: "Documents",
  endpoint: "/documents/control/records/",
  columns: [
    { key: "document_number", label: "Document Number", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "document_type", label: "Document Type", type: "text" },
    { key: "confidentiality_level", label: "Confidentiality Level", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "phase", label: "Phase", type: "text" },
    { key: "created_at", label: "Created", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search documents..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "UNDER_REVIEW", label: "Under Review" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "SUPERSEDED", label: "Superseded" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "confidentiality_level",
      label: "Confidentiality Level",
      type: "select",
      options: [
        { value: "PUBLIC", label: "Public" },
        { value: "INTERNAL", label: "Internal" },
        { value: "CONFIDENTIAL", label: "Confidential" },
        { value: "RESTRICTED", label: "Restricted" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "document_type", label: "Document Type", type: "relation_picker", optionsEndpoint: "/documents/control/lookups/document-types/" },
    {
      key: "confidentiality_level",
      label: "Confidentiality Level",
      type: "select",
      options: [
        { value: "PUBLIC", label: "Public" },
        { value: "INTERNAL", label: "Internal" },
        { value: "CONFIDENTIAL", label: "Confidential" },
        { value: "RESTRICTED", label: "Restricted" },
      ],
    },
    { key: "owner_role", label: "Owner Role", type: "relation_picker", optionsEndpoint: "/documents/control/lookups/owner-roles/" },
    { key: "phase", label: "Phase", type: "relation_picker", optionsEndpoint: "/documents/control/lookups/workflow-phases/" },
    { key: "retention_policy", label: "Retention Policy", type: "relation_picker", optionsEndpoint: "/documents/control/lookups/retention-policies/" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "contract_value", label: "Contract Value", type: "currency" },
  ],
});
