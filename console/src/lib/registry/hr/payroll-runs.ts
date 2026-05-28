import { registerResource } from "../index";

registerResource({
  key: "payroll-runs",
  module: "hr",
  label: "Payroll Run",
  labelPlural: "Payroll Runs",
  endpoint: "/hr/payroll-runs/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "period_start", label: "Period Start", type: "date", sortable: true },
    { key: "period_end", label: "Period End", type: "date" },
    { key: "status", label: "Status", type: "badge" },
    { key: "total_gross", label: "Total Gross", type: "currency" },
    { key: "total_deductions", label: "Total Deductions", type: "currency" },
    { key: "total_net", label: "Total Net", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search payroll runs..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PROCESSING", label: "Processing" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "period_start", label: "Period Start", type: "date", required: true },
    { key: "period_end", label: "Period End", type: "date", required: true },
    { key: "run_date", label: "Run Date", type: "date" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PROCESSING", label: "Processing" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
