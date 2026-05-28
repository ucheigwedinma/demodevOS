import { registerResource } from "../index";

registerResource({
  key: "goods-receipts",
  module: "procurement",
  label: "Goods Receipt",
  labelPlural: "Goods Receipts",
  endpoint: "/procurement/goods-receipts/",
  columns: [
    { key: "grn_number", label: "GRN Number", type: "text", sortable: true },
    { key: "purchase_order", label: "Purchase Order", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "received_date", label: "Received Date", type: "date", sortable: true },
    { key: "received_by", label: "Received By", type: "text" },
    { key: "delivery_note_number", label: "Delivery Note", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search goods receipts..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "RECEIVED", label: "Received" },
        { value: "INSPECTED", label: "Inspected" },
        { value: "ACCEPTED", label: "Accepted" },
        { value: "REJECTED", label: "Rejected" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
