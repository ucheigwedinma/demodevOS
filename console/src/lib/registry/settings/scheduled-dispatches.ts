import { registerResource } from "../index";

registerResource({
  key: "scheduled-dispatches",
  module: "settings",
  label: "Scheduled Dispatch",
  labelPlural: "Scheduled Dispatches",
  endpoint: "/settings/scheduled-dispatches/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "report_template_name", label: "Report Template", type: "text" },
    { key: "frequency", label: "Frequency", type: "text" },
    { key: "output_format", label: "Format", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "last_dispatched_at", label: "Last Dispatched", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search scheduled dispatches..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "report_template", label: "Report Template", type: "relation_picker", required: true, optionsEndpoint: "/settings/report-templates/" },
    {
      key: "frequency",
      label: "Frequency",
      type: "select",
      required: true,
      options: [
        { value: "daily", label: "Daily" },
        { value: "weekly", label: "Weekly" },
        { value: "monthly", label: "Monthly" },
        { value: "quarterly", label: "Quarterly" },
        { value: "annual", label: "Annual" },
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
    { key: "dispatch_time", label: "Dispatch Time", type: "text", placeholder: "HH:MM" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
