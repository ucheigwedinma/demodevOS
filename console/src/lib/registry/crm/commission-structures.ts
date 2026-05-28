import { registerResource } from "../index";

registerResource({
  key: "commission-structures",
  module: "crm",
  label: "Commission Structure",
  labelPlural: "Commission Structures",
  endpoint: "/crm/commission-structures/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "commission_type", label: "Commission Type", type: "badge" },
    { key: "base_rate", label: "Base Rate", type: "number" },
    { key: "trigger_stage", label: "Trigger Stage", type: "text" },
    { key: "broker", label: "Broker", type: "text" },
    { key: "project", label: "Project", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search commission structures..." },
    {
      key: "commission_type",
      label: "Commission Type",
      type: "select",
      options: [
        { value: "PERCENTAGE", label: "Percentage" },
        { value: "FIXED", label: "Fixed" },
        { value: "TIERED", label: "Tiered" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "commission_type",
      label: "Commission Type",
      type: "select",
      options: [
        { value: "PERCENTAGE", label: "Percentage" },
        { value: "FIXED", label: "Fixed" },
        { value: "TIERED", label: "Tiered" },
      ],
    },
    { key: "base_rate", label: "Base Rate", type: "number" },
    { key: "fixed_amount", label: "Fixed Amount", type: "currency" },
    {
      key: "trigger_stage",
      label: "Trigger Stage",
      type: "select",
      options: [
        { value: "RESERVATION", label: "Reservation" },
        { value: "SPA_ISSUED", label: "SPA Issued" },
        { value: "CLOSED", label: "Closed" },
        { value: "MILESTONE", label: "Milestone" },
      ],
    },
    {
      key: "payment_split",
      label: "Payment Split",
      type: "select",
      options: [
        { value: "UPFRONT", label: "Upfront" },
        { value: "SPLIT_50_50", label: "Split 50/50" },
        { value: "SPLIT_30_70", label: "Split 30/70" },
        { value: "MILESTONE", label: "Milestone" },
      ],
    },
    { key: "broker", label: "Broker", type: "relation_picker", optionsEndpoint: "/crm/brokers/" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "is_default", label: "Default", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "effective_from", label: "Effective From", type: "date" },
    { key: "effective_to", label: "Effective To", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
