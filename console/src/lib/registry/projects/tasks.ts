import { registerResource } from "../index";

registerResource({
  key: "tasks",
  module: "projects",
  label: "Task",
  labelPlural: "Tasks",
  endpoint: "/projects/tasks/",
  columns: [
    { key: "name", label: "Name", type: "text", sortable: true },
    { key: "phase", label: "Phase", type: "text" },
    { key: "work_package", label: "Work Package", type: "text" },
    { key: "priority", label: "Priority", type: "badge" },
    { key: "status", label: "Status", type: "badge" },
    { key: "assigned_to", label: "Assigned To", type: "text" },
    { key: "due_date", label: "Due Date", type: "date", sortable: true },
  ],
  filters: [
    { key: "search", label: "Search", type: "search", placeholder: "Search tasks..." },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
      ],
    },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
  ],
  formFields: [
    { key: "phase", label: "Phase", type: "relation_picker" },
    { key: "name", label: "Name", type: "text", required: true },
    { key: "work_package", label: "Work Package", type: "text" },
    {
      key: "priority",
      label: "Priority",
      type: "select",
      options: [
        { value: "LOW", label: "Low" },
        { value: "MEDIUM", label: "Medium" },
        { value: "HIGH", label: "High" },
        { value: "CRITICAL", label: "Critical" },
      ],
    },
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "PENDING", label: "Pending" },
        { value: "IN_PROGRESS", label: "In Progress" },
        { value: "COMPLETED", label: "Completed" },
      ],
    },
    { key: "assigned_to", label: "Assigned To", type: "text" },
    { key: "due_date", label: "Due Date", type: "date" },
    { key: "description", label: "Description", type: "textarea", gridSpan: 2 },
  ],
});
