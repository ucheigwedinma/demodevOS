import { registerResource } from "../index";

registerResource({
  key: "workforce-logs",
  module: "projects",
  label: "Workforce Log",
  labelPlural: "Workforce Logs",
  endpoint: "/projects/field-operations/workforce/",
  columns: [
    { key: "project", label: "Project", type: "text" },
    { key: "report_date", label: "Report Date", type: "date", sortable: true },
    { key: "shift", label: "Shift", type: "badge" },
    { key: "laborers_count", label: "Laborers", type: "number" },
    { key: "skilled_count", label: "Skilled", type: "number" },
    { key: "supervisors_count", label: "Supervisors", type: "number" },
    { key: "subcontractors_count", label: "Subcontractors", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search workforce logs..." },
    {
      key: "shift",
      label: "Shift",
      type: "select",
      options: [
        { value: "DAY", label: "Day" },
        { value: "NIGHT", label: "Night" },
        { value: "FULL_DAY", label: "Full Day" },
      ],
    },
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "report_date", label: "Report Date", type: "date", required: true },
    {
      key: "shift",
      label: "Shift",
      type: "select",
      options: [
        { value: "DAY", label: "Day" },
        { value: "NIGHT", label: "Night" },
        { value: "FULL_DAY", label: "Full Day" },
      ],
    },
    { key: "laborers_count", label: "Laborers Count", type: "number" },
    { key: "skilled_count", label: "Skilled Count", type: "number" },
    { key: "supervisors_count", label: "Supervisors Count", type: "number" },
    { key: "subcontractors_count", label: "Subcontractors Count", type: "number" },
    { key: "equipment_operators_count", label: "Equipment Operators Count", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
