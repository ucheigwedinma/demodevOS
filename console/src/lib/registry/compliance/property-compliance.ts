import { registerResource } from "../index";

registerResource({
  key: "property-compliance",
  module: "compliance",
  label: "Property Compliance",
  labelPlural: "Property Compliance",
  endpoint: "/compliance/tracker/",
  columns: [
    { key: "property", label: "Property", type: "text" },
    { key: "requirement", label: "Requirement", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "certificate_number", label: "Certificate Number", type: "text" },
    { key: "expiry_date", label: "Expiry Date", type: "date", sortable: true },
    { key: "responsible_person", label: "Responsible Person", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search compliance..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "COMPLIANT", label: "Compliant" },
        { value: "NON_COMPLIANT", label: "Non-Compliant" },
        { value: "PENDING", label: "Pending" },
        { value: "EXPIRED", label: "Expired" },
        { value: "EXEMPT", label: "Exempt" },
      ],
    },
  ],
  formFields: [
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "requirement", label: "Requirement", type: "relation_picker", required: true, optionsEndpoint: "/compliance/requirements/" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "COMPLIANT", label: "Compliant" },
        { value: "NON_COMPLIANT", label: "Non-Compliant" },
        { value: "PENDING", label: "Pending" },
        { value: "EXPIRED", label: "Expired" },
        { value: "EXEMPT", label: "Exempt" },
      ],
    },
    { key: "certificate_number", label: "Certificate Number", type: "text" },
    { key: "issuing_authority", label: "Issuing Authority", type: "text" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    { key: "responsible_person", label: "Responsible Person", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
