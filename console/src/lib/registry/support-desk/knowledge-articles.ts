import { registerResource } from "../index";

registerResource({
  key: "knowledge-articles",
  module: "support-desk",
  label: "Knowledge Article",
  labelPlural: "Knowledge Articles",
  endpoint: "/support-desk/knowledge-base/articles/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "category", label: "Category", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "visibility", label: "Visibility", type: "badge" },
    { key: "view_count", label: "Views", type: "number" },
    { key: "helpful_votes", label: "Helpful Votes", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search articles..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "IN_REVIEW", label: "In Review" },
        { value: "PUBLISHED", label: "Published" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "visibility",
      label: "Visibility",
      type: "select",
      options: [
        { value: "PUBLIC", label: "Public" },
        { value: "INTERNAL", label: "Internal" },
        { value: "AGENTS_ONLY", label: "Agents Only" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "slug", label: "Slug", type: "text" },
    { key: "category", label: "Category", type: "text" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "IN_REVIEW", label: "In Review" },
        { value: "PUBLISHED", label: "Published" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
    {
      key: "visibility",
      label: "Visibility",
      type: "select",
      options: [
        { value: "PUBLIC", label: "Public" },
        { value: "INTERNAL", label: "Internal" },
        { value: "AGENTS_ONLY", label: "Agents Only" },
      ],
    },
    { key: "summary", label: "Summary", type: "textarea", gridSpan: 2 },
    { key: "body", label: "Body", type: "textarea", gridSpan: 2 },
  ],
});
