import { registerResource } from "../index";

registerResource({
  key: "tax-records",
  module: "hr",
  label: "Tax Record",
  labelPlural: "Tax Records",
  endpoint: "/hr/tax-records/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "fiscal_year", label: "Fiscal Year", type: "text" },
    { key: "tax_type", label: "Tax Type", type: "badge" },
    { key: "taxable_income", label: "Taxable Income", type: "currency" },
    { key: "tax_amount", label: "Tax Amount", type: "currency" },
    { key: "tax_paid", label: "Tax Paid", type: "currency" },
    { key: "filing_status", label: "Filing Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search tax records..." },
    {
      key: "filing_status",
      label: "Filing Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "FILED", label: "Filed" },
        { value: "ASSESSED", label: "Assessed" },
        { value: "PAID", label: "Paid" },
      ],
    },
    {
      key: "tax_type",
      label: "Tax Type",
      type: "select",
      options: [
        { value: "INCOME_TAX", label: "Income Tax" },
        { value: "SOCIAL_SECURITY", label: "Social Security" },
        { value: "MUNICIPAL", label: "Municipal" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "fiscal_year", label: "Fiscal Year", type: "text", required: true },
    {
      key: "tax_type",
      label: "Tax Type",
      type: "select",
      options: [
        { value: "INCOME_TAX", label: "Income Tax" },
        { value: "SOCIAL_SECURITY", label: "Social Security" },
        { value: "MUNICIPAL", label: "Municipal" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "taxable_income", label: "Taxable Income", type: "currency" },
    { key: "tax_amount", label: "Tax Amount", type: "currency" },
    { key: "tax_paid", label: "Tax Paid", type: "currency" },
    {
      key: "filing_status",
      label: "Filing Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "FILED", label: "Filed" },
        { value: "ASSESSED", label: "Assessed" },
        { value: "PAID", label: "Paid" },
      ],
    },
    { key: "filed_date", label: "Filed Date", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
