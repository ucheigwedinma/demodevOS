import { registerResource } from "../index";

registerResource({
  key: "positions",
  module: "hr",
  label: "Position",
  labelPlural: "Positions",
  endpoint: "/hr/positions/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "department", label: "Department", type: "text" },
    { key: "employment_type", label: "Employment Type", type: "badge" },
    { key: "level", label: "Level", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search positions..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "FILLED", label: "Filled" },
        { value: "FROZEN", label: "Frozen" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    {
      key: "employment_type",
      label: "Employment Type",
      type: "select",
      options: [
        { value: "FULL_TIME", label: "Full Time" },
        { value: "PART_TIME", label: "Part Time" },
        { value: "CONTRACT", label: "Contract" },
        { value: "INTERN", label: "Intern" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "team", label: "Team", type: "relation_picker", optionsEndpoint: "/hr/teams/" },
    {
      key: "employment_type",
      label: "Employment Type",
      type: "select",
      options: [
        { value: "FULL_TIME", label: "Full Time" },
        { value: "PART_TIME", label: "Part Time" },
        { value: "CONTRACT", label: "Contract" },
        { value: "INTERN", label: "Intern" },
      ],
    },
    {
      key: "level",
      label: "Level",
      type: "select",
      options: [
        { value: "ENTRY", label: "Entry" },
        { value: "MID", label: "Mid" },
        { value: "SENIOR", label: "Senior" },
        { value: "LEAD", label: "Lead" },
        { value: "EXECUTIVE", label: "Executive" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "FILLED", label: "Filled" },
        { value: "FROZEN", label: "Frozen" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    { key: "headcount_budget", label: "Headcount Budget", type: "number" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "requirements", label: "Requirements", type: "textarea", gridSpan: 2 },
  ],
});
