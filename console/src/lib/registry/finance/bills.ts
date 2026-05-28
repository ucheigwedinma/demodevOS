import { registerResource } from "../index";

registerResource({
  key: "bills",
  module: "finance",
  label: "Bill",
  labelPlural: "Bills",
  endpoint: "/finance/bills/",
  columns: [
    { key: "bill_number", label: "Bill Number", type: "text", sortable: true },
    { key: "vendor", label: "Vendor", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "issue_date", label: "Issue Date", type: "date", sortable: true },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "total_amount", label: "Total Amount", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search bills..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "APPROVED", label: "Approved" },
        { value: "PAID", label: "Paid" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "vendor", label: "Vendor", type: "relation_picker", required: true, optionsEndpoint: "/procurement/vendors/" },
    { key: "issue_date", label: "Issue Date", type: "date", required: true },
    { key: "due_date", label: "Due Date", type: "date", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "APPROVED", label: "Approved" },
        { value: "PAID", label: "Paid" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
