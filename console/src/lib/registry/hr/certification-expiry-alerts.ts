import { registerResource } from "../index";

registerResource({
  key: "certification-expiry-alerts",
  module: "hr",
  label: "Certification Expiry Alert",
  labelPlural: "Certification Expiry Alerts",
  endpoint: "/hr/certification-expiry-alerts/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "employee", label: "Employee", type: "text" },
    { key: "alert_type", label: "Alert Type", type: "badge" },
    { key: "reference_name", label: "Reference", type: "text" },
    { key: "expiry_date", label: "Expiry Date", type: "date", sortable: true },
    { key: "alert_date", label: "Alert Date", type: "date" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search alerts..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "SENT", label: "Sent" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
        { value: "RENEWED", label: "Renewed" },
        { value: "EXPIRED", label: "Expired" },
      ],
    },
    {
      key: "alert_type",
      label: "Alert Type",
      type: "select",
      options: [
        { value: "CERTIFICATION", label: "Certification" },
        { value: "LICENSE", label: "License" },
        { value: "TRAINING", label: "Training" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    {
      key: "alert_type",
      label: "Alert Type",
      type: "select",
      options: [
        { value: "CERTIFICATION", label: "Certification" },
        { value: "LICENSE", label: "License" },
        { value: "TRAINING", label: "Training" },
      ],
    },
    { key: "reference_name", label: "Reference Name", type: "text", required: true },
    { key: "expiry_date", label: "Expiry Date", type: "date", required: true },
    { key: "alert_date", label: "Alert Date", type: "date", required: true },
    { key: "days_before_expiry", label: "Days Before Expiry", type: "number" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "SENT", label: "Sent" },
        { value: "ACKNOWLEDGED", label: "Acknowledged" },
        { value: "RENEWED", label: "Renewed" },
        { value: "EXPIRED", label: "Expired" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
