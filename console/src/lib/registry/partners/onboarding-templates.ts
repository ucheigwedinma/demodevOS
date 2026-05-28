import { registerResource } from "../index";

registerResource({
  key: "onboarding-templates",
  module: "partners",
  label: "Onboarding Template",
  labelPlural: "Onboarding Templates",
  endpoint: "/partners/templates/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "partner_type", label: "Partner Type", type: "badge" },
    { key: "version", label: "Version", type: "number" },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    {
      key: "partner_type",
      label: "Partner Type",
      type: "select",
      options: [
        { value: "VENDOR", label: "Vendor" },
        { value: "INVESTOR", label: "Investor" },
        { value: "CLIENT", label: "Client" },
        { value: "BROKER", label: "Broker" },
        { value: "CONTRACTOR", label: "Contractor" },
      ],
    },
    { key: "version", label: "Version", type: "number" },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
