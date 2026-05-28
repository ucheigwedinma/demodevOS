import { z } from "zod";

export const propertySchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  property_type: z.enum(["land", "building", "mixed", "estate", "warehouse", "industrial"]),
  classification: z.enum(["owned", "lease", "concession", "under_development"]).default("owned"),
  address: z.string().min(1, "Address is required"),
  description: z.string().default(""),
  gps_latitude: z.string().nullable().default(null),
  gps_longitude: z.string().nullable().default(null),
  plot_number: z.string().max(100).default(""),
  acquisition_date: z.string().nullable().default(null),
  acquisition_price: z.string().nullable().default(null),
  current_value: z.string().nullable().default(null),
  total_area_sqft: z.string().nullable().default(null),
  is_active: z.boolean().default(true),
});

export type PropertyFormData = z.infer<typeof propertySchema>;

export const unitSchema = z.object({
  unit_number: z.string().min(1, "Unit number is required").max(50),
  floor: z.number().int().nullable().default(null),
  area_sqft: z.string().min(1, "Area is required"),
  bedrooms: z.number().int().min(0).nullable().default(null),
  bathrooms: z.number().int().min(0).nullable().default(null),
  asking_price: z.string().nullable().default(null),
  status: z.enum(["available", "reserved", "sold", "leased"]).default("available"),
});

export type UnitFormData = z.infer<typeof unitSchema>;

export const valuationSchema = z.object({
  valuation_date: z.string().min(1, "Date is required"),
  value: z.string().min(1, "Value is required"),
  valuation_type: z.enum(["appraisal", "internal", "market", "tax"]).default("internal"),
  appraiser: z.string().default(""),
  notes: z.string().default(""),
});

export type ValuationFormData = z.infer<typeof valuationSchema>;

export const ownershipSchema = z.object({
  legal_owner_name: z.string().min(1, "Owner name is required").max(255),
  ownership_structure: z
    .enum(["individual", "corporate", "trust", "joint_venture"])
    .default("individual"),
  ownership_percentage: z.string().min(1, "Percentage is required"),
  title_deed_number: z.string().min(1, "Title deed number is required").max(100),
  registration_authority: z.string().min(1, "Registration authority is required").max(255),
  date_of_registration: z.string().min(1, "Registration date is required"),
  deed_expiry: z.string().nullable().default(null),
});

export type OwnershipFormData = z.infer<typeof ownershipSchema>;

export const encumbranceSchema = z.object({
  encumbrance_type: z.enum(["mortgage", "lien", "legal_dispute", "court_case", "tax_arrears"]),
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().default(""),
  amount: z.string().nullable().default(null),
  status: z.enum(["active", "resolved", "pending"]).default("active"),
  date_filed: z.string().min(1, "Date filed is required"),
  date_resolved: z.string().nullable().default(null),
  reference_number: z.string().max(100).default(""),
  notes: z.string().default(""),
});

export type EncumbranceFormData = z.infer<typeof encumbranceSchema>;
