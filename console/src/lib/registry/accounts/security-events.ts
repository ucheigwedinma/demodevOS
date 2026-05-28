import { registerResource } from "../index";

registerResource({
  key: "security-events",
  module: "accounts",
  label: "Security Event",
  labelPlural: "Security Events",
  endpoint: "/iam/security-events/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "event_type", label: "Event", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "principal", label: "Principal", type: "text" },
    { key: "provider", label: "Provider", type: "text" },
    { key: "ip_address", label: "IP Address", type: "text" },
    { key: "occurred_at", label: "Occurred", type: "datetime", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search events..." },
    {
      key: "event_type",
      label: "Event Type",
      type: "select",
      options: [
        { value: "login_success", label: "Login Success" },
        { value: "login_failed", label: "Login Failed" },
        { value: "otp_challenge", label: "OTP Challenge" },
        { value: "otp_failed", label: "OTP Failed" },
        { value: "password_changed", label: "Password Changed" },
        { value: "session_revoked_others", label: "Sessions Revoked" },
        { value: "provider_linked", label: "Provider Linked" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "success", label: "Success" },
        { value: "failed", label: "Failed" },
        { value: "info", label: "Info" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
