import { registerResource } from "../index";

registerResource({
  key: "payslips",
  module: "hr",
  label: "Payslip",
  labelPlural: "Payslips",
  endpoint: "/hr/payslips/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "period_start", label: "Period Start", type: "date", sortable: true },
    { key: "period_end", label: "Period End", type: "date" },
    { key: "gross_salary", label: "Gross Salary", type: "currency" },
    { key: "total_deductions", label: "Deductions", type: "currency" },
    { key: "net_salary", label: "Net Salary", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search payslips..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "GENERATED", label: "Generated" },
        { value: "SENT", label: "Sent" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
