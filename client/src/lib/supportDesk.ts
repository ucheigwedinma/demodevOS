export type SupportDeskPageKey =
  | "overview"
  | "tickets"
  | "requests"
  | "knowledge-base"
  | "sla-escalations"
  | "communication"
  | "automation"
  | "reports"
  | "configuration";

export type SupportDeskNavItem = {
  href: string;
  label: string;
  exact?: boolean;
};

export type SupportDeskPageConfig = {
  key: SupportDeskPageKey;
  title: string;
  description: string;
  focusAreas: string[];
  operatingControls: string[];
  implementationNote: string;
};

export const supportDeskNavItems: SupportDeskNavItem[] = [
  { href: "/support-desk", label: "Overview", exact: true },
  { href: "/support-desk/tickets", label: "Tickets" },
  { href: "/support-desk/requests", label: "Requests" },
  { href: "/support-desk/knowledge-base", label: "Knowledge Base" },
  { href: "/support-desk/sla-escalations", label: "SLA & Escalations" },
  { href: "/support-desk/communication", label: "Communication" },
  { href: "/support-desk/automation", label: "Automation" },
  { href: "/support-desk/reports", label: "Reports" },
  { href: "/support-desk/configuration", label: "Configuration" },
];

export const supportDeskPages: Record<SupportDeskPageKey, SupportDeskPageConfig> = {
  overview: {
    key: "overview",
    title: "Support Desk Overview",
    description: "Run ticket intake, request fulfilment, service commitments, and support governance from one operational workspace.",
    focusAreas: [
      "Centralize incidents, service requests, and support queues.",
      "Track ownership, priority, and escalation state across every case.",
      "Keep audit-ready support history for workflow and governance reviews.",
    ],
    operatingControls: [
      "Queue definitions by business unit or service line.",
      "Priority and severity rules for operational triage.",
      "Response and resolution commitments mapped to SLA targets.",
    ],
    implementationNote: "Use this module as the internal service operations surface for governance-driven support work.",
  },
  tickets: {
    key: "tickets",
    title: "Tickets",
    description: "Manage incidents from intake to closure with assignment, severity, status, and service clock visibility.",
    focusAreas: [
      "Incident logging with ownership and due dates.",
      "Priority-based triage and queue balancing.",
      "Resolution tracking with full audit history.",
    ],
    operatingControls: [
      "Agent assignment rules.",
      "Ticket status lifecycle.",
      "Response and breach monitoring.",
    ],
    implementationNote: "This page is ready for queue tables, ticket filters, and SLA-aware ticket detail views.",
  },
  requests: {
    key: "requests",
    title: "Requests",
    description: "Handle standardized service requests that may require fulfilment steps, approvals, or cross-team routing.",
    focusAreas: [
      "Service catalogue intake for repeatable requests.",
      "Approval-aware request fulfilment workflows.",
      "Clear handoff tracking between requester and fulfiller.",
    ],
    operatingControls: [
      "Request forms and required fields.",
      "Fulfilment steps per request type.",
      "Approval routing before completion.",
    ],
    implementationNote: "Use this surface for non-incident work such as access requests, document requests, or service fulfilment.",
  },
  "knowledge-base": {
    key: "knowledge-base",
    title: "Knowledge Base",
    description: "Publish governed support content so teams can resolve issues consistently and reduce repeat tickets.",
    focusAreas: [
      "Article ownership and review cadence.",
      "Searchable troubleshooting and policy content.",
      "Version control for support guidance.",
    ],
    operatingControls: [
      "Article lifecycle status.",
      "Approvals before publishing.",
      "Visibility and access rules.",
    ],
    implementationNote: "This area is suited for article libraries, review workflows, and controlled publication states.",
  },
  "sla-escalations": {
    key: "sla-escalations",
    title: "SLA & Escalations",
    description: "Monitor service performance, enforce breach rules, and route high-risk cases through escalation paths.",
    focusAreas: [
      "Response and resolution targets by ticket class.",
      "Escalation ladders for overdue or critical work.",
      "Breach visibility for operational governance.",
    ],
    operatingControls: [
      "SLA policy definitions.",
      "Escalation tiers and thresholds.",
      "Timer and breach notifications.",
    ],
    implementationNote: "This page is the control surface for policy-backed service assurance and escalation management.",
  },
  communication: {
    key: "communication",
    title: "Communication",
    description: "Coordinate customer and internal updates across tickets, requests, and escalated service events.",
    focusAreas: [
      "Conversation timelines per support record.",
      "Channel-specific communication templates.",
      "Internal notes separated from customer-facing updates.",
    ],
    operatingControls: [
      "Email and in-app message templates.",
      "Communication ownership and approvals.",
      "Audit history for outbound updates.",
    ],
    implementationNote: "Use this section for support messaging workflows and communication governance.",
  },
  automation: {
    key: "automation",
    title: "Automation",
    description: "Reduce manual support work through routing logic, event-driven actions, macros, and policy-based triggers.",
    focusAreas: [
      "Automatic queue routing for new records.",
      "Policy triggers for reminders and escalations.",
      "Reusable actions for repetitive support work.",
    ],
    operatingControls: [
      "Rule conditions and execution order.",
      "Macro libraries for common tasks.",
      "Triggered notifications and follow-up actions.",
    ],
    implementationNote: "This page is ready for automation rules, macro builders, and workflow trigger management.",
  },
  reports: {
    key: "reports",
    title: "Reports",
    description: "Measure support performance across volume, response times, breach trends, throughput, and service quality.",
    focusAreas: [
      "Queue-level workload and ageing metrics.",
      "SLA attainment and breach trends.",
      "Resolution throughput and backlog health.",
    ],
    operatingControls: [
      "Default filters and saved views.",
      "Export and scheduled report settings.",
      "Operational and executive report packs.",
    ],
    implementationNote: "Use this section for dashboards, scheduled reports, and governance-facing service summaries.",
  },
  configuration: {
    key: "configuration",
    title: "Configuration",
    description: "Define the core structure of the support desk, including queues, categories, intake forms, and policy defaults.",
    focusAreas: [
      "Queue and category structure.",
      "Request types and form templates.",
      "Default assignment and policy settings.",
    ],
    operatingControls: [
      "Service taxonomy and ownership.",
      "Form field configuration.",
      "Default automation and SLA linkage.",
    ],
    implementationNote: "This area should hold the foundational setup that all Support Desk workflows depend on.",
  },
};

export function getSupportDeskPageConfig(section: string): SupportDeskPageConfig | null {
  return supportDeskPages[section as SupportDeskPageKey] ?? null;
}
