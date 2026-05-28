import { registerResource } from "../index";

registerResource({
  key: "exit-management",
  module: "hr",
  label: "Exit Record",
  labelPlural: "Exit Records",
  endpoint: "/hr/exit-management/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "exit_type", label: "Exit Type", type: "badge" },
    { key: "notice_date", label: "Notice Date", type: "date" },
    { key: "last_working_day", label: "Last Working Day", type: "date" },
    { key: "clearance_status", label: "Clearance Status", type: "badge" },
    { key: "final_settlement_status", label: "Settlement Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "exit_type",
      label: "Exit Type",
      type: "select",
      options: [
        { value: "RESIGNATION", label: "Resignation" },
        { value: "TERMINATION", label: "Termination" },
        { value: "RETIREMENT", label: "Retirement" },
        { value: "END_OF_CONTRACT", label: "End of Contract" },
        { value: "REDUNDANCY", label: "Redundancy" },
        { value: "OTHER", label: "Other" },
      ],
    },
    {
      key: "clearance_status",
      label: "Clearance Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "exit_type", label: "Exit Type", type: "select", required: true, options: [
      { value: "RESIGNATION", label: "Resignation" },
      { value: "TERMINATION", label: "Termination" },
      { value: "RETIREMENT", label: "Retirement" },
      { value: "END_OF_CONTRACT", label: "End of Contract" },
      { value: "REDUNDANCY", label: "Redundancy" },
      { value: "OTHER", label: "Other" },
    ]},
    { key: "notice_date", label: "Notice Date", type: "date", required: true },
    { key: "last_working_day", label: "Last Working Day", type: "date", required: true },
    { key: "clearance_status", label: "Clearance Status", type: "select", options: [
      { value: "PENDING", label: "Pending" },
      { value: "IN_PROGRESS", label: "In Progress" },
      { value: "COMPLETED", label: "Completed" },
    ]},
    { key: "final_settlement_status", label: "Settlement Status", type: "select", options: [
      { value: "PENDING", label: "Pending" },
      { value: "PROCESSING", label: "Processing" },
      { value: "PAID", label: "Paid" },
    ]},
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
