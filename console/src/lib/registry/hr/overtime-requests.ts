import { registerResource } from "../index";

registerResource({
  key: "overtime-requests",
  module: "hr",
  label: "Overtime Request",
  labelPlural: "Overtime Requests",
  endpoint: "/hr/overtime-requests/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "date", label: "Date", type: "date", sortable: true },
    { key: "start_time", label: "Start Time", type: "text" },
    { key: "end_time", label: "End Time", type: "text" },
    { key: "total_hours", label: "Total Hours", type: "number" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search overtime requests..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "date", label: "Date", type: "date", required: true },
    { key: "start_time", label: "Start Time", type: "text", required: true },
    { key: "end_time", label: "End Time", type: "text", required: true },
    { key: "total_hours", label: "Total Hours", type: "number" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
