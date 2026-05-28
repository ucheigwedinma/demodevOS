import { registerResource } from "../index";

registerResource({
  key: "teams",
  module: "hr",
  label: "Team",
  labelPlural: "Teams",
  endpoint: "/hr/teams/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "code", label: "Code", type: "text" },
    { key: "department", label: "Department", type: "text" },
    { key: "lead", label: "Lead", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search teams..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "code", label: "Code", type: "text", required: true },
    { key: "department", label: "Department", type: "relation_picker", optionsEndpoint: "/settings/departments/" },
    { key: "lead", label: "Lead", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
  ],
});
