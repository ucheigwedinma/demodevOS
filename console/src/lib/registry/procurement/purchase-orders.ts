import { registerResource } from "../index";

registerResource({
  key: "purchase-orders",
  module: "procurement",
  label: "Purchase Order",
  labelPlural: "Purchase Orders",
  endpoint: "/procurement/purchase-orders/",
  columns: [
    { key: "po_number", label: "PO Number", type: "text", sortable: true },
    { key: "vendor", label: "Vendor", type: "text" },
    { key: "project", label: "Project", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "issue_date", label: "Issue Date", type: "date", sortable: true },
    { key: "expected_delivery_date", label: "Expected Delivery", type: "date" },
    { key: "total_amount", label: "Total Amount", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search purchase orders..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ISSUED", label: "Issued" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
        { value: "PARTIALLY_RECEIVED", label: "Partially Received" },
        { value: "RECEIVED", label: "Received" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "requisition", label: "Requisition", type: "relation_picker", optionsEndpoint: "/procurement/requisitions/" },
    { key: "vendor", label: "Vendor", type: "relation_picker", required: true, optionsEndpoint: "/procurement/vendors/" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "expected_delivery_date", label: "Expected Delivery Date", type: "date" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ISSUED", label: "Issued" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
        { value: "PARTIALLY_RECEIVED", label: "Partially Received" },
        { value: "RECEIVED", label: "Received" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
