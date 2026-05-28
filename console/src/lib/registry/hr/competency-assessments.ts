import { registerResource } from "../index";

registerResource({
  key: "competency-assessments",
  module: "hr",
  label: "Competency Assessment",
  labelPlural: "Competency Assessments",
  endpoint: "/hr/competency-assessments/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "assessor", label: "Assessor", type: "text" },
    { key: "competency_area", label: "Competency Area", type: "text", sortable: true },
    { key: "assessment_date", label: "Assessment Date", type: "date", sortable: true },
    { key: "score", label: "Score", type: "number" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "assessor", label: "Assessor", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "competency_area", label: "Competency Area", type: "text", required: true },
    { key: "assessment_date", label: "Assessment Date", type: "date", required: true },
    { key: "score", label: "Score", type: "number" },
    { key: "max_score", label: "Max Score", type: "number" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "strengths", label: "Strengths", type: "textarea", gridSpan: 2 },
    { key: "gaps", label: "Gaps", type: "textarea", gridSpan: 2 },
    { key: "development_plan", label: "Development Plan", type: "textarea", gridSpan: 2 },
  ],
});
