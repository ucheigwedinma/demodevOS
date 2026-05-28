import { registerResource } from "../index";

registerResource({
  key: "communications",
  module: "crm",
  label: "Communication",
  labelPlural: "Communications",
  endpoint: "/crm/communications/",
  columns: [
    { key: "lead", label: "Lead", type: "text" },
    { key: "channel", label: "Channel", type: "badge" },
    { key: "direction", label: "Direction", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "subject", label: "Subject", type: "text" },
    { key: "performed_by", label: "Performed By", type: "text" },
    { key: "communicated_at", label: "Communicated At", type: "datetime" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search communications..." },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "EMAIL", label: "Email" },
        { value: "WHATSAPP", label: "WhatsApp" },
        { value: "SMS", label: "SMS" },
        { value: "PHONE", label: "Phone" },
        { value: "VIDEO_CALL", label: "Video Call" },
        { value: "IN_PERSON", label: "In Person" },
        { value: "OTHER", label: "Other" },
      ],
    },
    {
      key: "direction",
      label: "Direction",
      type: "select",
      options: [
        { value: "INBOUND", label: "Inbound" },
        { value: "OUTBOUND", label: "Outbound" },
      ],
    },
  ],
  formFields: [
    { key: "lead", label: "Lead", type: "relation_picker", required: true, optionsEndpoint: "/crm/leads/" },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "EMAIL", label: "Email" },
        { value: "WHATSAPP", label: "WhatsApp" },
        { value: "SMS", label: "SMS" },
        { value: "PHONE", label: "Phone" },
        { value: "VIDEO_CALL", label: "Video Call" },
        { value: "IN_PERSON", label: "In Person" },
        { value: "OTHER", label: "Other" },
      ],
    },
    {
      key: "direction",
      label: "Direction",
      type: "select",
      options: [
        { value: "INBOUND", label: "Inbound" },
        { value: "OUTBOUND", label: "Outbound" },
      ],
    },
    { key: "subject", label: "Subject", type: "text", required: true },
    { key: "body", label: "Body", type: "textarea", gridSpan: 2 },
    { key: "summary", label: "Summary", type: "textarea", gridSpan: 2 },
  ],
});
