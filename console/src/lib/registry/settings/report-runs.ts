import { registerResource } from "../index";

registerResource({
  key: "report-runs",
  module: "settings",
  label: "Report Run",
  labelPlural: "Report Runs",
  endpoint: "/settings/report-runs/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "report_template_name", label: "Report Template", type: "text", sortable: true },
    { key: "trigger", label: "Trigger", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "row_count", label: "Rows", type: "number" },
    { key: "created_at", label: "Created", type: "datetime" },
    { key: "completed_at", label: "Completed", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search report runs..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "queued", label: "Queued" },
        { value: "running", label: "Running" },
        { value: "succeeded", label: "Succeeded" },
        { value: "failed", label: "Failed" },
      ],
    },
    {
      key: "trigger",
      label: "Trigger",
      type: "select",
      options: [
        { value: "manual", label: "Manual" },
        { value: "scheduled", label: "Scheduled" },
        { value: "subscription", label: "Subscription" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
