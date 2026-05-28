import { registerResource } from "../index";

registerResource({
  key: "purchase-requisitions",
  module: "procurement",
  label: "Purchase Requisition",
  labelPlural: "Purchase Requisitions",
  endpoint: "/procurement/requisitions/",
  columns: [
    { key: "pr_number", label: "PR Number", type: "text", sortable: true },
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "status", label: "Status", type: "badge" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "requester", label: "Requester", type: "text" },
    { key: "required_date", label: "Required Date", type: "date", sortable: true },
    { key: "estimated_total", label: "Estimated Total", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search requisitions..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "CANCELLED", label: "Cancelled" },
        { value: "ORDERED", label: "Ordered" },
      ],
    },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
  ],
  formFields: [
    { key: "title", label: "Title", type: "text", required: true },
    { key: "requester", label: "Requester", type: "text" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "URGENT", label: "Urgent" },
      ],
    },
    { key: "required_date", label: "Required Date", type: "date" },
    { key: "estimated_total", label: "Estimated Total", type: "currency" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING", label: "Pending" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
        { value: "CANCELLED", label: "Cancelled" },
        { value: "ORDERED", label: "Ordered" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
