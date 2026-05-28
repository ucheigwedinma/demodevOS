import { registerResource } from "../index";

registerResource({
  key: "workforce-cost-reports",
  module: "hr",
  label: "Workforce Cost Report",
  labelPlural: "Workforce Cost Reports",
  endpoint: "/hr/workforce-cost-reports/",
  columns: [
    { key: "period_start", label: "Period Start", type: "date" },
    { key: "period_end", label: "Period End", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "total_salary", label: "Total Salary", type: "currency" },
    { key: "total_allowances", label: "Total Allowances", type: "currency" },
    { key: "total_bonuses", label: "Total Bonuses", type: "currency" },
    { key: "headcount", label: "Headcount", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
