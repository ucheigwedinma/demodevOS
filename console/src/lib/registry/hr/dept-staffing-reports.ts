import { registerResource } from "../index";

registerResource({
  key: "dept-staffing-reports",
  module: "hr",
  label: "Staffing Report",
  labelPlural: "Staffing Reports",
  endpoint: "/hr/dept-staffing-reports/",
  columns: [
    { key: "report_date", label: "Report Date", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "budgeted_positions", label: "Budgeted Positions", type: "number" },
    { key: "filled_positions", label: "Filled Positions", type: "number" },
    { key: "vacant_positions", label: "Vacant Positions", type: "number" },
    { key: "pending_hires", label: "Pending Hires", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "report_date", label: "Report Date", type: "date", required: true },
    { key: "department", label: "Department", type: "text", required: true },
    { key: "budgeted_positions", label: "Budgeted Positions", type: "number" },
    { key: "filled_positions", label: "Filled Positions", type: "number" },
    { key: "vacant_positions", label: "Vacant Positions", type: "number" },
    { key: "pending_hires", label: "Pending Hires", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canEdit: false,
  canDelete: false,
});
