import { registerResource } from "../index";

registerResource({
  key: "subscriptions",
  module: "accounts",
  label: "Subscription",
  labelPlural: "Subscriptions",
  endpoint: "/platform/subscription/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "plan", label: "Plan Details" },
    { key: "billing", label: "Billing" },
    { key: "usage", label: "Usage" },
  ],
  formFields: [
    // Plan Details
    { key: "edition_name", label: "Edition", type: "readonly", section: "plan" },
    { key: "status", label: "Status", type: "readonly", section: "plan" },
    {
      key: "billing_cycle",
      label: "Billing Cycle",
      type: "select",
      section: "plan",
      options: [
        { value: "monthly", label: "Monthly" },
        { value: "annual", label: "Annual" },
      ],
    },
    // Billing
    { key: "current_period_start", label: "Period Start", type: "readonly", section: "billing" },
    { key: "current_period_end", label: "Period End", type: "readonly", section: "billing" },
    { key: "auto_renew", label: "Auto-Renew", type: "boolean", section: "billing" },
    { key: "payment_method_summary", label: "Payment Method", type: "readonly", section: "billing" },
    // Usage
    { key: "seats_purchased", label: "Seats Purchased", type: "readonly", section: "usage" },
    { key: "seats_used", label: "Seats Used", type: "readonly", section: "usage" },
    { key: "storage_used_gb", label: "Storage Used (GB)", type: "readonly", section: "usage" },
  ],
});
