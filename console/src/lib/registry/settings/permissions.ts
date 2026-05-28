import { registerResource } from "../index";

registerResource({
  key: "permissions",
  module: "settings",
  label: "Permission",
  labelPlural: "Permissions",
  endpoint: "/settings/permissions/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "key", label: "Key", type: "text", sortable: true },
    { key: "module", label: "Module", type: "text", sortable: true },
    { key: "sub_module", label: "Sub-Module", type: "text" },
    { key: "action", label: "Action", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search permissions..." },
    { key: "module", label: "Module", type: "select", optionsEndpoint: "/settings/permissions/modules/" },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
