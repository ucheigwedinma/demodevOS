import { registerResource } from "../index";

registerResource({
  key: "feature-flag-overrides",
  module: "settings",
  label: "Feature Flag Override",
  labelPlural: "Feature Flag Overrides",
  endpoint: "/settings/feature-flags/overrides/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "flag_name", label: "Flag", type: "text", sortable: true },
    { key: "organization_name", label: "Organization", type: "text" },
    { key: "enabled", label: "Enabled", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search overrides..." },
  ],
  formFields: [
    { key: "flag", label: "Feature Flag", type: "relation_picker", required: true, optionsEndpoint: "/settings/feature-flags/definitions/" },
    { key: "enabled", label: "Enabled", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
