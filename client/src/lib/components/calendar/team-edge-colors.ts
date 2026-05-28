/**
 * Static left-edge color classes for team-scoped events.
 *
 * Per docs/workspace-calendar-ui-spec.md §2.1: events with `team_id` set
 * get a 4px left-edge strip in the team's color. Reuses the 10-token
 * palette from the Teams UI spec (`workspace-teams-ui-spec.md` §1.6).
 *
 * Static lookup — Tailwind 4 scanner requires literal class names.
 */

export type TeamColor =
  | "rose"
  | "orange"
  | "amber"
  | "lime"
  | "emerald"
  | "teal"
  | "sky"
  | "indigo"
  | "violet"
  | "fuchsia";

export const TEAM_EDGE_CLASS: Record<TeamColor, string> = {
  rose: "border-l-rose-500",
  orange: "border-l-orange-500",
  amber: "border-l-amber-500",
  lime: "border-l-lime-600",
  emerald: "border-l-emerald-500",
  teal: "border-l-teal-500",
  sky: "border-l-sky-500",
  indigo: "border-l-indigo-500",
  violet: "border-l-violet-500",
  fuchsia: "border-l-fuchsia-500",
};

export function resolveTeamEdge(color: string | null | undefined): string {
  if (!color) return "border-l-transparent";
  return TEAM_EDGE_CLASS[color as TeamColor] ?? "border-l-neutral-300";
}
