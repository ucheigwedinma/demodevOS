import { registerResource } from "../index";

registerResource({
  key: "exit-interviews",
  module: "hr",
  label: "Exit Interview",
  labelPlural: "Exit Interviews",
  endpoint: "/hr/exit-interviews/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "interview_date", label: "Interview Date", type: "date" },
    { key: "overall_satisfaction", label: "Overall Satisfaction", type: "number" },
    { key: "would_recommend", label: "Would Recommend", type: "boolean" },
    { key: "would_rejoin", label: "Would Rejoin", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "exit_record", label: "Exit Record", type: "relation_picker", optionsEndpoint: "/hr/exit-management/" },
    { key: "interview_date", label: "Interview Date", type: "date", required: true },
    { key: "interviewer", label: "Interviewer", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "overall_satisfaction", label: "Overall Satisfaction", type: "number" },
    { key: "would_recommend", label: "Would Recommend", type: "boolean" },
    { key: "would_rejoin", label: "Would Rejoin", type: "boolean" },
    { key: "reason_for_leaving", label: "Reason for Leaving", type: "textarea", gridSpan: 2 },
    { key: "feedback", label: "Feedback", type: "textarea", gridSpan: 2 },
    { key: "key_concerns", label: "Key Concerns", type: "textarea", gridSpan: 2 },
    { key: "suggestions", label: "Suggestions", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
