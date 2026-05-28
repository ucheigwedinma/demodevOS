import { registerResource } from "../index";

registerResource({
  key: "probation-records",
  module: "hr",
  label: "Probation Record",
  labelPlural: "Probation Records",
  endpoint: "/hr/probation-records/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "end_date", label: "End Date", type: "date", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "performance_rating", label: "Performance Rating", type: "number" },
    { key: "recommendation", label: "Recommendation", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "PASSED", label: "Passed" },
        { value: "FAILED", label: "Failed" },
        { value: "EXTENDED", label: "Extended" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date", required: true },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "PASSED", label: "Passed" },
        { value: "FAILED", label: "Failed" },
        { value: "EXTENDED", label: "Extended" },
      ],
    },
    { key: "reviewer", label: "Reviewer", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "performance_rating", label: "Performance Rating", type: "number" },
    {
      key: "recommendation", label: "Recommendation", type: "select", options: [
        { value: "CONFIRM", label: "Confirm" },
        { value: "EXTEND", label: "Extend" },
        { value: "TERMINATE", label: "Terminate" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
