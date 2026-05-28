import { registerResource } from "../index";

registerResource({
  key: "interviews",
  module: "hr",
  label: "Interview",
  labelPlural: "Interviews",
  endpoint: "/hr/interviews/",
  columns: [
    { key: "candidate", label: "Candidate", type: "text" },
    { key: "interview_type", label: "Type", type: "text" },
    { key: "interviewer", label: "Interviewer", type: "text" },
    { key: "scheduled_date", label: "Scheduled Date", type: "date", sortable: true },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search interviews..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
        { value: "NO_SHOW", label: "No Show" },
      ],
    },
  ],
  formFields: [
    { key: "candidate", label: "Candidate", type: "relation_picker", required: true, optionsEndpoint: "/hr/candidates/" },
    {
      key: "interview_type",
      label: "Interview Type",
      type: "select",
      options: [
        { value: "PHONE", label: "Phone" },
        { value: "VIDEO", label: "Video" },
        { value: "IN_PERSON", label: "In Person" },
        { value: "PANEL", label: "Panel" },
        { value: "TECHNICAL", label: "Technical" },
      ],
    },
    { key: "interviewer", label: "Interviewer", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "scheduled_date", label: "Scheduled Date", type: "date", required: true },
    { key: "scheduled_time", label: "Scheduled Time", type: "text" },
    { key: "duration_minutes", label: "Duration (minutes)", type: "number", defaultValue: 60 },
    { key: "location", label: "Location", type: "text" },
    { key: "meeting_link", label: "Meeting Link", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
