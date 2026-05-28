import { registerResource } from "../index";

registerResource({
  key: "notification-templates",
  module: "settings",
  label: "Notification Template",
  labelPlural: "Notification Templates",
  endpoint: "/settings/notifications/templates/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "channel", label: "Channel", type: "badge" },
    { key: "event_key", label: "Event Key", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search templates..." },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "email", label: "Email" },
        { value: "in_app", label: "In-App" },
        { value: "sms", label: "SMS" },
        { value: "push", label: "Push" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      required: true,
      options: [
        { value: "email", label: "Email" },
        { value: "in_app", label: "In-App" },
        { value: "sms", label: "SMS" },
        { value: "push", label: "Push" },
      ],
    },
    { key: "event_key", label: "Event Key", type: "text" },
    { key: "severity_tier", label: "Severity Tier", type: "text" },
    { key: "subject", label: "Subject", type: "text" },
    { key: "body_text", label: "Body Text", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
