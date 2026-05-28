import { registerResource } from "../index";

registerResource({
  key: "valuation-appeals",
  module: "valuations",
  label: "Valuation Appeal",
  labelPlural: "Valuation Appeals",
  endpoint: "/valuations/appeals/",
  columns: [
    { key: "property", label: "Property", type: "text" },
    { key: "appeal_type", label: "Appeal Type", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "filed_date", label: "Filed Date", type: "date", sortable: true },
    { key: "assessed_value", label: "Assessed Value", type: "currency" },
    { key: "requested_value", label: "Requested Value", type: "currency" },
    { key: "decided_value", label: "Decided Value", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search appeals..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "FILED", label: "Filed" },
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "HEARD", label: "Heard" },
        { value: "DECIDED", label: "Decided" },
        { value: "WITHDRAWN", label: "Withdrawn" },
      ],
    },
  ],
  formFields: [
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "appeal_type", label: "Appeal Type", type: "text" },
    { key: "filed_date", label: "Filed Date", type: "date", required: true },
    { key: "hearing_date", label: "Hearing Date", type: "date" },
    { key: "assessed_value", label: "Assessed Value", type: "currency" },
    { key: "requested_value", label: "Requested Value", type: "currency" },
    { key: "filing_reference", label: "Filing Reference", type: "text" },
    { key: "representative", label: "Representative", type: "text" },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "FILED", label: "Filed" },
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "HEARD", label: "Heard" },
        { value: "DECIDED", label: "Decided" },
        { value: "WITHDRAWN", label: "Withdrawn" },
      ],
    },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
