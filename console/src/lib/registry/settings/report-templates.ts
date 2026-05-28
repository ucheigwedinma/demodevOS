import { registerResource } from "../index";

registerResource({
  key: "report-templates",
  module: "settings",
  label: "Report Template",
  labelPlural: "Report Templates",
  endpoint: "/settings/report-templates/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "template_type", label: "Type", type: "text" },
    { key: "output_format", label: "Format", type: "text" },
    { key: "visibility", label: "Visibility", type: "badge" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search report templates..." },
    {
      key: "template_type",
      label: "Type",
      type: "select",
      options: [
        { value: "financial", label: "Financial" },
        { value: "operational", label: "Operational" },
        { value: "compliance", label: "Compliance" },
        { value: "executive", label: "Executive" },
        { value: "project", label: "Project" },
        { value: "property", label: "Property" },
        { value: "custom", label: "Custom" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    {
      key: "template_type",
      label: "Type",
      type: "select",
      required: true,
      options: [
        { value: "financial", label: "Financial" },
        { value: "operational", label: "Operational" },
        { value: "compliance", label: "Compliance" },
        { value: "executive", label: "Executive" },
        { value: "project", label: "Project" },
        { value: "property", label: "Property" },
        { value: "custom", label: "Custom" },
      ],
    },
    {
      key: "output_format",
      label: "Output Format",
      type: "select",
      required: true,
      options: [
        { value: "pdf", label: "PDF" },
        { value: "xlsx", label: "XLSX" },
        { value: "csv", label: "CSV" },
        { value: "pdf_xlsx", label: "PDF + XLSX" },
      ],
    },
    {
      key: "visibility",
      label: "Visibility",
      type: "select",
      options: [
        { value: "private", label: "Private" },
        { value: "department", label: "Department" },
        { value: "shared", label: "Shared" },
      ],
    },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
