import { registerResource } from "../index";

registerResource({
  key: "campaigns",
  module: "crm",
  label: "Campaign",
  labelPlural: "Campaigns",
  endpoint: "/crm/campaigns/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "campaign_type", label: "Campaign Type", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "channel", label: "Channel", type: "badge" },
    { key: "total_recipients", label: "Total Recipients", type: "number" },
    { key: "sent_count", label: "Sent", type: "number" },
    { key: "opened_count", label: "Opened", type: "number" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search campaigns..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "DRAFT", label: "Draft" },
        { value: "SCHEDULED", label: "Scheduled" },
        { value: "RUNNING", label: "Running" },
        { value: "PAUSED", label: "Paused" },
        { value: "COMPLETED", label: "Completed" },
        { value: "CANCELLED", label: "Cancelled" },
      ],
    },
    {
      key: "campaign_type",
      label: "Campaign Type",
      type: "select",
      options: [
        { value: "EMAIL_BLAST", label: "Email Blast" },
        { value: "WHATSAPP_CAMPAIGN", label: "WhatsApp Campaign" },
        { value: "SMS_BLAST", label: "SMS Blast" },
        { value: "DRIP", label: "Drip" },
        { value: "FOLLOW_UP", label: "Follow Up" },
      ],
    },
  ],
  formFields: [
    { key: "name", label: "Name", type: "text", required: true },
    {
      key: "campaign_type",
      label: "Campaign Type",
      type: "select",
      options: [
        { value: "EMAIL_BLAST", label: "Email Blast" },
        { value: "WHATSAPP_CAMPAIGN", label: "WhatsApp Campaign" },
        { value: "SMS_BLAST", label: "SMS Blast" },
        { value: "DRIP", label: "Drip" },
        { value: "FOLLOW_UP", label: "Follow Up" },
      ],
    },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "EMAIL", label: "Email" },
        { value: "WHATSAPP", label: "WhatsApp" },
        { value: "SMS", label: "SMS" },
        { value: "PHONE", label: "Phone" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "subject", label: "Subject", type: "text" },
    { key: "scheduled_at", label: "Scheduled At", type: "datetime" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "body", label: "Body", type: "textarea", gridSpan: 2 },
  ],
});
