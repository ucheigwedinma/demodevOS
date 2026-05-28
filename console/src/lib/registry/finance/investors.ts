import { registerResource } from "../index";

registerResource({
  key: "investors",
  module: "finance",
  label: "Investor",
  labelPlural: "Investors",
  endpoint: "/finance/investors/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "investor_type", label: "Type", type: "badge" },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "entity_name", label: "Entity Name", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search investors..." },
    {
      key: "investor_type",
      label: "Investor Type",
      type: "select",
      options: [
        { value: "INDIVIDUAL", label: "Individual" },
        { value: "INSTITUTIONAL", label: "Institutional" },
        { value: "FAMILY_OFFICE", label: "Family Office" },
        { value: "FUND", label: "Fund" },
        { value: "CORPORATE", label: "Corporate" },
        { value: "JV_PARTNER", label: "JV Partner" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "investor_type",
      label: "Investor Type",
      type: "select",
      required: true,
      options: [
        { value: "INDIVIDUAL", label: "Individual" },
        { value: "INSTITUTIONAL", label: "Institutional" },
        { value: "FAMILY_OFFICE", label: "Family Office" },
        { value: "FUND", label: "Fund" },
        { value: "CORPORATE", label: "Corporate" },
        { value: "JV_PARTNER", label: "JV Partner" },
      ],
    },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "tax_id", label: "Tax ID", type: "text" },
    { key: "entity_name", label: "Entity Name", type: "text" },
    { key: "registration_number", label: "Registration Number", type: "text" },
    { key: "address", label: "Address", type: "textarea" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
