import { registerResource } from "../index";

registerResource({
  key: "hiring-funnel-metrics",
  module: "hr",
  label: "Hiring Funnel",
  labelPlural: "Hiring Funnels",
  endpoint: "/hr/hiring-funnel-metrics/",
  columns: [
    { key: "period_start", label: "Period Start", type: "date" },
    { key: "period_end", label: "Period End", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "applications_received", label: "Applications Received", type: "number" },
    { key: "candidates_interviewed", label: "Candidates Interviewed", type: "number" },
    { key: "offers_made", label: "Offers Made", type: "number" },
    { key: "offers_accepted", label: "Offers Accepted", type: "number" },
    { key: "avg_time_to_hire_days", label: "Avg Time to Hire (Days)", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
