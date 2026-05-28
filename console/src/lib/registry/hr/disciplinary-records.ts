import { registerResource } from "../index";

registerResource({
  key: "disciplinary-records",
  module: "hr",
  label: "Disciplinary Record",
  labelPlural: "Disciplinary Records",
  endpoint: "/hr/disciplinary-records/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "incident_date", label: "Incident Date", type: "date" },
    { key: "category", label: "Category", type: "badge" },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "follow_up_date", label: "Follow-up Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "UNDER_REVIEW", label: "Under Review" },
        { value: "RESOLVED", label: "Resolved" },
        { value: "APPEALED", label: "Appealed" },
      ],
    },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "MISCONDUCT", label: "Misconduct" },
        { value: "PERFORMANCE", label: "Performance" },
        { value: "ATTENDANCE", label: "Attendance" },
        { value: "POLICY_VIOLATION", label: "Policy Violation" },
        { value: "OTHER", label: "Other" },
      ],
    },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "VERBAL_WARNING", label: "Verbal Warning" },
        { value: "WRITTEN_WARNING", label: "Written Warning" },
        { value: "FINAL_WARNING", label: "Final Warning" },
        { value: "SUSPENSION", label: "Suspension" },
        { value: "TERMINATION", label: "Termination" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "incident_date", label: "Incident Date", type: "date", required: true },
    { key: "category", label: "Category", type: "select", options: [
      { value: "MISCONDUCT", label: "Misconduct" },
      { value: "PERFORMANCE", label: "Performance" },
      { value: "ATTENDANCE", label: "Attendance" },
      { value: "POLICY_VIOLATION", label: "Policy Violation" },
      { value: "OTHER", label: "Other" },
    ]},
    { key: "severity", label: "Severity", type: "select", options: [
      { value: "VERBAL_WARNING", label: "Verbal Warning" },
      { value: "WRITTEN_WARNING", label: "Written Warning" },
      { value: "FINAL_WARNING", label: "Final Warning" },
      { value: "SUSPENSION", label: "Suspension" },
      { value: "TERMINATION", label: "Termination" },
    ]},
    { key: "status", label: "Status", type: "select", options: [
      { value: "OPEN", label: "Open" },
      { value: "UNDER_REVIEW", label: "Under Review" },
      { value: "RESOLVED", label: "Resolved" },
      { value: "APPEALED", label: "Appealed" },
    ]},
    { key: "description", label: "Description", type: "textarea", gridSpan: 2, required: true },
    { key: "action_taken", label: "Action Taken", type: "textarea", gridSpan: 2 },
    { key: "follow_up_date", label: "Follow-up Date", type: "date" },
  ],
});
