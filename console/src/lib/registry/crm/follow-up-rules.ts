import { registerResource } from "../index";

registerResource({
  key: "follow-up-rules",
  module: "crm",
  label: "Follow-up Rule",
  labelPlural: "Follow-up Rules",
  endpoint: "/crm/follow-up-rules/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "trigger_stage", label: "Trigger Stage", type: "badge" },
    { key: "follow_up_within_hours", label: "Follow-up Within (Hours)", type: "number" },
    { key: "required_activity_type", label: "Required Activity Type", type: "text" },
    { key: "is_active", label: "Active", type: "boolean" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search follow-up rules..." },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "trigger_stage",
      label: "Trigger Stage",
      type: "select",
      options: [
        { value: "INQUIRY", label: "Inquiry" },
        { value: "QUALIFIED", label: "Qualified" },
        { value: "SITE_VISIT", label: "Site Visit" },
        { value: "OFFER_MADE", label: "Offer Made" },
        { value: "RESERVATION", label: "Reservation" },
        { value: "SPA_ISSUED", label: "SPA Issued" },
        { value: "CLOSED", label: "Closed" },
      ],
    },
    { key: "follow_up_within_hours", label: "Follow-up Within (Hours)", type: "number", required: true },
    {
      key: "required_activity_type",
      label: "Required Activity Type",
      type: "select",
      options: [
        { value: "CALL", label: "Call" },
        { value: "EMAIL", label: "Email" },
        { value: "MEETING", label: "Meeting" },
        { value: "SITE_VISIT", label: "Site Visit" },
        { value: "NOTE", label: "Note" },
        { value: "FOLLOW_UP", label: "Follow Up" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "auto_assign_to_owner", label: "Auto-assign to Owner", type: "boolean", defaultValue: true },
    { key: "is_active", label: "Active", type: "boolean", defaultValue: true },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
