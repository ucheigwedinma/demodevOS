import { registerResource } from "../index";

registerResource({
  key: "notification-channels",
  module: "settings",
  label: "Notification Channels",
  labelPlural: "Enable or disable notification delivery channels",
  endpoint: "/settings/notifications/channels/",
  singleton: true,
  columns: [],
  formFields: [
    { key: "email_enabled", label: "Email Enabled", type: "boolean", defaultValue: true },
    { key: "in_app_enabled", label: "In-App Enabled", type: "boolean", defaultValue: true },
    { key: "sms_enabled", label: "SMS Enabled", type: "boolean" },
    { key: "push_enabled", label: "Push Enabled", type: "boolean" },
  ],
});
