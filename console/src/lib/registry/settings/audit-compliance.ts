import { registerResource } from "../index";

registerResource({
  key: "audit-compliance",
  module: "settings",
  label: "Audit & Compliance",
  labelPlural: "Audit logging, retention, and financial period controls",
  endpoint: "/settings/audit/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "audit", label: "Audit Logging" },
    { key: "compliance", label: "Compliance Controls" },
  ],
  formFields: [
    { key: "audit_logging_enabled", label: "Audit Logging Enabled", type: "boolean", defaultValue: true, section: "audit" },
    { key: "audit_retention_days", label: "Audit Retention (days)", type: "number", defaultValue: 365, section: "audit" },
    { key: "access_log_retention_days", label: "Access Log Retention (days)", type: "number", defaultValue: 90, section: "audit" },
    { key: "mandatory_fields_enforced", label: "Mandatory Fields Enforced", type: "boolean", section: "compliance" },
    { key: "financial_period_locking", label: "Financial Period Locking", type: "boolean", section: "compliance" },
    { key: "change_approval_required", label: "Change Approval Required", type: "boolean", section: "compliance" },
  ],
});
