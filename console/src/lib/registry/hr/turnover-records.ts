import { registerResource } from "../index";

registerResource({
  key: "turnover-records",
  module: "hr",
  label: "Turnover Record",
  labelPlural: "Turnover Records",
  endpoint: "/hr/turnover-records/",
  columns: [
    { key: "period_start", label: "Period Start", type: "date" },
    { key: "period_end", label: "Period End", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "starting_headcount", label: "Starting Headcount", type: "number" },
    { key: "ending_headcount", label: "Ending Headcount", type: "number" },
    { key: "voluntary_departures", label: "Voluntary Departures", type: "number" },
    { key: "involuntary_departures", label: "Involuntary Departures", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "period_start", label: "Period Start", type: "date", required: true },
    { key: "period_end", label: "Period End", type: "date", required: true },
    { key: "department", label: "Department", type: "text", required: true },
    { key: "starting_headcount", label: "Starting Headcount", type: "number" },
    { key: "ending_headcount", label: "Ending Headcount", type: "number" },
    { key: "voluntary_departures", label: "Voluntary Departures", type: "number" },
    { key: "involuntary_departures", label: "Involuntary Departures", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canEdit: false,
  canDelete: false,
});
