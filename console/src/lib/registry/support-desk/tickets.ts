import { registerResource } from "../index";

registerResource({
  key: "tickets",
  module: "support-desk",
  label: "Ticket",
  labelPlural: "Tickets",
  endpoint: "/support-desk/tickets/",
  columns: [
    { key: "ticket_id", label: "Ticket ID", type: "text", sortable: true },
    { key: "subject", label: "Subject", type: "text", sortable: true },
    { key: "requester", label: "Requester", type: "text" },
    { key: "category", label: "Category", type: "badge" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "assigned_agent", label: "Assigned Agent", type: "text" },
    { key: "sla_deadline", label: "SLA Deadline", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search tickets..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "WAITING", label: "Waiting" },
        { value: "RESOLVED", label: "Resolved" },
        { value: "CLOSED", label: "Closed" },
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
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "BUG", label: "Bug" },
        { value: "FEATURE_REQUEST", label: "Feature Request" },
        { value: "GENERAL", label: "General" },
        { value: "ACCOUNT", label: "Account" },
        { value: "BILLING", label: "Billing" },
      ],
    },
  ],
  formFields: [
    { key: "subject", label: "Subject", type: "text", required: true },
    { key: "requester", label: "Requester", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "BUG", label: "Bug" },
        { value: "FEATURE_REQUEST", label: "Feature Request" },
        { value: "GENERAL", label: "General" },
        { value: "ACCOUNT", label: "Account" },
        { value: "BILLING", label: "Billing" },
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
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    { key: "assigned_agent", label: "Assigned Agent", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2, required: true },
  ],
});
