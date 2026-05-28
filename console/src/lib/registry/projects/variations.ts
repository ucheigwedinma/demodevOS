import { registerResource } from "../index";

registerResource({
  key: "variations",
  module: "projects",
  label: "Variation Order",
  labelPlural: "Variation Orders",
  endpoint: "/projects/variations/",
  columns: [
    { key: "variation_number", label: "Variation #", type: "text", sortable: true },
    { key: "project", label: "Project", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "contract_value", label: "Contract Value", type: "currency" },
    { key: "requested_date", label: "Requested Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search variation orders..." },
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
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "title", label: "Title", type: "text", required: true },
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
    { key: "contract_value", label: "Contract Value", type: "currency" },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    { key: "requested_date", label: "Requested Date", type: "date" },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "change_summary", label: "Change Summary", type: "textarea", gridSpan: 2 },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
