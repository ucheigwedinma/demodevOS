import { registerResource } from "../index";

registerResource({
  key: "auth-sessions",
  module: "accounts",
  label: "Auth Session",
  labelPlural: "Auth Sessions",
  endpoint: "/iam/sessions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "user_email", label: "User", type: "text", sortable: true },
    { key: "auth_provider", label: "Provider", type: "text" },
    { key: "device_label", label: "Device", type: "text" },
    { key: "ip_address", label: "IP Address", type: "text" },
    { key: "created_at", label: "Created", type: "datetime", sortable: true },
    { key: "last_seen_at", label: "Last Seen", type: "datetime" },
    { key: "revoked_at", label: "Revoked", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search sessions..." },
    {
      key: "auth_provider",
      label: "Provider",
      type: "select",
      options: [
        { value: "password", label: "Password" },
        { value: "google", label: "Google" },
        { value: "microsoft", label: "Microsoft" },
        { value: "apple", label: "Apple" },
        { value: "sso_saml", label: "SSO (SAML)" },
        { value: "passkey", label: "Passkey" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
