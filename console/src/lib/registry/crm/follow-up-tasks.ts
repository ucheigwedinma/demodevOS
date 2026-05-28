import { registerResource } from "../index";

registerResource({
  key: "follow-up-tasks",
  module: "crm",
  label: "Follow-up Task",
  labelPlural: "Follow-up Tasks",
  endpoint: "/crm/follow-up-tasks/",
  columns: [
    { key: "rule", label: "Rule", type: "text" },
    { key: "lead", label: "Lead", type: "text" },
    { key: "assigned_to", label: "Assigned To", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "due_at", label: "Due At", type: "datetime" },
    { key: "completed_at", label: "Completed At", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search follow-up tasks..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
        { value: "BREACHED", label: "Breached" },
        { value: "ESCALATED", label: "Escalated" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  canCreate: false,
  canDelete: false,
});
