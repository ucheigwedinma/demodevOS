import { registerResource } from "../index";

registerResource({
  key: "pips",
  module: "hr",
  label: "Performance Improvement Plan",
  labelPlural: "Performance Improvement Plans",
  endpoint: "/hr/pips/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "status", label: "Status", type: "badge" },
    { key: "outcome", label: "Outcome", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "EXTENDED", label: "Extended" },
        { value: "TERMINATED", label: "Terminated" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date", required: true },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "COMPLETED", label: "Completed" },
        { value: "EXTENDED", label: "Extended" },
        { value: "TERMINATED", label: "Terminated" },
      ],
    },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
    { key: "objectives", label: "Objectives", type: "textarea", gridSpan: 2 },
    { key: "support_provided", label: "Support Provided", type: "textarea", gridSpan: 2 },
    { key: "success_criteria", label: "Success Criteria", type: "textarea", gridSpan: 2 },
  ],
});
