import { registerResource } from "../index";

registerResource({
  key: "warehouses",
  module: "inventory",
  label: "Warehouse",
  labelPlural: "Warehouses",
  endpoint: "/inventory/warehouses/",
  columns: [
    { key: "code", label: "Code", type: "text", sortable: true },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "location", label: "Location", type: "text" },
    { key: "project", label: "Project", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "is_default", label: "Default", type: "boolean" },
  ],
  formFields: [
    { key: "code", label: "Code", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "location", label: "Location", type: "text" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "is_default", label: "Default", type: "boolean" },
  ],
});
