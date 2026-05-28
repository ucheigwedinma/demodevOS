import { registerResource } from "../index";

registerResource({
  key: "compliance-documents",
  module: "hr",
  label: "Compliance Document",
  labelPlural: "Compliance Documents",
  endpoint: "/hr/compliance-documents/",
  columns: [
    { key: "title", label: "Title", type: "text" },
    { key: "document_type", label: "Document Type", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "reference_number", label: "Reference Number", type: "text" },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "CURRENT", label: "Current" },
        { value: "EXPIRED", label: "Expired" },
        { value: "PENDING_REVIEW", label: "Pending Review" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "document_type",
      label: "Document Type",
      type: "select",
      options: [
        { value: "REGULATION", label: "Regulation" },
        { value: "CERTIFICATION", label: "Certification" },
        { value: "AUDIT_REPORT", label: "Audit Report" },
        { value: "LEGAL", label: "Legal" },
        { value: "POLICY", label: "Policy" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "document_type", label: "Document Type", type: "select", options: [
      { value: "REGULATION", label: "Regulation" },
      { value: "CERTIFICATION", label: "Certification" },
      { value: "AUDIT_REPORT", label: "Audit Report" },
      { value: "LEGAL", label: "Legal" },
      { value: "POLICY", label: "Policy" },
      { value: "OTHER", label: "Other" },
    ]},
    { key: "reference_number", label: "Reference Number", type: "text" },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    { key: "status", label: "Status", type: "select", options: [
      { value: "CURRENT", label: "Current" },
      { value: "EXPIRED", label: "Expired" },
      { value: "PENDING_REVIEW", label: "Pending Review" },
      { value: "ARCHIVED", label: "Archived" },
    ]},
    { key: "department", label: "Department", type: "text" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
