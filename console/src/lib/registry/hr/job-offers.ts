import { registerResource } from "../index";

registerResource({
  key: "job-offers",
  module: "hr",
  label: "Job Offer",
  labelPlural: "Job Offers",
  endpoint: "/hr/job-offers/",
  columns: [
    { key: "candidate", label: "Candidate", type: "text" },
    { key: "position", label: "Position", type: "text" },
    { key: "offered_salary", label: "Offered Salary", type: "currency" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "status", label: "Status", type: "badge" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search job offers..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "PENDING_APPROVAL", label: "Pending Approval" },
        { value: "APPROVED", label: "Approved" },
        { value: "EXTENDED", label: "Extended" },
        { value: "ACCEPTED", label: "Accepted" },
        { value: "REJECTED", label: "Rejected" },
        { value: "WITHDRAWN", label: "Withdrawn" },
        { value: "EXPIRED", label: "Expired" },
      ],
    },
  ],
  formFields: [
    { key: "candidate", label: "Candidate", type: "relation_picker", required: true, optionsEndpoint: "/hr/candidates/" },
    { key: "position", label: "Position", type: "relation_picker", optionsEndpoint: "/hr/positions/" },
    { key: "offered_salary", label: "Offered Salary", type: "currency", required: true },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    { key: "terms", label: "Terms", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
