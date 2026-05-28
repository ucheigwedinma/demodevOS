import { registerResource } from "../index";

registerResource({
  key: "orientation-checklists",
  module: "hr",
  label: "Orientation Checklist",
  labelPlural: "Orientation Checklists",
  endpoint: "/hr/orientation-checklists/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "category", label: "Category", type: "badge" },
    { key: "is_completed", label: "Completed", type: "boolean" },
    { key: "completed_date", label: "Completed Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "COMPANY_OVERVIEW", label: "Company Overview" },
        { value: "TEAM_INTRODUCTION", label: "Team Introduction" },
        { value: "SYSTEM_TRAINING", label: "System Training" },
        { value: "SAFETY_TRAINING", label: "Safety Training" },
        { value: "POLICY_REVIEW", label: "Policy Review" },
        { value: "FACILITY_TOUR", label: "Facility Tour" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "category", label: "Category", type: "select", options: [
        { value: "COMPANY_OVERVIEW", label: "Company Overview" },
        { value: "TEAM_INTRODUCTION", label: "Team Introduction" },
        { value: "SYSTEM_TRAINING", label: "System Training" },
        { value: "SAFETY_TRAINING", label: "Safety Training" },
        { value: "POLICY_REVIEW", label: "Policy Review" },
        { value: "FACILITY_TOUR", label: "Facility Tour" },
      ],
    },
    { key: "is_completed", label: "Completed", type: "boolean" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
