import { registerResource } from "../index";

registerResource({
  key: "salary-structures",
  module: "hr",
  label: "Salary Structure",
  labelPlural: "Salary Structures",
  endpoint: "/hr/salary-structures/",
  columns: [
    { key: "id", label: "ID", type: "number", width: "w-16" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "grade_level", label: "Grade Level", type: "number" },
    { key: "min_salary", label: "Min Salary", type: "currency" },
    { key: "max_salary", label: "Max Salary", type: "currency" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "grade_level", label: "Grade Level", type: "number" },
    { key: "min_salary", label: "Min Salary", type: "currency", required: true },
    { key: "max_salary", label: "Max Salary", type: "currency", required: true },
    { key: "currency", label: "Currency", type: "text", defaultValue: "USD" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
