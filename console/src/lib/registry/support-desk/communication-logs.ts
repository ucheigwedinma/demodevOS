import { registerResource } from "../index";

registerResource({
  key: "communication-logs",
  module: "support-desk",
  label: "Communication Log",
  labelPlural: "Communication Logs",
  endpoint: "/support-desk/communication/logs/",
  columns: [
    { key: "ticket", label: "Ticket", type: "text" },
    { key: "author", label: "Author", type: "text" },
    { key: "interaction_type", label: "Interaction Type", type: "badge" },
    { key: "direction", label: "Direction", type: "badge" },
    { key: "channel", label: "Channel", type: "badge" },
    { key: "subject", label: "Subject", type: "text" },
    { key: "happened_at", label: "Happened At", type: "datetime", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search communication logs..." },
    {
      key: "channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "EMAIL", label: "Email" },
        { value: "PHONE", label: "Phone" },
        { value: "CHAT", label: "Chat" },
        { value: "PORTAL", label: "Portal" },
        { value: "INTERNAL_NOTE", label: "Internal Note" },
      ],
    },
  ],
  canCreate: false,
  canEdit: false,
  canDelete: false,
});
