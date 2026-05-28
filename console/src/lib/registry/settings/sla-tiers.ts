import { registerResource } from "../index";

registerResource({
  key: "sla-tiers",
  module: "settings",
  label: "SLA Tier",
  labelPlural: "SLA Tiers",
  endpoint: "/settings/notifications/sla-tiers/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "level", label: "Level", type: "text", sortable: true },
    { key: "response_time_hours", label: "Response Time (hrs)", type: "number" },
    { key: "sort_order", label: "Sort Order", type: "number", sortable: true },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search SLA tiers..." },
  ],
  formFields: [
    {
      key: "level",
      label: "Level",
      type: "select",
      required: true,
      options: [
        { value: "info", label: "Info" },
        { value: "review", label: "Review" },
        { value: "action_required", label: "Action Required" },
        { value: "escalation", label: "Escalation" },
      ],
    },
    { key: "response_time_hours", label: "Response Time (hours)", type: "number", required: true },
    { key: "sort_order", label: "Sort Order", type: "number" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
