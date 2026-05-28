import { registerResource } from "../index";

registerResource({
  key: "project-investors",
  module: "finance",
  label: "Project Investor",
  labelPlural: "Project Investors",
  endpoint: "/finance/project-investors/",
  columns: [
    { key: "project", label: "Project", type: "text" },
    { key: "investor", label: "Investor", type: "text" },
    { key: "ownership_percentage", label: "Ownership %", type: "number" },
    { key: "capital_committed", label: "Capital Committed", type: "currency" },
    { key: "capital_contributed", label: "Capital Contributed", type: "currency" },
    { key: "total_profit_distributed", label: "Profit Distributed", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search project investors..." },
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "investor", label: "Investor", type: "relation_picker", required: true, optionsEndpoint: "/finance/investors/" },
    { key: "ownership_percentage", label: "Ownership %", type: "number", required: true },
    { key: "capital_committed", label: "Capital Committed", type: "currency", required: true },
    { key: "capital_contributed", label: "Capital Contributed", type: "currency" },
    { key: "custom_profit_split_pct", label: "Custom Profit Split %", type: "number" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
