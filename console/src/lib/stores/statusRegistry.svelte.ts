import { api } from "$lib/api";

export type BadgeVariant =
  | "neutral"
  | "muted"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "orange"
  | "violet"
  | "rose";

export interface StatusBadgeDef {
  label: string;
  variant: BadgeVariant;
  classes: string;
}

export const VARIANT_PALETTE: Record<BadgeVariant, string> = {
  neutral: "bg-neutral-100 text-neutral-600 border-neutral-200",
  muted: "bg-neutral-100 text-neutral-400 border-neutral-200",
  info: "bg-blue-50 text-blue-700 border-blue-100",
  success: "bg-emerald-50 text-emerald-700 border-emerald-100",
  warning: "bg-amber-50 text-amber-700 border-amber-100",
  danger: "bg-red-50 text-red-700 border-red-100",
  orange: "bg-orange-50 text-orange-700 border-orange-100",
  violet: "bg-violet-50 text-violet-700 border-violet-100",
  rose: "bg-rose-50 text-rose-700 border-rose-100",
};

const BUILT_IN_DEFAULTS: Record<string, { label: string; variant: BadgeVariant }> = {
  draft: { label: "Draft", variant: "neutral" },
  new: { label: "New", variant: "neutral" },
  not_started: { label: "Not Started", variant: "neutral" },
  submitted: { label: "Submitted", variant: "info" },
  under_review: { label: "Under Review", variant: "violet" },
  approved: { label: "Approved", variant: "success" },
  rejected: { label: "Rejected", variant: "danger" },
  cancelled: { label: "Cancelled", variant: "muted" },
  archived: { label: "Archived", variant: "muted" },
  pending: { label: "Pending", variant: "warning" },
  in_progress: { label: "In Progress", variant: "info" },
  completed: { label: "Completed", variant: "success" },
  on_hold: { label: "On Hold", variant: "warning" },
  paused: { label: "Paused", variant: "warning" },
  scheduled: { label: "Scheduled", variant: "info" },
  running: { label: "Running", variant: "info" },
  active: { label: "Active", variant: "success" },
  inactive: { label: "Inactive", variant: "muted" },
  suspended: { label: "Suspended", variant: "danger" },
  dormant: { label: "Dormant", variant: "muted" },
  dissolved: { label: "Dissolved", variant: "muted" },
  under_formation: { label: "Under Formation", variant: "info" },
  frozen: { label: "Frozen", variant: "warning" },
  abolished: { label: "Abolished", variant: "muted" },
  paid: { label: "Paid", variant: "success" },
  partially_paid: { label: "Partially Paid", variant: "warning" },
  overdue: { label: "Overdue", variant: "warning" },
  due: { label: "Due", variant: "warning" },
  past_due: { label: "Past Due", variant: "warning" },
  waived: { label: "Waived", variant: "muted" },
  posted: { label: "Posted", variant: "success" },
  reversed: { label: "Reversed", variant: "muted" },
  calculated: { label: "Calculated", variant: "info" },
  distributed: { label: "Distributed", variant: "success" },
  ordered: { label: "Ordered", variant: "info" },
  issued: { label: "Issued", variant: "info" },
  partially_received: { label: "Partially Received", variant: "warning" },
  received: { label: "Received", variant: "success" },
  inspected: { label: "Inspected", variant: "info" },
  accepted: { label: "Accepted", variant: "success" },
  partially_accepted: { label: "Partially Accepted", variant: "warning" },
  evaluation: { label: "Evaluation", variant: "info" },
  shortlisted: { label: "Shortlisted", variant: "info" },
  winner: { label: "Winner", variant: "success" },
  superseded: { label: "Superseded", variant: "violet" },
  declined: { label: "Declined", variant: "danger" },
  sent: { label: "Sent", variant: "info" },
  delivered: { label: "Delivered", variant: "success" },
  read: { label: "Read", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
  bounced: { label: "Bounced", variant: "danger" },
  opened: { label: "Opened", variant: "info" },
  clicked: { label: "Clicked", variant: "success" },
  unsubscribed: { label: "Unsubscribed", variant: "muted" },
  open: { label: "Open", variant: "info" },
  pending_requester: { label: "Pending Requester", variant: "warning" },
  escalated: { label: "Escalated", variant: "orange" },
  resolved: { label: "Resolved", variant: "success" },
  closed: { label: "Closed", variant: "muted" },
  acknowledged: { label: "Acknowledged", variant: "info" },
  matched: { label: "Matched", variant: "success" },
  available: { label: "Available", variant: "success" },
  held: { label: "Held", variant: "warning" },
  sold: { label: "Sold", variant: "info" },
  leased: { label: "Leased", variant: "violet" },
  unavailable: { label: "Unavailable", variant: "muted" },
  won: { label: "Won", variant: "success" },
  lost: { label: "Lost", variant: "muted" },
  disqualified: { label: "Disqualified", variant: "muted" },
  expired: { label: "Expired", variant: "muted" },
  hold: { label: "Hold", variant: "warning" },
  reserved: { label: "Reserved", variant: "info" },
  payment_pending: { label: "Payment Pending", variant: "warning" },
  converting: { label: "Converting", variant: "info" },
  converted: { label: "Converted", variant: "success" },
  planning: { label: "Planning", variant: "info" },
  mitigated: { label: "Mitigated", variant: "success" },
  skipped: { label: "Skipped", variant: "muted" },
  planned: { label: "Planned", variant: "info" },
  passed: { label: "Passed", variant: "success" },
  blocked: { label: "Blocked", variant: "danger" },
  reviewed: { label: "Reviewed", variant: "info" },
  critical: { label: "Critical", variant: "rose" },
  breached: { label: "Breached", variant: "rose" },
  urgent: { label: "Urgent", variant: "orange" },
  compliant: { label: "Compliant", variant: "success" },
  non_compliant: { label: "Non-Compliant", variant: "danger" },
  partially_compliant: { label: "Partially Compliant", variant: "warning" },
  pending_review: { label: "Pending Review", variant: "warning" },
  remediation: { label: "Remediation", variant: "warning" },
  appealed: { label: "Appealed", variant: "violet" },
  probation: { label: "Probation", variant: "warning" },
  notice_period: { label: "Notice Period", variant: "warning" },
  resigned: { label: "Resigned", variant: "muted" },
  terminated: { label: "Terminated", variant: "danger" },
  withdrawn: { label: "Withdrawn", variant: "muted" },
  no_show: { label: "No Show", variant: "danger" },
  filled: { label: "Filled", variant: "success" },
  extended: { label: "Extended", variant: "warning" },
  effective: { label: "Effective", variant: "success" },
  enrolled: { label: "Enrolled", variant: "info" },
  waitlisted: { label: "Waitlisted", variant: "warning" },
  current: { label: "Current", variant: "success" },
  published: { label: "Published", variant: "success" },
  revoked: { label: "Revoked", variant: "muted" },
  assessed: { label: "Assessed", variant: "info" },
  filed: { label: "Filed", variant: "info" },
  generated: { label: "Generated", variant: "info" },
  processing: { label: "Processing", variant: "info" },
  trialing: { label: "Trialing", variant: "info" },
  deprecated: { label: "Deprecated", variant: "muted" },
};

function humanize(code: string): string {
  return code
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

let registry = $state<Map<string, StatusBadgeDef>>(new Map());
let loaded = $state(false);

export const statusRegistry = {
  get loaded() {
    return loaded;
  },

  async load() {
    try {
      const data = await api.get<
        Array<{
          code: string;
          label: string;
          metadata: { variant?: string };
        }>
      >("/settings/status-badges/");

      const map = new Map<string, StatusBadgeDef>();
      for (const entry of data) {
        const variant = (entry.metadata?.variant as BadgeVariant) ?? "neutral";
        map.set(entry.code, {
          label: entry.label,
          variant,
          classes: VARIANT_PALETTE[variant] ?? VARIANT_PALETTE.neutral,
        });
      }
      registry = map;
    } catch {
      // Fall back to built-in defaults
    } finally {
      loaded = true;
    }
  },

  get(code: string): StatusBadgeDef {
    const fromApi = registry.get(code);
    if (fromApi) return fromApi;

    const builtin = BUILT_IN_DEFAULTS[code];
    if (builtin) {
      return {
        ...builtin,
        classes: VARIANT_PALETTE[builtin.variant],
      };
    }

    return {
      label: humanize(code),
      variant: "neutral",
      classes: VARIANT_PALETTE.neutral,
    };
  },

  classes(code: string): string {
    return this.get(code).classes;
  },

  variant(code: string): BadgeVariant {
    return this.get(code).variant;
  },

  reset() {
    registry = new Map();
    loaded = false;
  },
};
