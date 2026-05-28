import { registerResource } from "../index";

registerResource({
  key: "violations",
  module: "compliance",
  label: "Violation",
  labelPlural: "Violations",
  endpoint: "/compliance/violations/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "property", label: "Property", type: "text" },
    { key: "violation_type", label: "Type", type: "badge" },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "reported_date", label: "Reported Date", type: "date", sortable: true },
    { key: "due_date", label: "Due Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search violations..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "INVESTIGATING", label: "Investigating" },
        { value: "REMEDIATED", label: "Remediated" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
  ],
  formFields: [
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "compliance_item", label: "Compliance Item", type: "relation_picker", optionsEndpoint: "/compliance/tracker/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "violation_type", label: "Violation Type", type: "text" },
    {
      key: "severity",
      label: "Severity",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "OPEN", label: "Open" },
        { value: "INVESTIGATING", label: "Investigating" },
        { value: "REMEDIATED", label: "Remediated" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    { key: "reported_date", label: "Reported Date", type: "date", required: true },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "fine_amount", label: "Fine Amount", type: "currency" },
    { key: "assigned_to", label: "Assigned To", type: "text" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "corrective_action", label: "Corrective Action", type: "textarea", gridSpan: 2 },
  ],
});
