import { registerResource } from "../index";

registerResource({
  key: "platform-editions",
  module: "settings",
  label: "Platform Edition",
  labelPlural: "Platform Editions",
  endpoint: "/settings/platform-editions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "key", label: "Key", type: "text" },
    { key: "tier_level", label: "Tier", type: "number", sortable: true },
    { key: "max_users", label: "Max Users", type: "number" },
    { key: "monthly_price", label: "Monthly Price", type: "currency" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search platform editions..." },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
