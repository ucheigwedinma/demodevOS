import { registerResource } from "../index";

registerResource({
  key: "vacancies",
  module: "hr",
  label: "Vacancy",
  labelPlural: "Vacancies",
  endpoint: "/hr/vacancies/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "position", label: "Position", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "hiring_manager", label: "Hiring Manager", type: "text" },
    { key: "opened_date", label: "Opened Date", type: "date", sortable: true },
    { key: "target_fill_date", label: "Target Fill Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search vacancies..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "ON_HOLD", label: "On Hold" },
        { value: "FILLED", label: "Filled" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
  ],
  formFields: [
    { key: "position", label: "Position", type: "relation_picker", optionsEndpoint: "/hr/positions/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "ON_HOLD", label: "On Hold" },
        { value: "FILLED", label: "Filled" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
    { key: "hiring_manager", label: "Hiring Manager", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "target_fill_date", label: "Target Fill Date", type: "date" },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
