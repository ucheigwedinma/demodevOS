import { registerResource } from "../index";

registerResource({
  key: "feature-flags",
  module: "settings",
  label: "Feature Flag",
  labelPlural: "Feature Flags",
  endpoint: "/settings/feature-flags/definitions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "key", label: "Key", type: "text" },
    { key: "flag_type", label: "Type", type: "text" },
    { key: "scope", label: "Scope", type: "badge" },
    { key: "default_enabled", label: "Default Enabled", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search feature flags..." },
    {
      key: "scope",
      label: "Scope",
      type: "select",
      options: [
        { value: "global", label: "Global" },
        { value: "org", label: "Organization" },
        { value: "project", label: "Project" },
        { value: "region", label: "Region" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
