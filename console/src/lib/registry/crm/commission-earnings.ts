import { registerResource } from "../index";

registerResource({
  key: "commission-earnings",
  module: "crm",
  label: "Commission Earning",
  labelPlural: "Commission Earnings",
  endpoint: "/crm/commission-earnings/",
  columns: [
    { key: "broker", label: "Broker", type: "text" },
    { key: "lead", label: "Lead", type: "text" },
    { key: "project", label: "Project", type: "text" },
    { key: "deal_value", label: "Deal Value", type: "currency" },
    { key: "total_commission", label: "Total Commission", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
    { key: "triggered_at", label: "Triggered At", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search commission earnings..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "PROCESSING", label: "Processing" },
        { value: "PAID", label: "Paid" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  canCreate: false,
  canDelete: false,
});
