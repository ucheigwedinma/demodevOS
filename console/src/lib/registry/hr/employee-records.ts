import { registerResource } from "../index";

registerResource({
  key: "employee-records",
  module: "hr",
  label: "Employee Record",
  labelPlural: "Employee Records",
  endpoint: "/hr/employee-records/",
  columns: [
    { key: "user", label: "User", type: "text" },
    { key: "hire_date", label: "Hire Date", type: "date", sortable: true },
    { key: "employment_status", label: "Status", type: "badge" },
    { key: "contract_type", label: "Contract Type", type: "text" },
    { key: "probation_end_date", label: "Probation End", type: "date" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search employee records..." },
    {
      key: "employment_status",
      label: "Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "PROBATION", label: "Probation" },
        { value: "SUSPENDED", label: "Suspended" },
        { value: "TERMINATED", label: "Terminated" },
        { value: "RESIGNED", label: "Resigned" },
      ],
    },
  ],
  formFields: [
    { key: "user", label: "User", type: "relation_picker", required: true, optionsEndpoint: "/iam/users/" },
    { key: "hire_date", label: "Hire Date", type: "date" },
    { key: "contract_type", label: "Contract Type", type: "text" },
    {
      key: "employment_status",
      label: "Employment Status",
      type: "select",
      options: [
        { value: "ACTIVE", label: "Active" },
        { value: "PROBATION", label: "Probation" },
        { value: "SUSPENDED", label: "Suspended" },
        { value: "TERMINATED", label: "Terminated" },
        { value: "RESIGNED", label: "Resigned" },
      ],
    },
    { key: "contract_start_date", label: "Contract Start Date", type: "date" },
    { key: "contract_end_date", label: "Contract End Date", type: "date" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
  canDelete: false,
});
