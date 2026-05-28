import { registerResource } from "../index";

registerResource({
  key: "brokers",
  module: "crm",
  label: "Broker",
  labelPlural: "Brokers",
  endpoint: "/crm/brokers/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "company", label: "Company", type: "text" },
    { key: "license_number", label: "License Number", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "commission_rate", label: "Commission Rate", type: "number" },
    { key: "tier", label: "Tier", type: "text" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search brokers..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "INACTIVE", label: "Inactive" },
        { value: "SUSPENDED", label: "Suspended" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "company", label: "Company", type: "text" },
    { key: "license_number", label: "License Number", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "commission_rate", label: "Commission Rate", type: "number" },
    { key: "tier", label: "Tier", type: "relation_picker", optionsEndpoint: "/crm/tiers/" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "INACTIVE", label: "Inactive" },
        { value: "SUSPENDED", label: "Suspended" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
