import { registerResource } from "../index";

registerResource({
  key: "equipment-allocations",
  module: "hr",
  label: "Equipment Allocation",
  labelPlural: "Equipment Allocations",
  endpoint: "/hr/equipment-allocations/",
  columns: [
    { key: "employee", label: "Employee", type: "text" },
    { key: "item_name", label: "Item Name", type: "text", sortable: true },
    { key: "category", label: "Category", type: "badge" },
    { key: "serial_number", label: "Serial Number", type: "text" },
    { key: "status", label: "Status", type: "badge" },
    { key: "allocated_date", label: "Allocated Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "ALLOCATED", label: "Allocated" },
        { value: "RETURNED", label: "Returned" },
        { value: "LOST", label: "Lost" },
      ],
    },
    {
      key: "category",
      label: "Category",
      type: "select",
      options: [
        { value: "LAPTOP", label: "Laptop" },
        { value: "PHONE", label: "Phone" },
        { value: "ACCESS_CARD", label: "Access Card" },
        { value: "DESK", label: "Desk" },
        { value: "VEHICLE", label: "Vehicle" },
        { value: "UNIFORM", label: "Uniform" },
        { value: "OTHER", label: "Other" },
      ],
    },
  ],
  formFields: [
    { key: "employee", label: "Employee", type: "relation_picker", required: true, optionsEndpoint: "/hr/employee-records/" },
    { key: "item_name", label: "Item Name", type: "text", required: true },
    {
      key: "category", label: "Category", type: "select", options: [
        { value: "LAPTOP", label: "Laptop" },
        { value: "PHONE", label: "Phone" },
        { value: "ACCESS_CARD", label: "Access Card" },
        { value: "DESK", label: "Desk" },
        { value: "VEHICLE", label: "Vehicle" },
        { value: "UNIFORM", label: "Uniform" },
        { value: "OTHER", label: "Other" },
      ],
    },
    { key: "serial_number", label: "Serial Number", type: "text" },
    { key: "asset_tag", label: "Asset Tag", type: "text" },
    {
      key: "status", label: "Status", type: "select", options: [
        { value: "PENDING", label: "Pending" },
        { value: "ALLOCATED", label: "Allocated" },
        { value: "RETURNED", label: "Returned" },
        { value: "LOST", label: "Lost" },
      ],
    },
    { key: "allocated_date", label: "Allocated Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
    { key: "notes", label: "Notes", type: "textarea", gridSpan: 2 },
  ],
});
