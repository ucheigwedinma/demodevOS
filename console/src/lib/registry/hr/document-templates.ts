import { registerResource } from "../index";

registerResource({
  key: "document-templates",
  module: "hr",
  label: "Document Template",
  labelPlural: "Document Templates",
  endpoint: "/hr/document-templates/",
  columns: [
    { key: "title", label: "Title", type: "text" },
    { key: "category", label: "Category", type: "badge" },
    { key: "version", label: "Version", type: "text" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "DRAFT", label: "Draft" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "OFFER_LETTER", label: "Offer Letter" },
        { value: "CONTRACT", label: "Contract" },
        { value: "WARNING_LETTER", label: "Warning Letter" },
        { value: "TERMINATION", label: "Termination" },
        { value: "PROMOTION", label: "Promotion" },
        { value: "TRANSFER", label: "Transfer" },
        { value: "GENERAL", label: "General" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "category", label: "Category", type: "select", options: [
      { value: "OFFER_LETTER", label: "Offer Letter" },
      { value: "CONTRACT", label: "Contract" },
      { value: "WARNING_LETTER", label: "Warning Letter" },
      { value: "TERMINATION", label: "Termination" },
      { value: "PROMOTION", label: "Promotion" },
      { value: "TRANSFER", label: "Transfer" },
      { value: "GENERAL", label: "General" },
      { value: "OTHER", label: "Other" },
    ]},
    { key: "version", label: "Version", type: "text" },
    { key: "status", label: "Status", type: "select", options: [
      { value: "ACTIVE", label: "Active" },
      { value: "DRAFT", label: "Draft" },
      { value: "ARCHIVED", label: "Archived" },
    ]},
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "content", label: "Content", type: "textarea", gridSpan: 2 },
  ],
});
