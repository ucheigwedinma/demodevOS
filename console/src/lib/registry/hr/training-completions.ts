import { registerResource } from "../index";

registerResource({
  key: "training-completions",
  module: "hr",
  label: "Training Completion",
  labelPlural: "Training Completions",
  endpoint: "/hr/training-completions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "course", label: "Course", type: "text" },
    { key: "completion_date", label: "Completion Date", type: "date", sortable: true },
    { key: "result", label: "Result", type: "badge" },
    { key: "score", label: "Score", type: "number" },
    { key: "certificate_number", label: "Certificate #", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search completions..." },
    {
      key: "result",
      label: "Result",
      type: "select",
      options: [
        { value: "PASS", label: "Pass" },
        { value: "FAIL", label: "Fail" },
        { value: "DISTINCTION", label: "Distinction" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "course", label: "Course", type: "relation_picker", optionsEndpoint: "/hr/training-courses/" },
    { key: "completion_date", label: "Completion Date", type: "date", required: true },
    {
      key: "result",
      label: "Result",
      type: "select",
      options: [
        { value: "PASS", label: "Pass" },
        { value: "FAIL", label: "Fail" },
        { value: "DISTINCTION", label: "Distinction" },
      ],
    },
    { key: "score", label: "Score", type: "number" },
    { key: "certificate_number", label: "Certificate Number", type: "text" },
    { key: "certificate_expiry", label: "Certificate Expiry", type: "date" },
    { key: "hours_completed", label: "Hours Completed", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canCreate: true,
  canEdit: true,
  canDelete: false,
});
