import { registerResource } from "../index";

registerResource({
  key: "customers",
  module: "finance",
  label: "Customer",
  labelPlural: "Customers",
  endpoint: "/finance/customers/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search customers..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "tax_id", label: "Tax ID", type: "text" },
    { key: "address", label: "Address", type: "textarea" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
