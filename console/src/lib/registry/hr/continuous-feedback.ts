import { registerResource } from "../index";

registerResource({
  key: "continuous-feedback",
  module: "hr",
  label: "Continuous Feedback",
  labelPlural: "Continuous Feedback",
  endpoint: "/hr/continuous-feedback/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "given_by", label: "Given By", type: "text" },
    { key: "feedback_type", label: "Feedback Type", type: "badge" },
    { key: "subject", label: "Subject", type: "text" },
    { key: "visibility", label: "Visibility", type: "badge" },
    { key: "created_at", label: "Created At", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "feedback_type",
      label: "Feedback Type",
      type: "select",
      options: [
        { value: "PRAISE", label: "Praise" },
        { value: "CONSTRUCTIVE", label: "Constructive" },
        { value: "SUGGESTION", label: "Suggestion" },
        { value: "CONCERN", label: "Concern" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "given_by", label: "Given By", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    {
      key: "feedback_type", label: "Feedback Type", type: "select", options: [
        { value: "PRAISE", label: "Praise" },
        { value: "CONSTRUCTIVE", label: "Constructive" },
        { value: "SUGGESTION", label: "Suggestion" },
        { value: "CONCERN", label: "Concern" },
      ],
    },
    {
      key: "visibility", label: "Visibility", type: "select", options: [
        { value: "PRIVATE", label: "Private" },
        { value: "MANAGER", label: "Manager" },
        { value: "PUBLIC", label: "Public" },
      ],
    },
    { key: "subject", label: "Subject", type: "text", required: true },
    { key: "content", label: "Content", type: "textarea", gridSpan: 2, required: true },
    { key: "is_anonymous", label: "Anonymous", type: "boolean" },
  ],
});
