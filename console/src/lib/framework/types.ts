import type { z } from "zod";

export interface ColumnDef {
  key: string;
  label: string;
  type: "text" | "number" | "date" | "datetime" | "currency" | "badge" | "boolean" | "link" | "relation";
  sortable?: boolean;
  width?: string;
  linkTo?: string;
  hidden?: boolean;
}

export interface FilterDef {
  key: string;
  label: string;
  type: "search" | "select" | "date_range" | "boolean" | "multi_select";
  options?: { value: string; label: string }[];
  optionsEndpoint?: string;
  placeholder?: string;
}

export interface FormFieldDef {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "date" | "datetime" | "select" | "multi_select" | "boolean" | "file" | "currency" | "relation_picker" | "readonly";
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  options?: { value: string; label: string }[];
  optionsEndpoint?: string;
  defaultValue?: unknown;
  gridSpan?: 1 | 2;
  section?: string;
  showIf?: (data: Record<string, unknown>) => boolean;
}

export interface ResourceAction {
  key: string;
  label: string;
  variant: "primary" | "secondary" | "danger";
  endpoint: string;
  method?: "POST" | "PATCH" | "DELETE";
  confirmMessage?: string;
  requiresSelection?: boolean;
}

export interface ResourceConfig {
  key: string;
  module: string;
  label: string;
  labelPlural: string;
  endpoint: string;
  parentEndpoint?: string;
  parentParam?: string;

  /** Singleton resources have no list view — just a form that GETs and PATCHes */
  singleton?: boolean;

  columns: ColumnDef[];
  defaultSort?: string;
  pageSize?: number;
  searchable?: boolean;
  filters?: FilterDef[];

  formFields?: FormFieldDef[];
  formSchema?: z.ZodSchema;
  formSections?: { key: string; label: string }[];

  actions?: ResourceAction[];
  bulkActions?: ResourceAction[];
  canCreate?: boolean;
  canEdit?: boolean;
  canDelete?: boolean;

  detailSections?: {
    key: string;
    label: string;
    fields: { key: string; label: string; type: ColumnDef["type"] }[];
  }[];
  relatedResources?: {
    resourceKey: string;
    label: string;
    foreignKey: string;
  }[];

  superAdminOnly?: boolean;
}

export interface PaginatedResponse<T = Record<string, unknown>> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
