import { registerResource } from "../index";

registerResource({
  key: "position-assignments",
  module: "hr",
  label: "Position Assignment",
  labelPlural: "Position Assignments",
  endpoint: "/hr/position-assignments/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "position", label: "Position", type: "text" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "is_primary", label: "Primary", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search assignments..." },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "position", label: "Position", type: "relation_picker", required: true, optionsEndpoint: "/hr/positions/" },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "is_primary", label: "Primary", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
