import { registerResource } from "../index";

registerResource({
  key: "performance-reviews",
  module: "hr",
  label: "Performance Review",
  labelPlural: "Performance Reviews",
  endpoint: "/hr/performance-reviews/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "reviewer", label: "Reviewer", type: "text" },
    { key: "review_type", label: "Review Type", type: "badge" },
    { key: "review_period_start", label: "Period Start", type: "date" },
    { key: "review_period_end", label: "Period End", type: "date" },
    { key: "status", label: "Status", type: "badge" },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
      ],
    },
    {
      key: "review_type",
      label: "Review Type",
      type: "select",
      options: [
        { value: "ANNUAL", label: "Annual" },
        { value: "SEMI_ANNUAL", label: "Semi-Annual" },
        { value: "QUARTERLY", label: "Quarterly" },
        { value: "PROBATION", label: "Probation" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "reviewer", label: "Reviewer", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    {
      key: "review_type", label: "Review Type", type: "select", options: [
        { value: "ANNUAL", label: "Annual" },
        { value: "SEMI_ANNUAL", label: "Semi-Annual" },
        { value: "QUARTERLY", label: "Quarterly" },
        { value: "PROBATION", label: "Probation" },
      ],
    },
    { key: "review_period_start", label: "Period Start", type: "date", required: true },
    { key: "review_period_end", label: "Period End", type: "date", required: true },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "DRAFT", label: "Draft" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
      ],
    },
    { key: "strengths", label: "Strengths", type: "textarea", gridSpan: 2 },
    { key: "areas_for_improvement", label: "Areas for Improvement", type: "textarea", gridSpan: 2 },
    { key: "goals_summary", label: "Goals Summary", type: "textarea", gridSpan: 2 },
  ],
});
