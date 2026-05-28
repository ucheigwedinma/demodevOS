import { registerResource } from "../index";

registerResource({
  key: "subsidiaries",
  module: "settings",
  label: "Subsidiary",
  labelPlural: "Subsidiaries",
  endpoint: "/settings/subsidiaries/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "legal_name", label: "Legal Name", type: "text" },
    { key: "relationship_type", label: "Relationship", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "city", label: "City", type: "text" },
    { key: "country", label: "Country", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search subsidiaries..." },
    {
      key: "relationship_type",
      label: "Relationship",
      type: "select",
      options: [
        { value: "subsidiary", label: "Subsidiary" },
        { value: "branch", label: "Branch" },
        { value: "joint_venture", label: "Joint Venture" },
        { value: "associate", label: "Associate" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "active", label: "Active" },
        { value: "dormant", label: "Dormant" },
        { value: "dissolved", label: "Dissolved" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "legal_name", label: "Legal Name", type: "text", required: true },
    { key: "registration_number", label: "Registration Number", type: "text" },
    { key: "tax_id", label: "Tax ID", type: "text" },
    {
      key: "relationship_type",
      label: "Relationship Type",
      type: "select",
      required: true,
      options: [
        { value: "subsidiary", label: "Subsidiary" },
        { value: "branch", label: "Branch" },
        { value: "joint_venture", label: "Joint Venture" },
        { value: "associate", label: "Associate" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      required: true,
      options: [
        { value: "active", label: "Active" },
        { value: "dormant", label: "Dormant" },
        { value: "dissolved", label: "Dissolved" },
      ],
    },
    { key: "address", label: "Address", type: "text" },
    { key: "city", label: "City", type: "text" },
    { key: "country", label: "Country", type: "text" },
    { key: "contact_email", label: "Contact Email", type: "text" },
    { key: "contact_phone", label: "Contact Phone", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
