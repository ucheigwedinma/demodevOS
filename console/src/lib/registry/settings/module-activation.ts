import { registerResource } from "../index";

registerResource({
  key: "module-activation",
  module: "settings",
  label: "Module Activation",
  labelPlural: "Enable or disable platform modules for this organization",
  endpoint: "/settings/module-activation/",
  singleton: true,
  columns: [],
  formFields: [
    { key: "enabled_modules", label: "Enabled Modules", type: "textarea", gridSpan: 2, helpText: "JSON array of enabled module keys" },
  ],
});
