import { registerResource } from "../index";

registerResource({
  key: "course-enrollments",
  module: "hr",
  label: "Course Enrollment",
  labelPlural: "Course Enrollments",
  endpoint: "/hr/course-enrollments/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "course", label: "Course", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "progress", label: "Progress", type: "number" },
    { key: "score", label: "Score", type: "number" },
    { key: "enrolled_date", label: "Enrolled Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search enrollments..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ENROLLED", label: "Enrolled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "FAILED", label: "Failed" },
        { value: "WITHDRAWN", label: "Withdrawn" },
        { value: "WAITLISTED", label: "Waitlisted" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "course", label: "Course", type: "relation_picker", required: true, optionsEndpoint: "/hr/training-courses/" },
    { key: "training_plan", label: "Training Plan", type: "relation_picker", optionsEndpoint: "/hr/training-plans/" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ENROLLED", label: "Enrolled" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "FAILED", label: "Failed" },
        { value: "WITHDRAWN", label: "Withdrawn" },
        { value: "WAITLISTED", label: "Waitlisted" },
      ],
    },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "score", label: "Score", type: "number" },
    { key: "progress", label: "Progress", type: "number" },
    { key: "feedback", label: "Feedback", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
