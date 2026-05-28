import { registerResource } from "../index";

registerResource({
  key: "handbook-sections",
  module: "hr",
  label: "Handbook Section",
  labelPlural: "Handbook Sections",
  endpoint: "/hr/handbook-sections/",
  columns: [
    { key: "section_number", label: "Section Number", type: "text" },
    { key: "title", label: "Title", type: "text" },
    { key: "handbook_version", label: "Handbook Version", type: "text" },
    { key: "order", label: "Order", type: "number" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PUBLISHED", label: "Published" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
  ],
  formFields: [
    { key: "handbook_version", label: "Handbook Version", type: "text", required: true },
    { key: "section_number", label: "Section Number", type: "text", required: true },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "order", label: "Order", type: "number" },
    { key: "status", label: "Status", type: "select", options: [
      { value: "DRAFT", label: "Draft" },
      { value: "PUBLISHED", label: "Published" },
      { value: "ARCHIVED", label: "Archived" },
    ]},
    { key: "content", label: "Content", type: "textarea", gridSpan: 2 },
  ],
});
