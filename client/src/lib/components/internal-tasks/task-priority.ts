/**
 * Static Tailwind class maps for the 4 priority values.
 *
 * Per docs/workspace-internal-tasks-ui-spec.md §3:
 *   - Only "urgent" gets a color accent (rose).
 *   - low + medium are HIDDEN in list rows (showInRow=false). Reduces noise
 *     on the ~70% of tasks that don't deserve visual competition.
 *   - All four show in the detail view + form.
 */

import type { InternalTaskPriority } from "$lib/types";

export interface PriorityTreatment {
  chip: string;
  text: string;
  border: string;
  iconPath: string | null;
  showInRow: boolean;
  labelKey: string;
}

export const PRIORITY_TREATMENT: Record<InternalTaskPriority, PriorityTreatment> = {
  low: {
    chip: "bg-white",
    text: "text-neutral-500",
    border: "border-neutral-200",
    // down-arrow
    iconPath: "M12 4.5v15M4.5 12l7.5 7.5L19.5 12",
    showInRow: false,
    labelKey: "workspace.internal_tasks.priority.low",
  },
  medium: {
    chip: "bg-white",
    text: "text-neutral-600",
    border: "border-neutral-200",
    iconPath: null,
    showInRow: false,
    labelKey: "workspace.internal_tasks.priority.medium",
  },
  high: {
    chip: "bg-white",
    text: "text-neutral-700",
    border: "border-neutral-300",
    // up-arrow
    iconPath: "M12 19.5v-15M4.5 12l7.5-7.5L19.5 12",
    showInRow: true,
    labelKey: "workspace.internal_tasks.priority.high",
  },
  urgent: {
    chip: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    // fire (heroicons-outline)
    iconPath:
      "M15.362 5.214A8.252 8.252 0 0 1 12 21 8.25 8.25 0 0 1 6.038 7.047 8.287 8.287 0 0 0 9 9.601a8.983 8.983 0 0 1 3.361-6.867 8.21 8.21 0 0 0 3 2.48Z",
    showInRow: true,
    labelKey: "workspace.internal_tasks.priority.urgent",
  },
};

export const PRIORITY_ORDER: InternalTaskPriority[] = [
  "urgent",
  "high",
  "medium",
  "low",
];
