import { registerResource } from "../index";

registerResource({
  key: "distributions",
  module: "finance",
  label: "Distribution",
  labelPlural: "Distributions",
  endpoint: "/finance/distributions/",
  columns: [
    { key: "distribution_number", label: "Distribution #", type: "text", sortable: true },
    { key: "project", label: "Project", type: "text" },
    { key: "distribution_date", label: "Distribution Date", type: "date", sortable: true },
    { key: "total_amount", label: "Total Amount", type: "currency" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search distributions..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "CALCULATED", label: "Calculated" },
        { value: "APPROVED", label: "Approved" },
        { value: "DISTRIBUTED", label: "Distributed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "distribution_date", label: "Distribution Date", type: "date", required: true },
    { key: "total_amount", label: "Total Amount", type: "currency" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "CALCULATED", label: "Calculated" },
        { value: "APPROVED", label: "Approved" },
        { value: "DISTRIBUTED", label: "Distributed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
