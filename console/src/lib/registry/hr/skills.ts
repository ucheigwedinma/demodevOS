import { registerResource } from "../index";

registerResource({
  key: "skills",
  module: "hr",
  label: "Skill",
  labelPlural: "Skills",
  endpoint: "/hr/skills/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "category", label: "Category", type: "badge" },
    { key: "proficiency", label: "Proficiency", type: "badge" },
    { key: "years_experience", label: "Years Experience", type: "number" },
    { key: "verified", label: "Verified", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "TECHNICAL", label: "Technical" },
        { value: "MANAGEMENT", label: "Management" },
        { value: "SOFT", label: "Soft" },
        { value: "DOMAIN", label: "Domain" },
        { value: "REGULATORY", label: "Regulatory" },
      ],
    },
    {
      key: "proficiency",
      label: "Proficiency",
      type: "select",
      options: [
        { value: "BEGINNER", label: "Beginner" },
        { value: "INTERMEDIATE", label: "Intermediate" },
        { value: "ADVANCED", label: "Advanced" },
        { value: "EXPERT", label: "Expert" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "category", label: "Category", type: "select", options: [
        { value: "TECHNICAL", label: "Technical" },
        { value: "MANAGEMENT", label: "Management" },
        { value: "SOFT", label: "Soft" },
        { value: "DOMAIN", label: "Domain" },
        { value: "REGULATORY", label: "Regulatory" },
      ],
    },
    {
      key: "proficiency", label: "Proficiency", type: "select", options: [
        { value: "BEGINNER", label: "Beginner" },
        { value: "INTERMEDIATE", label: "Intermediate" },
        { value: "ADVANCED", label: "Advanced" },
        { value: "EXPERT", label: "Expert" },
      ],
    },
    { key: "years_experience", label: "Years Experience", type: "number" },
    { key: "is_primary", label: "Primary", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
