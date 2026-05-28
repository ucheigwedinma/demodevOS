import { registerResource } from "../index";

registerResource({
  key: "job-listings",
  module: "hr",
  label: "Job Listing",
  labelPlural: "Job Listings",
  endpoint: "/hr/job-listings/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "requisition", label: "Requisition", type: "text" },
    { key: "location", label: "Location", type: "text" },
    { key: "employment_type", label: "Employment Type", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "posted_date", label: "Posted Date", type: "date", sortable: true },
    { key: "closing_date", label: "Closing Date", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search job listings..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "ACTIVE", label: "Active" },
        { value: "CLOSED", label: "Closed" },
        { value: "ARCHIVED", label: "Archived" },
      ],
    },
  ],
  formFields: [
    { key: "requisition", label: "Requisition", type: "relation_picker", required: true, optionsEndpoint: "/hr/requisitions/" },
    { key: "title", label: "Title", type: "text", required: true },
    { key: "location", label: "Location", type: "text" },
    {
      key: "employment_type",
      label: "Employment Type",
      type: "select",
      options: [
        { value: "FULL_TIME", label: "Full Time" },
        { value: "PART_TIME", label: "Part Time" },
        { value: "CONTRACT", label: "Contract" },
        { value: "INTERN", label: "Intern" },
      ],
    },
    {
      key: "salary_display",
      label: "Salary Display",
      type: "select",
      options: [
        { value: "HIDDEN", label: "Hidden" },
        { value: "RANGE", label: "Range" },
        { value: "EXACT", label: "Exact" },
      ],
    },
    { key: "is_internal", label: "Internal", type: "boolean" },
    { key: "is_external", label: "External", type: "boolean", defaultValue: true },
    { key: "posted_date", label: "Posted Date", type: "date" },
    { key: "closing_date", label: "Closing Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "requirements", label: "Requirements", type: "textarea", gridSpan: 2 },
  ],
});
