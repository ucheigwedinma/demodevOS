import { registerResource } from "../index";

registerResource({
  key: "signature-requests",
  module: "documents",
  label: "Signature Request",
  labelPlural: "Signature Requests",
  endpoint: "/documents/control/signatures/",
  columns: [
    { key: "document", label: "Document", type: "text" },
    { key: "provider", label: "Provider", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "requested_at", label: "Requested At", type: "datetime" },
    { key: "sent_at", label: "Sent At", type: "datetime" },
    { key: "completed_at", label: "Completed At", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search signature requests..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SENT", label: "Sent" },
        { value: "COMPLETED", label: "Completed" },
        { value: "DECLINED", label: "Declined" },
        { value: "CANCELLED", label: "Cancelled" },
        { value: "FAILED", label: "Failed" },
      ],
    },
    {
      key: "provider",
      label: "Provider",
      type: "select",
      options: [
        { value: "DOCUSIGN", label: "DocuSign" },
        { value: "ADOBE_ACROBAT_SIGN", label: "Adobe Acrobat Sign" },
        { value: "DROPBOX_SIGN", label: "Dropbox Sign" },
        { value: "SIGNNOW", label: "SignNow" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
