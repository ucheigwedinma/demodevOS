import { registerResource } from "../index";

registerResource({
  key: "journals",
  module: "finance",
  label: "Journal Entry",
  labelPlural: "Journal Entries",
  endpoint: "/finance/journals/",
  columns: [
    { key: "journal_number", label: "Journal #", type: "text", sortable: true },
    { key: "entry_date", label: "Entry Date", type: "date", sortable: true },
    { key: "description", label: "Description", type: "text" },
    { key: "source_type", label: "Source Type", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search journal entries..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "POSTED", label: "Posted" },
        { value: "REVERSED", label: "Reversed" },
      ],
    },
    {
      key: "source_type",
      label: "Source Type",
      type: "select",
      options: [
        { value: "MANUAL", label: "Manual" },
        { value: "BILL", label: "Bill" },
        { value: "INVOICE", label: "Invoice" },
        { value: "PAYMENT", label: "Payment" },
        { value: "ADJUSTMENT", label: "Adjustment" },
        { value: "CLOSING", label: "Closing" },
        { value: "OPENING", label: "Opening" },
      ],
    },
  ],
  formFields: [
    { key: "entry_date", label: "Entry Date", type: "date", required: true },
    { key: "description", label: "Description", type: "text", required: true },
    { key: "reference", label: "Reference", type: "text" },
    {
      key: "source_type",
      label: "Source Type",
      type: "select",
      options: [
        { value: "MANUAL", label: "Manual" },
        { value: "BILL", label: "Bill" },
        { value: "INVOICE", label: "Invoice" },
        { value: "PAYMENT", label: "Payment" },
        { value: "ADJUSTMENT", label: "Adjustment" },
        { value: "CLOSING", label: "Closing" },
        { value: "OPENING", label: "Opening" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "POSTED", label: "Posted" },
        { value: "REVERSED", label: "Reversed" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
