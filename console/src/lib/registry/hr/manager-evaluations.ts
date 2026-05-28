import { registerResource } from "../index";

registerResource({
  key: "manager-evaluations",
  module: "hr",
  label: "Manager Evaluation",
  labelPlural: "Manager Evaluations",
  endpoint: "/hr/manager-evaluations/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "evaluator", label: "Evaluator", type: "text" },
    { key: "evaluation_date", label: "Evaluation Date", type: "date", sortable: true },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    { key: "leadership_rating", label: "Leadership Rating", type: "number" },
    { key: "communication_rating", label: "Communication Rating", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "evaluator", label: "Evaluator", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "review", label: "Review", type: "relation_picker", optionsEndpoint: "/hr/performance-reviews/" },
    { key: "evaluation_date", label: "Evaluation Date", type: "date", required: true },
    { key: "overall_rating", label: "Overall Rating", type: "number", required: true },
    { key: "leadership_rating", label: "Leadership Rating", type: "number" },
    { key: "communication_rating", label: "Communication Rating", type: "number" },
    { key: "technical_rating", label: "Technical Rating", type: "number" },
    { key: "teamwork_rating", label: "Teamwork Rating", type: "number" },
    { key: "strengths", label: "Strengths", type: "textarea", gridSpan: 2 },
    { key: "areas_for_improvement", label: "Areas for Improvement", type: "textarea", gridSpan: 2 },
  ],
});
