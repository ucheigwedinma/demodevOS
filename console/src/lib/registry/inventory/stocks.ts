import { registerResource } from "../index";

registerResource({
  key: "stocks",
  module: "inventory",
  label: "Stock Level",
  labelPlural: "Stock Levels",
  endpoint: "/inventory/stocks/",
  columns: [
    { key: "warehouse", label: "Warehouse", type: "text" },
    { key: "item", label: "Item", type: "text" },
    { key: "quantity_on_hand", label: "Qty on Hand", type: "number" },
    { key: "quantity_reserved", label: "Qty Reserved", type: "number" },
    { key: "average_unit_cost", label: "Avg Unit Cost", type: "currency" },
    { key: "last_transaction_at", label: "Last Transaction", type: "datetime", sortable: true },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
