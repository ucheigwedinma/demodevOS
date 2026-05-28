/**
 * Static Tailwind class maps for the 4 task status values.
 *
 * Per docs/workspace-internal-tasks-ui-spec.md §2:
 *   todo        → neutral hollow (the starting line)
 *   in_progress → solid neutral-900 (the loudest state)
 *   blocked     → amber accent (the only attention-grabber besides urgent)
 *   done        → muted neutral-100 (falls back; filtered out by default)
 *
 * Tailwind 4's static class scanner requires every utility class to appear
 * verbatim here. Never interpolate classnames.
 */

import type { InternalTaskStatus } from "$lib/types";

export interface StatusTreatment {
  chip: string;
  text: string;
  border: string;
  iconPath: string;
  labelKey: string;
}

export const STATUS_TREATMENT: Record<InternalTaskStatus, StatusTreatment> = {
  todo: {
    chip: "bg-white",
    text: "text-neutral-600",
    border: "border-neutral-300",
    // hollow circle (heroicons-outline)
    iconPath:
      "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z",
    labelKey: "workspace.internal_tasks.status.todo",
  },
  in_progress: {
    chip: "bg-neutral-900",
    text: "text-white",
    border: "border-neutral-900",
    // half-filled clock-like circle
    iconPath:
      "M12 6v6l4 2m4-2a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
    labelKey: "workspace.internal_tasks.status.in_progress",
  },
  blocked: {
    chip: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    // exclamation triangle
    iconPath:
      "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.732 0 2.814-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
    labelKey: "workspace.internal_tasks.status.blocked",
  },
  done: {
    chip: "bg-neutral-100",
    text: "text-neutral-500",
    border: "border-neutral-200",
    // check inside circle
    iconPath:
      "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    labelKey: "workspace.internal_tasks.status.done",
  },
};

export const STATUS_ORDER: InternalTaskStatus[] = [
  "todo",
  "in_progress",
  "blocked",
  "done",
];
