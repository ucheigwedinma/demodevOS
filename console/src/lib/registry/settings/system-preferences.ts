import { registerResource } from "../index";

registerResource({
  key: "system-preferences",
  module: "settings",
  label: "System Preferences",
  labelPlural: "Theme, localization, currency, and display settings",
  endpoint: "/settings/preferences/",
  singleton: true,
  columns: [],
  formSections: [
    { key: "display", label: "Display" },
    { key: "localization", label: "Localization" },
    { key: "currency", label: "Currency" },
  ],
  formFields: [
    {
      key: "theme_mode",
      label: "Theme Mode",
      type: "select",
      options: [
        { value: "light", label: "Light" },
        { value: "dark", label: "Dark" },
        { value: "auto", label: "Auto" },
      ],
      section: "display",
    },
    { key: "accent_color", label: "Accent Color", type: "text", placeholder: "#hexcolor", section: "display" },
    { key: "date_format", label: "Date Format", type: "text", placeholder: "YYYY-MM-DD", section: "localization" },
    { key: "number_format", label: "Number Format", type: "text", section: "localization" },
    { key: "measurement_unit", label: "Measurement Unit", type: "text", section: "localization" },
    { key: "default_currency", label: "Default Currency", type: "text", defaultValue: "USD", section: "currency" },
    { key: "currency_position", label: "Currency Position", type: "text", section: "currency" },
    { key: "currency_decimal_places", label: "Decimal Places", type: "number", defaultValue: 2, section: "currency" },
  ],
});
