import { registerResource } from "../index";

registerResource({
  key: "security-settings",
  module: "settings",
  label: "Security Settings",
  labelPlural: "Configure password policies, MFA, session management, and access restrictions",
  endpoint: "/settings/security/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "password", label: "Password Policy" },
    { key: "mfa", label: "Multi-Factor Authentication" },
    { key: "session", label: "Session Management" },
    { key: "ip", label: "IP Restrictions" },
  ],
  formFields: [
    { key: "password_min_length", label: "Minimum Length", type: "number", defaultValue: 8, section: "password" },
    { key: "password_require_uppercase", label: "Require Uppercase", type: "boolean", section: "password" },
    { key: "password_require_lowercase", label: "Require Lowercase", type: "boolean", section: "password" },
    { key: "password_require_digits", label: "Require Digits", type: "boolean", section: "password" },
    { key: "password_require_special", label: "Require Special Characters", type: "boolean", section: "password" },
    { key: "mfa_enforced", label: "Enforce MFA", type: "boolean", section: "mfa" },
    { key: "session_timeout_minutes", label: "Session Timeout (minutes)", type: "number", defaultValue: 1440, section: "session" },
    { key: "ip_restriction_enabled", label: "IP Restriction Enabled", type: "boolean", section: "ip" },
    { key: "geo_blocking_enabled", label: "Geo-Blocking Enabled", type: "boolean", section: "ip" },
  ],
});
