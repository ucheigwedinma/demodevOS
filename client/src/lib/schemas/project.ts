import { z } from "zod";

export const projectSchema = z.object({
  property: z.number({ required_error: "Property is required" }),
  name: z.string().min(1, "Name is required").max(255),
  status: z.enum(["planning", "in_progress", "on_hold", "completed"]).default("planning"),
  number_of_units: z.number().int().min(0).nullable().default(null),
  start_date: z.string().nullable().default(null),
  target_end_date: z.string().nullable().default(null),
  actual_end_date: z.string().nullable().default(null),
  budget: z.string().nullable().default(null),
  project_manager: z.string().max(255).default(""),
  description: z.string().default(""),
  location: z.string().max(500).default(""),
  gps_latitude: z.number().min(-90).max(90).nullable().default(null),
  gps_longitude: z.number().min(-180).max(180).nullable().default(null),
});
export type ProjectFormData = z.infer<typeof projectSchema>;

export const phaseSchema = z.object({
  name: z.string().min(1, "Phase name is required").max(255),
  description: z.string().default(""),
  sort_order: z.number().int().min(0).default(0),
  status: z.enum(["not_started", "in_progress", "completed", "skipped"]).default("not_started"),
  planned_start_date: z.string().nullable().default(null),
  planned_end_date: z.string().nullable().default(null),
  actual_start_date: z.string().nullable().default(null),
  actual_end_date: z.string().nullable().default(null),
  planned_budget: z.string().nullable().default(null),
  weight: z.number().int().min(1).default(1),
});
export type PhaseFormData = z.infer<typeof phaseSchema>;

export const milestoneSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  description: z.string().default(""),
  target_date: z.string().nullable().default(null),
  completed_date: z.string().nullable().default(null),
  is_completed: z.boolean().default(false),
  sort_order: z.number().int().min(0).default(0),
});
export type MilestoneFormData = z.infer<typeof milestoneSchema>;

export const taskSchema = z.object({
  name: z.string().min(1, "Task name is required").max(255),
  description: z.string().default(""),
  status: z.enum(["pending", "in_progress", "completed"]).default("pending"),
  assigned_to: z.string().max(255).default(""),
  due_date: z.string().nullable().default(null),
  completed_date: z.string().nullable().default(null),
  sort_order: z.number().int().min(0).default(0),
});
export type TaskFormData = z.infer<typeof taskSchema>;

export const costEntrySchema = z.object({
  description: z.string().min(1, "Description is required").max(255),
  amount: z.string().min(1, "Amount is required"),
  date: z.string().min(1, "Date is required"),
  category: z.enum(["materials", "labor", "permits", "equipment", "subcontractor", "other"]).default("other"),
  vendor: z.string().max(255).default(""),
  reference_number: z.string().max(100).default(""),
});
export type CostEntryFormData = z.infer<typeof costEntrySchema>;
