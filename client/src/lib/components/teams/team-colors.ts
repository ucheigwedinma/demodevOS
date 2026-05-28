/**
 * Static palette token → Tailwind classes for Workspace Teams.
 *
 * Why a static map: Tailwind 4's class scanner is purely static — it scans
 * source files for fully-formed class names, so `bg-${color}-500` would be
 * purged out of the build. Every class name we want must appear *literally*
 * in source. This map is the literal lookup; consumers index into it.
 *
 * See docs/workspace-teams-ui-spec.md §1.6.
 */

import type { WorkspaceTeamColor } from "$lib/types";

export interface TeamColorClasses {
  /** Avatar disc background — saturated. */
  disc: string;
  /** Chip background — soft. */
  chipBg: string;
  /** Chip text — strong, WCAG AA on chipBg. */
  chipText: string;
  /** Chip border — slightly darker than chipBg. */
  chipBorder: string;
  /** Color swatch dot used in pickers. Same as disc. */
  swatch: string;
}

export const TEAM_COLOR_TOKENS: WorkspaceTeamColor[] = [
  "rose",
  "orange",
  "amber",
  "lime",
  "emerald",
  "teal",
  "sky",
  "indigo",
  "violet",
  "fuchsia",
];

export const TEAM_COLORS: Record<WorkspaceTeamColor, TeamColorClasses> = {
  rose: {
    disc: "bg-rose-500",
    chipBg: "bg-rose-100",
    chipText: "text-rose-700",
    chipBorder: "border-rose-200",
    swatch: "bg-rose-500",
  },
  orange: {
    disc: "bg-orange-500",
    chipBg: "bg-orange-100",
    chipText: "text-orange-700",
    chipBorder: "border-orange-200",
    swatch: "bg-orange-500",
  },
  amber: {
    disc: "bg-amber-500",
    chipBg: "bg-amber-100",
    chipText: "text-amber-700",
    chipBorder: "border-amber-200",
    swatch: "bg-amber-500",
  },
  lime: {
    disc: "bg-lime-600",
    chipBg: "bg-lime-100",
    chipText: "text-lime-700",
    chipBorder: "border-lime-200",
    swatch: "bg-lime-600",
  },
  emerald: {
    disc: "bg-emerald-500",
    chipBg: "bg-emerald-100",
    chipText: "text-emerald-700",
    chipBorder: "border-emerald-200",
    swatch: "bg-emerald-500",
  },
  teal: {
    disc: "bg-teal-500",
    chipBg: "bg-teal-100",
    chipText: "text-teal-700",
    chipBorder: "border-teal-200",
    swatch: "bg-teal-500",
  },
  sky: {
    disc: "bg-sky-500",
    chipBg: "bg-sky-100",
    chipText: "text-sky-700",
    chipBorder: "border-sky-200",
    swatch: "bg-sky-500",
  },
  indigo: {
    disc: "bg-indigo-500",
    chipBg: "bg-indigo-100",
    chipText: "text-indigo-700",
    chipBorder: "border-indigo-200",
    swatch: "bg-indigo-500",
  },
  violet: {
    disc: "bg-violet-500",
    chipBg: "bg-violet-100",
    chipText: "text-violet-700",
    chipBorder: "border-violet-200",
    swatch: "bg-violet-500",
  },
  fuchsia: {
    disc: "bg-fuchsia-500",
    chipBg: "bg-fuchsia-100",
    chipText: "text-fuchsia-700",
    chipBorder: "border-fuchsia-200",
    swatch: "bg-fuchsia-500",
  },
};

/** Coerce an arbitrary string into a known token, falling back to sky. */
export function resolveColor(value: string | null | undefined): WorkspaceTeamColor {
  if (value && (TEAM_COLOR_TOKENS as string[]).includes(value)) {
    return value as WorkspaceTeamColor;
  }
  return "sky";
}

/** Curated emoji set for the team-create picker — 32 friendly options. */
export const TEAM_EMOJI_PICKS: string[] = [
  "👥", "🚀", "⚡️", "🎯", "🛠️", "🌱", "📐", "💡",
  "🔥", "🌊", "🏔️", "⛰️", "🎨", "🧪", "🔍", "📊",
  "📈", "🌟", "✨", "🌀", "🦊", "🐢", "🐝", "🦉",
  "🌻", "🌸", "🌳", "🪴", "☕️", "🥁", "🎻", "🛰️",
];
