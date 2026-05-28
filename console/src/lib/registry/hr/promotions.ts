import { registerResource } from "../index";

registerResource({
  key: "promotions",
  module: "hr",
  label: "Promotion",
  labelPlural: "Promotions",
  endpoint: "/hr/promotions/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "from_position", label: "From Position", type: "text" },
    { key: "to_position", label: "To Position", type: "text" },
    { key: "effective_date", label: "Effective Date", type: "date" },
    { key: "salary_adjustment", label: "Salary Adjustment", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "EFFECTIVE", label: "Effective" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "from_position", label: "From Position", type: "text" },
    { key: "to_position", label: "To Position", type: "text", required: true },
    { key: "from_grade", label: "From Grade", type: "text" },
    { key: "to_grade", label: "To Grade", type: "text" },
    { key: "effective_date", label: "Effective Date", type: "date", required: true },
    { key: "salary_adjustment", label: "Salary Adjustment", type: "currency" },
    { key: "new_salary", label: "New Salary", type: "currency" },
    { key: "status", label: "Status", type: "select", options: [
      { value: "PENDING", label: "Pending" },
      { value: "APPROVED", label: "Approved" },
      { value: "EFFECTIVE", label: "Effective" },
      { value: "CANCELLED", label: "Cancelled" },
    ]},
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
