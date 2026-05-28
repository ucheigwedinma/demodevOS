import { registerResource } from "../index";

registerResource({
  key: "learning-resources",
  module: "hr",
  label: "Learning Resource",
  labelPlural: "Learning Resources",
  endpoint: "/hr/learning-resources/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "resource_type", label: "Type", type: "badge" },
    { key: "category", label: "Category", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "duration_minutes", label: "Duration (min)", type: "number" },
    { key: "view_count", label: "Views", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search resources..." },
    {
      key: "resource_type",
      label: "Type",
      type: "select",
      options: [
        { value: "DOCUMENT", label: "Document" },
        { value: "VIDEO", label: "Video" },
        { value: "ARTICLE", label: "Article" },
        { value: "EBOOK", label: "eBook" },
        { value: "TEMPLATE", label: "Template" },
        { value: "LINK", label: "Link" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PUBLISHED", label: "Published" },
        { value: "DRAFT", label: "Draft" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "resource_type",
      label: "Type",
      type: "select",
      options: [
        { value: "DOCUMENT", label: "Document" },
        { value: "VIDEO", label: "Video" },
        { value: "ARTICLE", label: "Article" },
        { value: "EBOOK", label: "eBook" },
        { value: "TEMPLATE", label: "Template" },
        { value: "LINK", label: "Link" },
      ],
    },
    { key: "category", label: "Category", type: "text" },
    { key: "url", label: "URL", type: "text" },
    { key: "duration_minutes", label: "Duration (min)", type: "number" },
    { key: "tags", label: "Tags", type: "text" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PUBLISHED", label: "Published" },
        { value: "DRAFT", label: "Draft" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
