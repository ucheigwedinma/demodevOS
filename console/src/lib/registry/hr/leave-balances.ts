import { registerResource } from "../index";

registerResource({
  key: "leave-balances",
  module: "hr",
  label: "Leave Balance",
  labelPlural: "Leave Balances",
  endpoint: "/hr/leave-balances/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "leave_type", label: "Leave Type", type: "text" },
    { key: "fiscal_year", label: "Fiscal Year", type: "number" },
    { key: "entitled_days", label: "Entitled", type: "number" },
    { key: "used_days", label: "Used", type: "number" },
    { key: "pending_days", label: "Pending", type: "number" },
    { key: "carried_over", label: "Carried Over", type: "number" },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "leave_type", label: "Leave Type", type: "relation_picker", required: true, optionsEndpoint: "/hr/leave-types/" },
    { key: "fiscal_year", label: "Fiscal Year", type: "number", required: true },
    { key: "entitled_days", label: "Entitled Days", type: "number" },
    { key: "carried_over", label: "Carried Over", type: "number" },
    { key: "adjustment", label: "Adjustment", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
