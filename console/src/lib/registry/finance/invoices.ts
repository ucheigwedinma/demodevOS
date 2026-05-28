import { registerResource } from "../index";

registerResource({
  key: "invoices",
  module: "finance",
  label: "Invoice",
  labelPlural: "Invoices",
  endpoint: "/finance/invoices/",
  columns: [
    { key: "invoice_number", label: "Invoice Number", type: "text", sortable: true },
    { key: "customer", label: "Customer", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "issue_date", label: "Issue Date", type: "date", sortable: true },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "total_amount", label: "Total Amount", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search invoices..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SENT", label: "Sent" },
        { value: "PAID", label: "Paid" },
        { value: "OVERDUE", label: "Overdue" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "customer", label: "Customer", type: "relation_picker", required: true, optionsEndpoint: "/finance/customers/" },
    { key: "issue_date", label: "Issue Date", type: "date", required: true },
    { key: "due_date", label: "Due Date", type: "date", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SENT", label: "Sent" },
        { value: "PAID", label: "Paid" },
        { value: "OVERDUE", label: "Overdue" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
