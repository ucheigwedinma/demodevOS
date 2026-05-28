import { registerResource } from "../index";

registerResource({
  key: "risk-register",
  module: "projects",
  label: "Risk Entry",
  labelPlural: "Risk Register",
  endpoint: "/projects/risk-register/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "project", label: "Project", type: "text" },
    { key: "severity", label: "Severity", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "treatment", label: "Treatment", type: "badge" },
    { key: "risk_score", label: "Risk Score", type: "number" },
    { key: "target_resolution_date", label: "Target Resolution", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search risk register..." },
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
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "MITIGATED", label: "Mitigated" },
        { value: "ACCEPTED", label: "Accepted" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
  ],
  formFields: [
    { key: "project", label: "Project", type: "relation_picker", required: true, optionsEndpoint: "/projects/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "risk_category", label: "Risk Category", type: "relation_picker", optionsEndpoint: "/settings/risk-categories/" },
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
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "MITIGATED", label: "Mitigated" },
        { value: "ACCEPTED", label: "Accepted" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    {
      key: "treatment",
      label: "Treatment",
      type: "select",
      options: [
        { value: "MITIGATE", label: "Mitigate" },
        { value: "AVOID", label: "Avoid" },
        { value: "TRANSFER", label: "Transfer" },
        { value: "ACCEPT", label: "Accept" },
      ],
    },
    { key: "target_resolution_date", label: "Target Resolution Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "mitigation_plan", label: "Mitigation Plan", type: "textarea", gridSpan: 2 },
  ],
});
