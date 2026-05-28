import { registerResource } from "../index";

registerResource({
  key: "attendance-logs",
  module: "hr",
  label: "Attendance Log",
  labelPlural: "Attendance Logs",
  endpoint: "/hr/attendance-logs/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "date", label: "Date", type: "date", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "clock_in", label: "Clock In", type: "text" },
    { key: "clock_out", label: "Clock Out", type: "text" },
    { key: "total_hours", label: "Total Hours", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search attendance..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PRESENT", label: "Present" },
        { value: "ABSENT", label: "Absent" },
        { value: "LATE", label: "Late" },
        { value: "HALF_DAY", label: "Half Day" },
        { value: "ON_LEAVE", label: "On Leave" },
        { value: "REMOTE", label: "Remote" },
        { value: "HOLIDAY", label: "Holiday" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "date", label: "Date", type: "date", required: true },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PRESENT", label: "Present" },
        { value: "ABSENT", label: "Absent" },
        { value: "LATE", label: "Late" },
        { value: "HALF_DAY", label: "Half Day" },
        { value: "ON_LEAVE", label: "On Leave" },
        { value: "REMOTE", label: "Remote" },
        { value: "HOLIDAY", label: "Holiday" },
      ],
    },
    { key: "clock_in", label: "Clock In", type: "text" },
    { key: "clock_out", label: "Clock Out", type: "text" },
    { key: "break_minutes", label: "Break (min)", type: "number", defaultValue: 0 },
    { key: "location", label: "Location", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
