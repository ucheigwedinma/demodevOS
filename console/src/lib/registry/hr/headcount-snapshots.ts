import { registerResource } from "../index";

registerResource({
  key: "headcount-snapshots",
  module: "hr",
  label: "Headcount Snapshot",
  labelPlural: "Headcount Snapshots",
  endpoint: "/hr/headcount-snapshots/",
  columns: [
    { key: "snapshot_date", label: "Snapshot Date", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "active_count", label: "Active Count", type: "number" },
    { key: "new_hires", label: "New Hires", type: "number" },
    { key: "departures", label: "Departures", type: "number" },
    { key: "contractors", label: "Contractors", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "snapshot_date", label: "Snapshot Date", type: "date", required: true },
    { key: "department", label: "Department", type: "text", required: true },
    { key: "team", label: "Team", type: "text" },
    { key: "active_count", label: "Active Count", type: "number" },
    { key: "inactive_count", label: "Inactive Count", type: "number" },
    { key: "new_hires", label: "New Hires", type: "number" },
    { key: "departures", label: "Departures", type: "number" },
    { key: "contractors", label: "Contractors", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canEdit: false,
  canDelete: false,
});
