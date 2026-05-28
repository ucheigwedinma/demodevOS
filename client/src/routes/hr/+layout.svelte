<script lang="ts">
  import { page } from "$app/stores";

  let { children } = $props();

  type TabGroup = {
    tabs: { href: string; label: string }[];
  };

  const groups: TabGroup[] = [
    {
      tabs: [
        { href: "/hr", label: "Org Chart" },
        { href: "/hr/business-units", label: "Business Units" },
        { href: "/hr/departments", label: "Departments" },
        { href: "/hr/teams", label: "Teams" },
        { href: "/hr/positions", label: "Positions & Roles" },
        { href: "/hr/position-assignments", label: "Position Assignments" },
        { href: "/hr/reporting-lines", label: "Reporting Lines" },
        { href: "/hr/budgeting", label: "Position Budgeting" },
        { href: "/hr/vacancies", label: "Vacancy Tracker" },
      ],
    },
    {
      tabs: [
        { href: "/hr/employees", label: "Employee Profiles" },
        { href: "/hr/employment-history", label: "Employment History" },
        { href: "/hr/contact-info", label: "Contact Information" },
        { href: "/hr/id-documents", label: "Identification Docs" },
        { href: "/hr/emergency-contacts", label: "Emergency Contacts" },
        { href: "/hr/compensation", label: "Compensation Records" },
        { href: "/hr/contracts", label: "Contract Documents" },
        { href: "/hr/attachments", label: "HR Attachments" },
      ],
    },
    {
      tabs: [
        { href: "/hr/requisitions", label: "Job Requisitions" },
        { href: "/hr/job-listings", label: "Job Listings" },
        { href: "/hr/candidates", label: "Candidate Pipeline" },
        { href: "/hr/interviews", label: "Interview Scheduling" },
        { href: "/hr/evaluations", label: "Candidate Evaluation" },
        { href: "/hr/offers", label: "Offer Management" },
        { href: "/hr/hiring-workflow", label: "Hiring Workflow" },
      ],
    },
    {
      tabs: [
        { href: "/hr/onboarding-templates", label: "Onboarding Templates" },
        { href: "/hr/onboarding-tasks", label: "Onboarding Tasks" },
        { href: "/hr/document-collection", label: "Document Collection" },
        { href: "/hr/equipment-allocation", label: "Equipment Allocation" },
        { href: "/hr/orientation-checklists", label: "Orientation Checklists" },
        { href: "/hr/probation-tracking", label: "Probation Tracking" },
      ],
    },
    {
      tabs: [
        { href: "/hr/performance-goals", label: "Performance Goals" },
        { href: "/hr/performance-reviews", label: "Performance Reviews" },
        { href: "/hr/continuous-feedback", label: "Continuous Feedback" },
        { href: "/hr/manager-evaluations", label: "Manager Evaluations" },
        { href: "/hr/peer-reviews", label: "Peer Reviews" },
        { href: "/hr/performance-improvement-plans", label: "Improvement Plans" },
      ],
    },
    {
      tabs: [
        { href: "/hr/skills-matrix", label: "Skills Matrix" },
        { href: "/hr/certifications", label: "Certifications" },
        { href: "/hr/licenses", label: "Professional Licenses" },
        { href: "/hr/competency-assessments", label: "Competency Assessments" },
        { href: "/hr/training-records", label: "Training Records" },
      ],
    },
    {
      tabs: [
        { href: "/hr/training-courses", label: "Training Courses" },
        { href: "/hr/training-plans", label: "Training Plans" },
        { href: "/hr/course-enrollments", label: "Course Enrollment" },
        { href: "/hr/learning-library", label: "Learning Library" },
        { href: "/hr/training-completions", label: "Training Completion" },
        { href: "/hr/certification-expiry-alerts", label: "Expiry Alerts" },
      ],
    },
    {
      tabs: [
        { href: "/hr/attendance-logs", label: "Attendance Logs" },
        { href: "/hr/leave-requests", label: "Leave Requests" },
        { href: "/hr/leave-calendar", label: "Leave Calendar" },
        { href: "/hr/leave-balances", label: "Leave Balances" },
        { href: "/hr/overtime-requests", label: "Overtime Requests" },
        { href: "/hr/remote-work-logs", label: "Remote Work Logs" },
      ],
    },
    {
      tabs: [
        { href: "/hr/promotions", label: "Promotions" },
        { href: "/hr/transfers", label: "Transfers" },
        { href: "/hr/role-changes", label: "Role Changes" },
        { href: "/hr/disciplinary-records", label: "Disciplinary Records" },
        { href: "/hr/exit-management", label: "Exit Management" },
        { href: "/hr/exit-interviews", label: "Exit Interviews" },
      ],
    },
    {
      tabs: [
        { href: "/hr/headcount-analytics", label: "Headcount Analytics" },
        { href: "/hr/turnover-rate", label: "Turnover Rate" },
        { href: "/hr/department-staffing", label: "Department Staffing" },
        { href: "/hr/hiring-funnel", label: "Hiring Funnel Metrics" },
        { href: "/hr/workforce-cost", label: "Workforce Cost" },
        { href: "/hr/diversity-metrics", label: "Diversity Metrics" },
      ],
    },
    {
      tabs: [
        { href: "/hr/hr-policies", label: "HR Policies" },
        { href: "/hr/employee-handbook", label: "Employee Handbook" },
        { href: "/hr/compliance-documents", label: "Compliance Documents" },
        { href: "/hr/policy-acknowledgements", label: "Policy Acknowledgements" },
        { href: "/hr/document-templates", label: "Document Templates" },
      ],
    },
  ];

  let activeGroup = $derived(
    groups.find((g) => g.tabs.some((t) => $page.url.pathname === t.href)) ?? null
  );
</script>

{#if activeGroup}
  <div class="border-b border-neutral-200 -mt-2 mb-6">
    <nav class="flex gap-0.5 -mb-px overflow-x-auto scrollbar-none" aria-label="HR tabs">
      {#each activeGroup.tabs as tab}
        <a
          href={tab.href}
          class="shrink-0 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                 {$page.url.pathname === tab.href
                   ? 'border-neutral-900 text-neutral-900'
                   : 'border-transparent text-neutral-400 hover:text-neutral-600 hover:border-neutral-300'}"
        >
          {tab.label}
        </a>
      {/each}
    </nav>
  </div>
{/if}

{@render children()}

<style>
  .scrollbar-none {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .scrollbar-none::-webkit-scrollbar {
    display: none;
  }
</style>
