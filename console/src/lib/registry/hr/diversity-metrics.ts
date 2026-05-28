import { registerResource } from "../index";

registerResource({
  key: "diversity-metrics",
  module: "hr",
  label: "Diversity Metric",
  labelPlural: "Diversity Metrics",
  endpoint: "/hr/diversity-metrics/",
  columns: [
    { key: "snapshot_date", label: "Snapshot Date", type: "date" },
    { key: "department", label: "Department", type: "text" },
    { key: "dimension", label: "Dimension", type: "badge" },
    { key: "category_value", label: "Category Value", type: "text" },
    { key: "count", label: "Count", type: "number" },
    { key: "percentage", label: "Percentage", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "dimension",
      label: "Dimension",
      type: "select",
      options: [
        { value: "GENDER", label: "Gender" },
        { value: "AGE_GROUP", label: "Age Group" },
        { value: "ETHNICITY", label: "Ethnicity" },
        { value: "NATIONALITY", label: "Nationality" },
        { value: "DISABILITY", label: "Disability" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
