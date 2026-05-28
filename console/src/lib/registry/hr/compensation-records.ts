import { registerResource } from "../index";

registerResource({
  key: "compensation-records",
  module: "hr",
  label: "Compensation Record",
  labelPlural: "Compensation Records",
  endpoint: "/hr/compensation-records/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "effective_date", label: "Effective Date", type: "date", sortable: true },
    { key: "base_salary", label: "Base Salary", type: "currency" },
    { key: "total_package", label: "Total Package", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
    { key: "pay_frequency", label: "Pay Frequency", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search compensation records..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "SUPERSEDED", label: "Superseded" },
      ],
    },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "effective_date", label: "Effective Date", type: "date", required: true },
    { key: "base_salary", label: "Base Salary", type: "currency", required: true },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    {
      key: "pay_frequency",
      label: "Pay Frequency",
      type: "select",
      options: [
        { value: "MONTHLY", label: "Monthly" },
        { value: "BIWEEKLY", label: "Biweekly" },
        { value: "WEEKLY", label: "Weekly" },
        { value: "ANNUAL", label: "Annual" },
      ],
    },
    { key: "allowances", label: "Allowances", type: "currency" },
    { key: "bonus", label: "Bonus", type: "currency" },
    { key: "total_package", label: "Total Package", type: "currency" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "SUPERSEDED", label: "Superseded" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
