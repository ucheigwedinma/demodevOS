import { registerResource } from "../index";

registerResource({
  key: "deductions",
  module: "hr",
  label: "Deduction",
  labelPlural: "Deductions",
  endpoint: "/hr/deductions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "deduction_type", label: "Type", type: "badge" },
    { key: "amount", label: "Amount", type: "currency" },
    { key: "frequency", label: "Frequency", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search deductions..." },
    {
      key: "deduction_type",
      label: "Type",
      type: "select",
      options: [
        { value: "TAX", label: "Tax" },
        { value: "INSURANCE", label: "Insurance" },
        { value: "PENSION", label: "Pension" },
        { value: "LOAN", label: "Loan" },
        { value: "UNION", label: "Union" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "deduction_type",
      label: "Type",
      type: "select",
      options: [
        { value: "TAX", label: "Tax" },
        { value: "INSURANCE", label: "Insurance" },
        { value: "PENSION", label: "Pension" },
        { value: "LOAN", label: "Loan" },
        { value: "UNION", label: "Union" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "amount", label: "Amount", type: "currency", required: true },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    {
      key: "frequency",
      label: "Frequency",
      type: "select",
      options: [
        { value: "MONTHLY", label: "Monthly" },
        { value: "QUARTERLY", label: "Quarterly" },
        { value: "ANNUALLY", label: "Annually" },
        { value: "ONE_TIME", label: "One Time" },
      ],
    },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
