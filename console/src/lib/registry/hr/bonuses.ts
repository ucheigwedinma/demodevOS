import { registerResource } from "../index";

registerResource({
  key: "bonuses",
  module: "hr",
  label: "Bonus",
  labelPlural: "Bonuses",
  endpoint: "/hr/bonuses/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "bonus_type", label: "Type", type: "badge" },
    { key: "amount", label: "Amount", type: "currency" },
    { key: "date", label: "Date", type: "date", sortable: true },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search bonuses..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "PAID", label: "Paid" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "bonus_type",
      label: "Type",
      type: "select",
      options: [
        { value: "PERFORMANCE", label: "Performance" },
        { value: "ANNUAL", label: "Annual" },
        { value: "SIGNING", label: "Signing" },
        { value: "REFERRAL", label: "Referral" },
        { value: "PROJECT", label: "Project" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    {
      key: "bonus_type",
      label: "Type",
      type: "select",
      options: [
        { value: "PERFORMANCE", label: "Performance" },
        { value: "ANNUAL", label: "Annual" },
        { value: "SIGNING", label: "Signing" },
        { value: "REFERRAL", label: "Referral" },
        { value: "PROJECT", label: "Project" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "amount", label: "Amount", type: "currency", required: true },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    { key: "date", label: "Date", type: "date", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "PAID", label: "Paid" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
