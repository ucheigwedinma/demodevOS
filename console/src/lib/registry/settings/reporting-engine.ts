import { registerResource } from "../index";

registerResource({
  key: "reporting-engine",
  module: "settings",
  label: "Reporting Engine",
  labelPlural: "PDF formatting, watermarks, board pack, and dispatch defaults",
  endpoint: "/settings/reporting-engine/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "pdf", label: "PDF Formatting" },
    { key: "watermark", label: "Watermark" },
    { key: "dispatch", label: "Dispatch" },
  ],
  formFields: [
    {
      key: "page_size",
      label: "Page Size",
      type: "select",
      options: [
        { value: "A4", label: "A4" },
        { value: "letter", label: "Letter" },
        { value: "legal", label: "Legal" },
      ],
      section: "pdf",
    },
    {
      key: "orientation",
      label: "Orientation",
      type: "select",
      options: [
        { value: "portrait", label: "Portrait" },
        { value: "landscape", label: "Landscape" },
      ],
      section: "pdf",
    },
    { key: "font_family", label: "Font Family", type: "text", defaultValue: "Raleway", section: "pdf" },
    { key: "font_size_pt", label: "Font Size (pt)", type: "number", defaultValue: 10, section: "pdf" },
    { key: "header_enabled", label: "Header Enabled", type: "boolean", defaultValue: true, section: "pdf" },
    { key: "footer_enabled", label: "Footer Enabled", type: "boolean", defaultValue: true, section: "pdf" },
    { key: "watermark_enabled", label: "Watermark Enabled", type: "boolean", section: "watermark" },
    { key: "watermark_text", label: "Watermark Text", type: "text", section: "watermark" },
    { key: "watermark_opacity", label: "Watermark Opacity", type: "number", section: "watermark" },
    {
      key: "default_dispatch_format",
      label: "Default Dispatch Format",
      type: "select",
      options: [
        { value: "pdf", label: "PDF" },
        { value: "xlsx", label: "XLSX" },
        { value: "csv", label: "CSV" },
      ],
      section: "dispatch",
    },
    { key: "dispatch_retention_days", label: "Retention (days)", type: "number", defaultValue: 90, section: "dispatch" },
  ],
});
