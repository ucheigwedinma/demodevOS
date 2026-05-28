import { registerResource } from "../index";

registerResource({
  key: "transactions",
  module: "inventory",
  label: "Transaction",
  labelPlural: "Transactions",
  endpoint: "/inventory/transactions/",
  columns: [
    { key: "item", label: "Item", type: "text" },
    { key: "warehouse", label: "Warehouse", type: "text" },
    { key: "transaction_type", label: "Type", type: "badge" },
    { key: "quantity", label: "Quantity", type: "number" },
    { key: "unit_cost", label: "Unit Cost", type: "currency" },
    { key: "total_cost", label: "Total Cost", type: "currency" },
    { key: "transaction_date", label: "Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search transactions..." },
    {
      key: "transaction_type",
      label: "Type",
      type: "select",
      options: [
        { value: "RECEIPT", label: "Receipt" },
        { value: "ISSUE", label: "Issue" },
        { value: "TRANSFER", label: "Transfer" },
        { value: "ADJUSTMENT", label: "Adjustment" },
        { value: "RETURN", label: "Return" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
