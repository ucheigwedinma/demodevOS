/**
 * Static Tailwind class maps for the four event kinds.
 *
 * Per docs/workspace-calendar-ui-spec.md §2:
 *   meeting       → solid neutral fill
 *   focus         → muted with subtle dotted pattern
 *   out_of_office → diagonal stripes
 *   reminder      → dot/marker (not a block)
 *
 * Tailwind 4's static class scanner requires that every utility class appears
 * verbatim in source — these maps preserve that. Never compose class names by
 * string interpolation; always look up via the map.
 */

import type { CalendarEventKind } from "$lib/types";

export type KindTreatment = {
  block: string;
  chip: string;
  chipText: string;
  chipBorder: string;
  iconColor: string;
  label: string;
};

/**
 * Block treatments. `block` is applied to a full event block in MonthView
 * pills / WeekView blocks. `chip` + text + border are for KindChip in forms.
 *
 * Patterns (focus + out_of_office) are CSS-in-class using inline-style
 * `background-image` overlays — Tailwind has no dotted/striped utility, so
 * we keep these as small repeating-linear-gradient declarations in the
 * EventCell component itself, gated on kind.
 */
export const KIND_TREATMENT: Record<CalendarEventKind, KindTreatment> = {
  meeting: {
    block: "bg-neutral-900 text-white border-neutral-900",
    chip: "bg-neutral-900",
    chipText: "text-white",
    chipBorder: "border-neutral-900",
    iconColor: "text-white",
    label: "Meeting",
  },
  focus: {
    block: "bg-neutral-100 text-neutral-700 border-neutral-200",
    chip: "bg-neutral-100",
    chipText: "text-neutral-700",
    chipBorder: "border-neutral-200",
    iconColor: "text-neutral-500",
    label: "Focus block",
  },
  out_of_office: {
    block: "bg-white text-neutral-700 border-neutral-300",
    chip: "bg-white",
    chipText: "text-neutral-700",
    chipBorder: "border-neutral-300",
    iconColor: "text-neutral-500",
    label: "Out of office",
  },
  reminder: {
    block: "bg-white text-neutral-700 border-neutral-200",
    chip: "bg-white",
    chipText: "text-neutral-600",
    chipBorder: "border-neutral-200",
    iconColor: "text-neutral-500",
    label: "Reminder",
  },
};

/**
 * CSS background-image patterns for kinds that need them. Applied inline
 * via style attribute (necessary because Tailwind has no pattern utility,
 * and we want the scanner to remain static).
 */
export const KIND_PATTERN: Record<CalendarEventKind, string | null> = {
  meeting: null,
  focus: "radial-gradient(rgba(115,115,115,0.18) 1px, transparent 1px)",
  out_of_office:
    "repeating-linear-gradient(135deg, rgba(115,115,115,0.10) 0 6px, transparent 6px 12px)",
  reminder: null,
};

export const KIND_PATTERN_SIZE: Record<CalendarEventKind, string | null> = {
  meeting: null,
  focus: "6px 6px",
  out_of_office: "auto",
  reminder: null,
};

export const KIND_ORDER: CalendarEventKind[] = [
  "meeting",
  "focus",
  "out_of_office",
  "reminder",
];

/**
 * SVG path strings (heroicons outline, stroke-width=1.5) for each kind.
 * Inline-rendered by KindChip and EventCell.
 */
export const KIND_ICON_PATH: Record<CalendarEventKind, string> = {
  // calendar
  meeting:
    "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0V11.25h18v7.5",
  // bolt (focus)
  focus:
    "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
  // paper-airplane (OOO)
  out_of_office:
    "M6 12L3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12zm0 0h7.5",
  // bell (reminder)
  reminder:
    "M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0",
};
