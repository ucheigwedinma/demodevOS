import { registerResource } from "../index";

registerResource({
  key: "confidentiality-labels",
  module: "settings",
  label: "Confidentiality Label",
  labelPlural: "Confidentiality Labels",
  endpoint: "/settings/confidentiality-labels/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "access_level", label: "Access Level", type: "badge" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search confidentiality labels..." },
    {
      key: "access_level",
      label: "Access Level",
      type: "select",
      options: [
        { value: "public", label: "Public" },
        { value: "internal", label: "Internal" },
        { value: "confidential", label: "Confidential" },
        { value: "strictly_confidential", label: "Strictly Confidential" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    {
      key: "access_level",
      label: "Access Level",
      type: "select",
      required: true,
      options: [
        { value: "public", label: "Public" },
        { value: "internal", label: "Internal" },
        { value: "confidential", label: "Confidential" },
        { value: "strictly_confidential", label: "Strictly Confidential" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "color", label: "Color", type: "text" },
    { key: "restrict_printing", label: "Restrict Printing", type: "boolean" },
    { key: "restrict_download", label: "Restrict Download", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
