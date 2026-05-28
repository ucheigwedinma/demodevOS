import { registerResource } from "../index";

registerResource({
  key: "training-courses",
  module: "hr",
  label: "Training Course",
  labelPlural: "Training Courses",
  endpoint: "/hr/training-courses/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "provider", label: "Provider", type: "text" },
    { key: "format", label: "Format", type: "badge" },
    { key: "level", label: "Level", type: "badge" },
    { key: "duration_hours", label: "Duration (hrs)", type: "number" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search courses..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "format",
      label: "Format",
      type: "select",
      options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "ONLINE", label: "Online" },
        { value: "HYBRID", label: "Hybrid" },
        { value: "SELF_PACED", label: "Self Paced" },
        { value: "WORKSHOP", label: "Workshop" },
      ],
    },
    {
      key: "level",
      label: "Level",
      type: "select",
      options: [
        { value: "BEGINNER", label: "Beginner" },
        { value: "INTERMEDIATE", label: "Intermediate" },
        { value: "ADVANCED", label: "Advanced" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "provider", label: "Provider", type: "text" },
    {
      key: "format",
      label: "Format",
      type: "select",
      options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "ONLINE", label: "Online" },
        { value: "HYBRID", label: "Hybrid" },
        { value: "SELF_PACED", label: "Self Paced" },
        { value: "WORKSHOP", label: "Workshop" },
      ],
    },
    {
      key: "level",
      label: "Level",
      type: "select",
      options: [
        { value: "BEGINNER", label: "Beginner" },
        { value: "INTERMEDIATE", label: "Intermediate" },
        { value: "ADVANCED", label: "Advanced" },
      ],
    },
    { key: "duration_hours", label: "Duration (hrs)", type: "number" },
    { key: "max_participants", label: "Max Participants", type: "number" },
    { key: "cost_per_participant", label: "Cost per Participant", type: "currency" },
    { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "learning_objectives", label: "Learning Objectives", type: "textarea", gridSpan: 2 },
  ],
});
