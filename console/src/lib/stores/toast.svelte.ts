export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: number;
  title: string;
  description?: string;
  type: ToastType;
}

let nextId = 0;
let toasts = $state<Toast[]>([]);

function inferToastDescription(type: ToastType, title: string): string {
  const normalized = title.toLowerCase();

  if (type === "success") {
    if (normalized.includes("created")) return "The new record has been created successfully.";
    if (normalized.includes("updated")) return "Your changes were saved successfully.";
    if (normalized.includes("deleted") || normalized.includes("removed")) return "The record has been removed successfully.";
    if (normalized.includes("submitted")) return "The request was submitted successfully.";
    if (normalized.includes("approved")) return "The record was approved successfully.";
    if (normalized.includes("rejected")) return "The record was rejected successfully.";
    if (normalized.includes("accepted")) return "The record was accepted successfully.";
    if (normalized.includes("completed")) return "The action was completed successfully.";
    if (normalized.includes("queued")) return "The action has been queued and will continue in the background.";
    return "The action completed successfully.";
  }

  if (type === "error") {
    if (normalized.includes("validation")) return "Please review the highlighted fields and try again.";
    if (normalized.includes("load failed")) return "Data could not be loaded. Refresh or try again shortly.";
    if (normalized.includes("save") || normalized.includes("create") || normalized.includes("update")) {
      return "The record could not be saved. Check required fields and try again.";
    }
    if (normalized.includes("delete")) return "The record could not be deleted. Please try again.";
    if (normalized.includes("submit")) return "The request could not be submitted. Please try again.";
    if (normalized.includes("extend")) return "The action could not be completed at this time.";
    if (normalized.includes("accept") || normalized.includes("reject") || normalized.includes("withdraw")) {
      return "The action could not be completed. Please retry.";
    }
    return "An unexpected error occurred. Please try again.";
  }

  if (type === "warning") {
    return "Please review this warning before continuing.";
  }

  return "Here is an update on your request.";
}

export function getToasts(): Toast[] {
  return toasts;
}

export function addToast(title: string, type: ToastType = "info", description?: string, duration = 4000) {
  const id = nextId++;
  const desc = typeof description === "string" ? description : Array.isArray(description) ? description[0] : description ? String(description) : "";
  const message = desc && desc.trim().length > 0 ? desc : inferToastDescription(type, title);
  toasts = [...toasts, { id, title, description: message, type }];

  if (duration > 0) {
    setTimeout(() => dismissToast(id), duration);
  }
}

export function dismissToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
}

export const toast = {
  success: (title: string, description?: string) => addToast(title, "success", description),
  error: (title: string, description?: string) => addToast(title, "error", description, 6000),
  warning: (title: string, description?: string) => addToast(title, "warning", description, 5000),
  info: (title: string, description?: string) => addToast(title, "info", description),
};
