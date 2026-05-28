import { registerResource } from "../index";

registerResource({
  key: "vendors",
  module: "procurement",
  label: "Vendor",
  labelPlural: "Vendors",
  endpoint: "/procurement/vendors/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "category", label: "Category", type: "text" },
    { key: "performance_rating", label: "Performance Rating", type: "number" },
    { key: "compliance_status", label: "Compliance Status", type: "badge" },
    { key: "is_blacklisted", label: "Blacklisted", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search vendors..." },
    {
      key: "compliance_status",
      label: "Compliance Status",
      type: "select",
      options: [
        { value: "COMPLIANT", label: "Compliant" },
        { value: "NON_COMPLIANT", label: "Non-Compliant" },
        { value: "PENDING", label: "Pending" },
        { value: "EXPIRED", label: "Expired" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "contact_person", label: "Contact Person", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "category", label: "Category", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "performance_rating", label: "Performance Rating", type: "number" },
    {
      key: "compliance_status",
      label: "Compliance Status",
      type: "select",
      options: [
        { value: "COMPLIANT", label: "Compliant" },
        { value: "NON_COMPLIANT", label: "Non-Compliant" },
        { value: "PENDING", label: "Pending" },
        { value: "EXPIRED", label: "Expired" },
      ],
    },
    { key: "is_blacklisted", label: "Blacklisted", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
