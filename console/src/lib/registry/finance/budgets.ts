import { registerResource } from "../index";

registerResource({
  key: "budgets",
  module: "finance",
  label: "Budget",
  labelPlural: "Budgets",
  endpoint: "/finance/budgets/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "period_type", label: "Period Type", type: "text" },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "end_date", label: "End Date", type: "date", sortable: true },
    { key: "total_amount", label: "Total Amount", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search budgets..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    {
      key: "period_type",
      label: "Period Type",
      type: "select",
      options: [
        { value: "ANNUAL", label: "Annual" },
        { value: "QUARTERLY", label: "Quarterly" },
        { value: "MONTHLY", label: "Monthly" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "period_type",
      label: "Period Type",
      type: "select",
      options: [
        { value: "ANNUAL", label: "Annual" },
        { value: "QUARTERLY", label: "Quarterly" },
        { value: "MONTHLY", label: "Monthly" },
      ],
    },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date", required: true },
    { key: "total_amount", label: "Total Amount", type: "currency" },
    { key: "overspend_tolerance_pct", label: "Overspend Tolerance %", type: "number" },
    { key: "warning_threshold_pct", label: "Warning Threshold %", type: "number" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
