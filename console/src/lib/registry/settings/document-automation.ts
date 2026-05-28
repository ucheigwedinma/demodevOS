import { registerResource } from "../index";

registerResource({
  key: "document-automation",
  module: "settings",
  label: "Document Automation",
  labelPlural: "Default settings for document generation and digital signatures",
  endpoint: "/settings/document-automation/",
  singleton: true,
  columns: [],
  formFields: [
    { key: "default_signature_provider", label: "Default Signature Provider", type: "text" },
    { key: "default_generation_confidentiality_level", label: "Default Confidentiality Level", type: "text" },
    { key: "default_generation_template_code", label: "Default Template Code", type: "text" },
  ],
});
