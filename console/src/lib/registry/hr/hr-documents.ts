import { registerResource } from "../index";

registerResource({
  key: "hr-documents",
  module: "hr",
  label: "HR Document",
  labelPlural: "HR Documents",
  endpoint: "/hr/hr-documents/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "category", label: "Category", type: "text" },
    { key: "file_size", label: "File Size", type: "number" },
    { key: "created_at", label: "Created", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search HR documents..." },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "CONTRACT", label: "Contract" },
        { value: "ID", label: "ID" },
        { value: "CERTIFICATE", label: "Certificate" },
        { value: "EVALUATION", label: "Evaluation" },
        { value: "DISCIPLINARY", label: "Disciplinary" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "file", label: "File", type: "file" },
  ],
});
