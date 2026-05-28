import { registerResource } from "../index";

registerResource({
  key: "entitlements",
  module: "partners",
  label: "Entitlement",
  labelPlural: "Entitlements",
  endpoint: "/partners/entitlements/",
  columns: [
    { key: "case", label: "Case", type: "text" },
    { key: "portal_role", label: "Portal Role", type: "text" },
    { key: "project", label: "Project", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "effective_from", label: "Effective From", type: "date" },
    { key: "expires_at", label: "Expires At", type: "date" },
  ],
  formFields: [
    { key: "case", label: "Case", type: "relation_picker", required: true, optionsEndpoint: "/partners/cases/" },
    {
      key: "portal_role",
      label: "Portal Role",
      type: "select",
      options: [
        { value: "VIEWER", label: "Viewer" },
        { value: "CONTRIBUTOR", label: "Contributor" },
        { value: "APPROVER", label: "Approver" },
        { value: "ADMIN", label: "Admin" },
      ],
    },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "can_view_other_investors", label: "Can View Other Investors", type: "boolean" },
    { key: "can_edit", label: "Can Edit", type: "boolean" },
    { key: "can_approve", label: "Can Approve", type: "boolean" },
    { key: "can_comment", label: "Can Comment", type: "boolean" },
    { key: "can_download_documents", label: "Can Download Documents", type: "boolean" },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "effective_from", label: "Effective From", type: "date" },
    { key: "expires_at", label: "Expires At", type: "date" },
  ],
});
