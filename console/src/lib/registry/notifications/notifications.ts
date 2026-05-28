import { registerResource } from "../index";

registerResource({
  key: "notifications",
  module: "notifications",
  label: "Notification",
  labelPlural: "Notifications",
  endpoint: "/notifications/",
  columns: [
    { key: "recipient", label: "Recipient", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "category", label: "Category", type: "badge" },
    { key: "is_read", label: "Read", type: "boolean" },
    { key: "created_at", label: "Created At", type: "datetime", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search notifications..." },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "INFO", label: "Info" },
        { value: "WARNING", label: "Warning" },
        { value: "ERROR", label: "Error" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    { key: "is_read", label: "Read", type: "boolean" },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
