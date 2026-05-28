import { registerResource } from "../index";

registerResource({
  key: "communication-branding",
  module: "settings",
  label: "Communication & Branding",
  labelPlural: "Email, SMS, notification branding, and letterhead settings",
  endpoint: "/settings/communication-branding/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "email", label: "Email Branding" },
    { key: "notification", label: "Notifications" },
    { key: "sms", label: "SMS" },
  ],
  formFields: [
    { key: "email_sender_name", label: "Sender Name", type: "text", section: "email" },
    { key: "email_sender_address", label: "Sender Address", type: "text", section: "email" },
    { key: "email_reply_to", label: "Reply-To Address", type: "text", section: "email" },
    { key: "email_primary_color", label: "Primary Color", type: "text", placeholder: "#hexcolor", section: "email" },
    { key: "notification_brand_color", label: "Brand Color", type: "text", placeholder: "#hexcolor", section: "notification" },
    { key: "notification_app_name", label: "App Name", type: "text", section: "notification" },
    { key: "notification_include_logo", label: "Include Logo", type: "boolean", section: "notification" },
    { key: "sms_sender_id", label: "Sender ID", type: "text", section: "sms" },
    { key: "sms_enabled", label: "SMS Enabled", type: "boolean", section: "sms" },
    { key: "sms_character_limit", label: "Character Limit", type: "number", defaultValue: 160, section: "sms" },
  ],
});
