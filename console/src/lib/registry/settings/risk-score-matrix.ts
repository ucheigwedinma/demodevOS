import { registerResource } from "../index";

registerResource({
  key: "risk-score-matrix",
  module: "settings",
  label: "Risk Score Matrix",
  labelPlural: "Configure the risk probability and impact scoring matrix",
  endpoint: "/settings/risk-score-matrix/",
  singleton: true,
  columns: [],
  formFields: [
    { key: "matrix_config", label: "Matrix Configuration", type: "textarea", gridSpan: 2, helpText: "JSON configuration for risk probability/impact matrix" },
  ],
});
