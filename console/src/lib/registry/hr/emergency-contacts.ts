import { registerResource } from "../index";

registerResource({
  key: "emergency-contacts",
  module: "hr",
  label: "Emergency Contact",
  labelPlural: "Emergency Contacts",
  endpoint: "/hr/emergency-contacts/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "relationship", label: "Relationship", type: "text" },
    { key: "phone", label: "Phone", type: "text" },
    { key: "is_primary", label: "Primary", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search emergency contacts..." },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "relationship", label: "Relationship", type: "text", required: true },
    { key: "phone", label: "Phone", type: "text", required: true },
    { key: "secondary_phone", label: "Secondary Phone", type: "text" },
    { key: "email", label: "Email", type: "text" },
    { key: "address", label: "Address", type: "textarea" },
    { key: "is_primary", label: "Primary", type: "boolean" },
  ],
});
