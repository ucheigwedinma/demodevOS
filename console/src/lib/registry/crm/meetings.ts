import { registerResource } from "../index";

registerResource({
  key: "meetings",
  module: "crm",
  label: "Meeting",
  labelPlural: "Meetings",
  endpoint: "/crm/meetings/",
  columns: [
    { key: "title", label: "Title", type: "text", sortable: true },
    { key: "lead", label: "Lead", type: "text" },
    { key: "meeting_type", label: "Meeting Type", type: "badge" },
    { key: "outcome", label: "Outcome", type: "badge" },
    { key: "scheduled_start", label: "Scheduled Start", type: "datetime", sortable: true },
    { key: "organized_by", label: "Organized By", type: "text" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search meetings..." },
    {
      key: "meeting_type",
      label: "Meeting Type",
      type: "select",
      options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "VIDEO_CALL", label: "Video Call" },
        { value: "PHONE_CONFERENCE", label: "Phone Conference" },
        { value: "SITE_VISIT", label: "Site Visit" },
      ],
    },
    {
      key: "outcome",
      label: "Outcome",
      type: "select",
      options: [
        { value: "POSITIVE", label: "Positive" },
        { value: "NEUTRAL", label: "Neutral" },
        { value: "NEGATIVE", label: "Negative" },
        { value: "FOLLOW_UP_NEEDED", label: "Follow-Up Needed" },
        { value: "NO_SHOW", label: "No Show" },
      ],
    },
  ],
  formFields: [
    { key: "lead", label: "Lead", type: "relation_picker", required: true, optionsEndpoint: "/crm/leads/" },
    { key: "title", label: "Title", type: "text", required: true },
    {
      key: "meeting_type",
      label: "Meeting Type",
      type: "select",
      options: [
        { value: "IN_PERSON", label: "In Person" },
        { value: "VIDEO_CALL", label: "Video Call" },
        { value: "PHONE_CONFERENCE", label: "Phone Conference" },
        { value: "SITE_VISIT", label: "Site Visit" },
      ],
    },
    { key: "scheduled_start", label: "Scheduled Start", type: "datetime", required: true },
    { key: "scheduled_end", label: "Scheduled End", type: "datetime", required: true },
    { key: "location", label: "Location", type: "text" },
    { key: "meeting_link", label: "Meeting Link", type: "text" },
    { key: "organized_by", label: "Organized By", type: "relation_picker", optionsEndpoint: "/iam/users/" },
    { key: "project", label: "Project", type: "relation_picker", optionsEndpoint: "/projects/" },
    { key: "agenda", label: "Agenda", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
