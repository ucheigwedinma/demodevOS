import { registerResource } from "../index";

registerResource({
  key: "broker-tiers",
  module: "crm",
  label: "Broker Tier",
  labelPlural: "Broker Tiers",
  endpoint: "/crm/tiers/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "min_deals", label: "Min Deals", type: "number" },
    { key: "min_revenue", label: "Min Revenue", type: "currency" },
    { key: "commission_multiplier", label: "Commission Multiplier", type: "number" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search broker tiers..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "min_deals", label: "Min Deals", type: "number" },
    { key: "min_revenue", label: "Min Revenue", type: "currency" },
    { key: "commission_multiplier", label: "Commission Multiplier", type: "number" },
    { key: "bonus_pct", label: "Bonus %", type: "number" },
    { key: "evaluation_period_months", label: "Evaluation Period (Months)", type: "number" },
    { key: "color", label: "Color", type: "text" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "benefits", label: "Benefits", type: "textarea", gridSpan: 2 },
  ],
});
