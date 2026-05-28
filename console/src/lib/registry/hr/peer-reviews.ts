import { registerResource } from "../index";

registerResource({
  key: "peer-reviews",
  module: "hr",
  label: "Peer Review",
  labelPlural: "Peer Reviews",
  endpoint: "/hr/peer-reviews/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "reviewer", label: "Reviewer", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    { key: "submitted_at", label: "Submitted At", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "DECLINED", label: "Declined" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "reviewer", label: "Reviewer", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "review", label: "Review", type: "relation_picker", optionsEndpoint: "/hr/performance-reviews/" },
    { key: "overall_rating", label: "Overall Rating", type: "number" },
    { key: "collaboration_rating", label: "Collaboration Rating", type: "number" },
    { key: "communication_rating", label: "Communication Rating", type: "number" },
    { key: "strengths", label: "Strengths", type: "textarea", gridSpan: 2 },
    { key: "areas_for_improvement", label: "Areas for Improvement", type: "textarea", gridSpan: 2 },
    { key: "is_anonymous", label: "Anonymous", type: "boolean" },
  ],
});
