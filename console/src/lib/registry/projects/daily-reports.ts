import { registerResource } from "../index";

registerResource({
  key: "daily-reports",
  module: "projects",
  label: "Daily Site Report",
  labelPlural: "Daily Site Reports",
  endpoint: "/projects/field-operations/reports/",
  columns: [
    { key: "project", label: "Project", type: "text" },
    { key: "report_date", label: "Report Date", type: "date", sortable: true },
    { key: "shift", label: "Shift", type: "badge" },
    { key: "weather", label: "Weather", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "progress_percent", label: "Progress %", type: "number" },
    { key: "escalation_required", label: "Escalation Required", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search daily reports..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "REVIEWED", label: "Reviewed" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    {
      key: "weather",
      label: "Weather",
      type: "select",
      options: [
        { value: "CLEAR", label: "Clear" },
        { value: "CLOUDY", label: "Cloudy" },
        { value: "RAIN", label: "Rain" },
        { value: "STORM", label: "Storm" },
        { value: "WINDY", label: "Windy" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "report_date", label: "Report Date", type: "date", required: true },
    {
      key: "shift",
      label: "Shift",
      type: "select",
      options: [
        { value: "DAY", label: "Day" },
        { value: "NIGHT", label: "Night" },
        { value: "FULL_DAY", label: "Full Day" },
      ],
    },
    {
      key: "weather",
      label: "Weather",
      type: "select",
      options: [
        { value: "CLEAR", label: "Clear" },
        { value: "CLOUDY", label: "Cloudy" },
        { value: "RAIN", label: "Rain" },
        { value: "STORM", label: "Storm" },
        { value: "WINDY", label: "Windy" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "weather_delay_hours", label: "Weather Delay Hours", type: "number" },
    { key: "progress_percent", label: "Progress %", type: "number" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "REVIEWED", label: "Reviewed" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    { key: "work_completed", label: "Work Completed", type: "textarea", gridSpan: 2 },
    { key: "planned_next_day", label: "Planned Next Day", type: "textarea", gridSpan: 2 },
    { key: "blockers", label: "Blockers", type: "textarea", gridSpan: 2 },
    { key: "safety_observations", label: "Safety Observations", type: "textarea", gridSpan: 2 },
  ],
});
