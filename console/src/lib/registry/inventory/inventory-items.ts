import { registerResource } from "../index";

registerResource({
  key: "inventory-items",
  module: "inventory",
  label: "Inventory Item",
  labelPlural: "Inventory Items",
  endpoint: "/inventory/items/",
  columns: [
    { key: "sku", label: "SKU", type: "text", sortable: true },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "category", label: "Category", type: "text" },
    { key: "unit_of_measure", label: "Unit of Measure", type: "text" },
    { key: "reorder_level", label: "Reorder Level", type: "number" },
    { key: "default_unit_cost", label: "Default Unit Cost", type: "currency" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search inventory items..." },
  ],
  formFields: [
    { key: "sku", label: "SKU", type: "text", required: true },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "category", label: "Category", type: "text" },
    { key: "unit_of_measure", label: "Unit of Measure", type: "text" },
    { key: "reorder_level", label: "Reorder Level", type: "number" },
    { key: "target_stock_level", label: "Target Stock Level", type: "number" },
    { key: "default_unit_cost", label: "Default Unit Cost", type: "currency" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
