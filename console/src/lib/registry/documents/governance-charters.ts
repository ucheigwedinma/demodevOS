import { registerResource } from "../index";

registerResource({
  key: "governance-charters",
  module: "documents",
  label: "Governance Charter",
  labelPlural: "Governance Charters",
  endpoint: "/documents/charters/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "version", label: "Version", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "repository_scope", label: "Repository Scope", type: "text" },
    { key: "approved_by", label: "Approved By", type: "text" },
    { key: "approved_at", label: "Approved At", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search governance charters..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "SUPERSEDED", label: "Superseded" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "version", label: "Version", type: "text", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "SUPERSEDED", label: "Superseded" },
      ],
    },
    {
      key: "repository_scope",
      label: "Repository Scope",
      type: "select",
      options: [
        { value: "FORMAL_ONLY", label: "Formal Only" },
        { value: "FORMAL_AND_SITE_PHOTOS", label: "Formal and Site Photos" },
      ],
    },
    {
      key: "external_portal_access",
      label: "External Portal Access",
      type: "select",
      options: [
        { value: "NOT_INCLUDED", label: "Not Included" },
        { value: "READ_ONLY", label: "Read Only" },
        { value: "COLLABORATION", label: "Collaboration" },
      ],
    },
    { key: "includes_digital_signature_v1", label: "Includes Digital Signature v1", type: "boolean" },
    { key: "approved_by", label: "Approved By", type: "text" },
    { key: "approved_at", label: "Approved At", type: "date" },
    { key: "review_due_at", label: "Review Due At", type: "date" },
    { key: "scope_notes", label: "Scope Notes", type: "textarea", gridSpan: 2 },
  ],
});
