import { registerResource } from "../index";

registerResource({
  key: "comparable-sales",
  module: "valuations",
  label: "Comparable Sale",
  labelPlural: "Comparable Sales",
  endpoint: "/valuations/comparables/",
  columns: [
    { key: "property", label: "Property", type: "text" },
    { key: "address", label: "Address", type: "text" },
    { key: "sale_date", label: "Sale Date", type: "date", sortable: true },
    { key: "sale_price", label: "Sale Price", type: "currency" },
    { key: "property_type", label: "Property Type", type: "text" },
    { key: "area_sqft", label: "Area (sqft)", type: "number" },
    { key: "price_per_sqft", label: "Price/sqft", type: "currency" },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search comparable sales..." },
  ],
  formFields: [
    { key: "property", label: "Property", type: "relation_picker", required: true, optionsEndpoint: "/properties/" },
    { key: "address", label: "Address", type: "text", required: true },
    { key: "sale_date", label: "Sale Date", type: "date", required: true },
    { key: "sale_price", label: "Sale Price", type: "currency", required: true },
    { key: "property_type", label: "Property Type", type: "text" },
    { key: "area_sqft", label: "Area (sqft)", type: "number" },
    { key: "proximity_km", label: "Proximity (km)", type: "number" },
    { key: "source", label: "Source", type: "text" },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
