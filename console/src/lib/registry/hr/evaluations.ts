import { registerResource } from "../index";

registerResource({
  key: "evaluations",
  module: "hr",
  label: "Evaluation",
  labelPlural: "Evaluations",
  endpoint: "/hr/evaluations/",
  columns: [
    { key: "candidate", label: "Candidate", type: "text" },
    { key: "evaluator", label: "Evaluator", type: "text" },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    { key: "recommendation", label: "Recommendation", type: "badge" },
    { key: "evaluated_at", label: "Evaluated At", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search evaluations..." },
  ],
  formFields: [
    { key: "candidate", label: "Candidate", type: "relation_picker", required: true, optionsEndpoint: "/hr/candidates/" },
    { key: "evaluator", label: "Evaluator", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    {
      key: "recommendation",
      label: "Recommendation",
      type: "select",
      options: [
        { value: "STRONG_HIRE", label: "Strong Hire" },
        { value: "HIRE", label: "Hire" },
        { value: "MAYBE", label: "Maybe" },
        { value: "NO_HIRE", label: "No Hire" },
        { value: "STRONG_NO_HIRE", label: "Strong No Hire" },
      ],
    },
    { key: "strengths", label: "Strengths", type: "textarea", gridSpan: 2 },
    { key: "concerns", label: "Concerns", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canCreate: true,
  canEdit: true,
  canDelete: false,
});
