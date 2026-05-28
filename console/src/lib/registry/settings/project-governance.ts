import { registerResource } from "../index";

registerResource({
  key: "project-governance",
  module: "settings",
  label: "Project Governance",
  labelPlural: "Project governance enforcement and template requirements",
  endpoint: "/settings/project-governance/",
  singleton: true,
  columns: [],
  formFields: [
    { key: "stage_gate_enforcement_enabled", label: "Stage-Gate Enforcement Enabled", type: "boolean" },
    { key: "require_template_selection", label: "Require Template Selection", type: "boolean" },
    { key: "risk_assessment_mandatory", label: "Risk Assessment Mandatory", type: "boolean" },
  ],
});
