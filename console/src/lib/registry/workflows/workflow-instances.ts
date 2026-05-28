import { registerResource } from "../index";

registerResource({
  key: "workflow-instances",
  module: "workflows",
  label: "Workflow Instance",
  labelPlural: "Workflow Instances",
  endpoint: "/workflows/instances/",
  columns: [
    { key: "content_type", label: "Content Type", type: "text" },
    { key: "object_id", label: "Object ID", type: "number" },
    { key: "template", label: "Template", type: "text" },
    { key: "state", label: "State", type: "badge" },
    { key: "submitted_by", label: "Submitted By", type: "text" },
    { key: "submitted_at", label: "Submitted At", type: "datetime", sortable: true },
    { key: "completed_at", label: "Completed At", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search workflow instances..." },
    {
      key: "state",
      label: "State",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SUBMITTED", label: "Submitted" },
        { value: "UNDER_REVIEW", label: "Under Review" },
        { value: "APPROVED", label: "Approved" },
        { value: "REJECTED", label: "Rejected" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
