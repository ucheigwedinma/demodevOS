import { registerResource } from "../index";

registerResource({
  key: "rfqs",
  module: "procurement",
  label: "Request for Quotation",
  labelPlural: "Requests for Quotation",
  endpoint: "/procurement/rfqs/",
  columns: [
    { key: "rfq_number", label: "RFQ Number", type: "text", sortable: true },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "issue_date", label: "Issue Date", type: "date", sortable: true },
    { key: "submission_deadline", label: "Submission Deadline", type: "date" },
    { key: "estimated_value", label: "Estimated Value", type: "currency" },
    { key: "selected_vendor", label: "Selected Vendor", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search RFQs..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ISSUED", label: "Issued" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "EVALUATING", label: "Evaluating" },
        { value: "AWARDED", label: "Awarded" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "requisition", label: "Requisition", type: "relation_picker", optionsEndpoint: "/procurement/requisitions/" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "submission_deadline", label: "Submission Deadline", type: "date" },
    { key: "estimated_value", label: "Estimated Value", type: "currency" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ISSUED", label: "Issued" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "EVALUATING", label: "Evaluating" },
        { value: "AWARDED", label: "Awarded" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
