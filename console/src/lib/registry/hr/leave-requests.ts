import { registerResource } from "../index";

registerResource({
  key: "leave-requests",
  module: "hr",
  label: "Leave Request",
  labelPlural: "Leave Requests",
  endpoint: "/hr/leave-requests/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "leave_type", label: "Leave Type", type: "text" },
    { key: "start_date", label: "Start Date", type: "date", sortable: true },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "total_days", label: "Total Days", type: "number" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search leave requests..." },
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
    { key: "leave_type", label: "Leave Type", type: "relation_picker", required: true, optionsEndpoint: "/hr/leave-types/" },
    { key: "start_date", label: "Start Date", type: "date", required: true },
    { key: "end_date", label: "End Date", type: "date", required: true },
    { key: "total_days", label: "Total Days", type: "number" },
    { key: "is_half_day", label: "Half Day", type: "boolean" },
    { key: "reason", label: "Reason", type: "textarea", gridSpan: 2 },
  ],
});
