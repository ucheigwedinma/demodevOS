import { registerResource } from "../index";

registerResource({
  key: "position-budgets",
  module: "hr",
  label: "Position Budget",
  labelPlural: "Position Budgets",
  endpoint: "/hr/position-budgets/",
  columns: [
    { key: "department", label: "Department", type: "text" },
    { key: "position", label: "Position", type: "text" },
    { key: "fiscal_year", label: "Fiscal Year", type: "number" },
    { key: "approved_headcount", label: "Approved Headcount", type: "number" },
    { key: "filled_headcount", label: "Filled Headcount", type: "number" },
    { key: "budget_amount", label: "Budget Amount", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search budgets..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "APPROVED", label: "Approved" },
        { value: "FROZEN", label: "Frozen" },
      ],
    },
    { key: "fiscal_year", label: "Fiscal Year", type: "search", placeholder: "Fiscal year..." },
  ],
  formFields: [
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "position", label: "Position", type: "relation_picker", optionsEndpoint: "/hr/positions/" },
    { key: "fiscal_year", label: "Fiscal Year", type: "number", required: true },
    { key: "approved_headcount", label: "Approved Headcount", type: "number" },
    { key: "filled_headcount", label: "Filled Headcount", type: "number" },
    { key: "budget_amount", label: "Budget Amount", type: "currency" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "APPROVED", label: "Approved" },
        { value: "FROZEN", label: "Frozen" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
