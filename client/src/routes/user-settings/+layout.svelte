<script lang="ts">
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import type {
    UserAccountSecurity,
    UserNotificationPreferences,
    UserSettingsProfile,
    UserTaskWorkflowPreferences,
  } from "$lib/types";

  let { children } = $props();

  type RightPanelAction = {
    label: string;
    href: string;
  };

  type RightPanelActivity = {
    date: string;
    event: string;
  };

  type RightPanelScoreRow = {
    label: string;
    value: string;
    isPositive: boolean;
  };

  type RightPanelSpotlight = {
    title: string;
    paragraphs: string[];
    listTitle?: string;
    list?: string[];
    scoreRows?: RightPanelScoreRow[];
    rating?: string;
    recommendation?: string;
  };

  type RightPanelContent = {
    spotlight?: RightPanelSpotlight;
    helpTitle: string;
    helpBody: string[];
    recommendationsTitle: string;
    recommendations: string[];
    quickActions: RightPanelAction[];
    activityTitle: string;
    activity: RightPanelActivity[];
  };

  type SmartRecommendation = {
    title: string;
    lines: string[];
    actionLabel?: string;
    actionHref?: string;
  };

  type ConfigurationHealthItem = {
    label: string;
    ok: boolean;
    detail: string;
  };

  type ConfigurationHealth = {
    items: ConfigurationHealthItem[];
    score: number;
  };

  const menuSections = [
    {
      title: "Account",
      items: [
        { href: "/user-settings", label: "Profile", exact: true },
        { href: "/user-settings/account-login", label: "Account & Login" },
        { href: "/user-settings/notifications-alerts", label: "Notifications & Alerts" },
        { href: "/user-settings/privacy-visibility", label: "Privacy & Visibility" },
        { href: "/user-settings/workspace-preferences", label: "Workspace Preferences" },
        { href: "/user-settings/task-workflow-preferences", label: "Task & Workflow Preferences" },
        { href: "/user-settings/calendar-scheduling", label: "Calendar & Scheduling" },
        { href: "/user-settings/data-export-preferences", label: "Data & Export Preferences" },
        { href: "/user-settings/integrations", label: "Integrations" },
        { href: "/user-settings/accessibility", label: "Accessibility" },
      ],
    },
  ];

  const rightPanelByPath: Record<string, RightPanelContent> = {
    "/user-settings": {
      spotlight: {
        title: "Profile Visibility",
        paragraphs: [
          "Your profile information is visible to members of your organization.",
        ],
        listTitle: "Fields visible to others",
        list: ["Name", "Job title", "Department"],
      },
      helpTitle: "Profile Settings",
      helpBody: [
        "Manage personal identity and contact information shown across the platform.",
        "Profile details influence approvals, comments, and assignment displays.",
      ],
      recommendationsTitle: "Recommended Setup",
      recommendations: [
        "Keep job title and department current for accurate routing.",
        "Set preferred display name to match how colleagues address you.",
        "Use a clear profile photo for faster identity verification.",
      ],
      quickActions: [
        { label: "Open Account & Login", href: "/user-settings/account-login" },
        { label: "Review Privacy Settings", href: "/user-settings/privacy-visibility" },
        { label: "Open Audit Center", href: "/settings/audit" },
      ],
      activityTitle: "Recent Profile Activity",
      activity: [
        { date: "Mar 7", event: "Display name updated" },
        { date: "Mar 5", event: "Profile photo changed" },
        { date: "Mar 3", event: "Contact number updated" },
      ],
    },
    "/user-settings/account-login": {
      spotlight: {
        title: "Security Score",
        paragraphs: [],
        scoreRows: [
          { label: "Password Strength", value: "Strong", isPositive: true },
          { label: "Two-Factor Auth", value: "Disabled", isPositive: false },
          { label: "Login Alerts", value: "Enabled", isPositive: true },
        ],
        rating: "Medium",
        recommendation: "Enable 2FA to increase your security level.",
      },
      helpTitle: "Two-Factor Authentication",
      helpBody: [
        "Two-factor authentication adds an extra layer of security to your account.",
        "When enabled, verification codes are required during login.",
        "Recommended apps: Google Authenticator, Microsoft Authenticator, 1Password.",
      ],
      recommendationsTitle: "Recommended Security Setup",
      recommendations: [
        "Enable MFA for privileged or approval-heavy accounts.",
        "Rotate passwords after suspected device compromise.",
        "Revoke old sessions after role or device changes.",
      ],
      quickActions: [
        { label: "Review Login Activity", href: "/user-settings/account-login" },
        { label: "Open Security Audit", href: "/settings/audit" },
        { label: "Update Privacy Controls", href: "/user-settings/privacy-visibility" },
      ],
      activityTitle: "Recent Security Activity",
      activity: [
        { date: "Mar 7", event: "Password changed" },
        { date: "Mar 6", event: "Login from new device" },
        { date: "Mar 4", event: "MFA preference updated" },
      ],
    },
    "/user-settings/notifications-alerts": {
      spotlight: {
        title: "Notification Tips",
        paragraphs: [
          "Too many alerts can cause notification fatigue.",
        ],
        listTitle: "Recommended setup",
        list: [
          "Instant alerts for approvals",
          "Daily digest for updates",
          "Weekly summary for reports",
        ],
      },
      helpTitle: "Notification Preferences",
      helpBody: [
        "Choose which events trigger alerts and which channels receive them.",
        "Category-level controls let you tune delivery to role responsibilities.",
      ],
      recommendationsTitle: "Recommended Notification Setup",
      recommendations: [
        "Executives: enable SLA warnings and escalations.",
        "Managers: enable task assignments and approvals.",
        "Team members: enable mentions and workflow updates.",
      ],
      quickActions: [
        { label: "Open SLA Notifications", href: "/settings/notifications" },
        { label: "Review Escalation Matrix", href: "/settings/escalation-matrix" },
        { label: "Open Audit Logs", href: "/settings/audit" },
      ],
      activityTitle: "Recent Notification Activity",
      activity: [
        { date: "Mar 7", event: "Category channels updated" },
        { date: "Mar 6", event: "Digest frequency changed" },
        { date: "Mar 2", event: "Push alerts enabled" },
      ],
    },
    "/user-settings/privacy-visibility": {
      helpTitle: "Privacy and Visibility",
      helpBody: [
        "Control who can see profile details, activity presence, and discoverability.",
        "These settings affect visibility inside collaboration and workflow modules.",
      ],
      recommendationsTitle: "Recommended Privacy Setup",
      recommendations: [
        "Keep email visibility at team or organization for collaboration.",
        "Restrict phone visibility unless direct contact is required.",
        "Keep activity visibility aligned with leadership expectations.",
      ],
      quickActions: [
        { label: "Open Profile", href: "/user-settings" },
        { label: "Open Account Security", href: "/user-settings/account-login" },
        { label: "Review Audit Trail", href: "/settings/audit" },
      ],
      activityTitle: "Recent Privacy Activity",
      activity: [
        { date: "Mar 7", event: "Email visibility changed" },
        { date: "Mar 5", event: "Search discoverability updated" },
        { date: "Mar 3", event: "Online status visibility changed" },
      ],
    },
    "/user-settings/workspace-preferences": {
      helpTitle: "Workspace Preferences",
      helpBody: [
        "Set default theme, layout behavior, and dashboard composition.",
        "These options personalize interface behavior without changing global policy.",
      ],
      recommendationsTitle: "Recommended Workspace Setup",
      recommendations: [
        "Use system theme for consistent day/night behavior.",
        "Set landing page to your most-used operational module.",
        "Limit dashboard widgets to key indicators for faster focus.",
      ],
      quickActions: [
        { label: "Open Default Dashboard", href: "/" },
        { label: "Open Reporting Engine", href: "/settings/reporting-engine" },
        { label: "Open Modules & Features", href: "/settings/modules" },
      ],
      activityTitle: "Recent Workspace Activity",
      activity: [
        { date: "Mar 7", event: "Sidebar behavior updated" },
        { date: "Mar 6", event: "Widget order changed" },
        { date: "Mar 4", event: "Theme preference updated" },
      ],
    },
    "/user-settings/task-workflow-preferences": {
      helpTitle: "Task and Workflow Preferences",
      helpBody: [
        "Configure default task views, reminder timing, and delegation behavior.",
        "These settings optimize workflow handling for your operating role.",
      ],
      recommendationsTitle: "Recommended Workflow Setup",
      recommendations: [
        "Managers: set reminders before SLA thresholds.",
        "Approvers: use delegation rules when out of office.",
        "Project users: auto-subscribe to project updates.",
      ],
      quickActions: [
        { label: "Open Delegations", href: "/settings/workflows/delegations" },
        { label: "Open Approval Policies", href: "/settings/workflows/policies" },
        { label: "Open Workflow Builder", href: "/settings/workflows" },
      ],
      activityTitle: "Recent Workflow Activity",
      activity: [
        { date: "Mar 7", event: "Default task view changed" },
        { date: "Mar 5", event: "Reminder timing updated" },
        { date: "Mar 2", event: "Delegation rule changed" },
      ],
    },
    "/user-settings/calendar-scheduling": {
      helpTitle: "Calendar and Scheduling",
      helpBody: [
        "Manage working windows, meeting defaults, and calendar sync providers.",
        "Scheduling preferences affect reminders and deadline interpretation.",
      ],
      recommendationsTitle: "Recommended Scheduling Setup",
      recommendations: [
        "Keep timezone override aligned with your main working location.",
        "Use meeting buffers to reduce scheduling collisions.",
        "Enable only active calendar providers for cleaner synchronization.",
      ],
      quickActions: [
        { label: "Open Task Preferences", href: "/user-settings/task-workflow-preferences" },
        { label: "Open Notifications", href: "/user-settings/notifications-alerts" },
        { label: "Review Audit Logs", href: "/settings/audit" },
      ],
      activityTitle: "Recent Scheduling Activity",
      activity: [
        { date: "Mar 7", event: "Working hours updated" },
        { date: "Mar 6", event: "Timezone override changed" },
        { date: "Mar 1", event: "Calendar sync provider enabled" },
      ],
    },
    "/user-settings/data-export-preferences": {
      helpTitle: "Data and Export Preferences",
      helpBody: [
        "Control default export format, report filters, and table display behavior.",
        "Saved views let you reuse common analysis configurations quickly.",
      ],
      recommendationsTitle: "Recommended Data Setup",
      recommendations: [
        "Set export format based on your most frequent downstream workflow.",
        "Use saved views for recurring operational and board reporting cuts.",
        "Restrict visible columns to reduce noise in large tables.",
      ],
      quickActions: [
        { label: "Open Reporting Engine", href: "/settings/reporting-engine" },
        { label: "Open Master Data", href: "/settings/master-data" },
        { label: "Review Audit Logs", href: "/settings/audit" },
      ],
      activityTitle: "Recent Data Preference Activity",
      activity: [
        { date: "Mar 7", event: "Default export format changed" },
        { date: "Mar 5", event: "Saved view updated" },
        { date: "Mar 4", event: "Rows per page changed" },
      ],
    },
    "/user-settings/integrations": {
      helpTitle: "User Integrations",
      helpBody: [
        "Manage user-owned external integrations such as Drive, Slack, and webhooks.",
        "Use connect, revoke, and token refresh actions to maintain secure access.",
      ],
      recommendationsTitle: "Recommended Integration Setup",
      recommendations: [
        "Keep only required integrations connected.",
        "Rotate tokens regularly for critical external services.",
        "Use descriptive account labels for easier support and audits.",
      ],
      quickActions: [
        { label: "Open Integration Governance", href: "/settings/integration-governance" },
        { label: "Open Security Controls", href: "/settings/security" },
        { label: "Review Audit Logs", href: "/settings/audit" },
      ],
      activityTitle: "Recent Integration Activity",
      activity: [
        { date: "Mar 7", event: "Slack integration connected" },
        { date: "Mar 6", event: "Token refreshed for Google Drive" },
        { date: "Mar 2", event: "Webhook integration revoked" },
      ],
    },
    "/user-settings/accessibility": {
      helpTitle: "Accessibility Settings",
      helpBody: [
        "Adjust readability and interaction preferences for different usability needs.",
        "These settings support font scaling, contrast, reduced motion, and assistive behavior.",
      ],
      recommendationsTitle: "Recommended Accessibility Setup",
      recommendations: [
        "Enable high contrast in glare-prone or low-visibility environments.",
        "Enable reduced motion when animation causes distraction.",
        "Keep keyboard navigation enabled for faster non-mouse workflows.",
      ],
      quickActions: [
        { label: "Open Workspace Preferences", href: "/user-settings/workspace-preferences" },
        { label: "Open Notifications", href: "/user-settings/notifications-alerts" },
        { label: "Review Audit Logs", href: "/settings/audit" },
      ],
      activityTitle: "Recent Accessibility Activity",
      activity: [
        { date: "Mar 7", event: "Font size changed" },
        { date: "Mar 6", event: "High contrast mode toggled" },
        { date: "Mar 4", event: "Keyboard navigation updated" },
      ],
    },
  };

  function isActive(href: string, exact?: boolean): boolean {
    if (exact) return $page.url.pathname === href;
    return $page.url.pathname.startsWith(href);
  }

  function resolvePanelContent(pathname: string): RightPanelContent {
    let bestMatch = "/user-settings";
    for (const key of Object.keys(rightPanelByPath)) {
      if (key === "/user-settings") continue;
      if (pathname.startsWith(key) && key.length > bestMatch.length) {
        bestMatch = key;
      }
    }
    return rightPanelByPath[bestMatch] ?? rightPanelByPath["/user-settings"];
  }

  function compact(value: string, limit = 90): string {
    const text = value.trim();
    if (text.length <= limit) return text;
    return `${text.slice(0, limit - 3).trimEnd()}...`;
  }

  let panelReady = $state(false);
  let panelLoading = $state(false);
  let panelContent = $state<RightPanelContent | null>(null);

  async function loadPanelContext(pathname: string) {
    panelLoading = true;
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    panelContent = resolvePanelContent(pathname);
    panelLoading = false;
  }

  onMount(() => {
    requestAnimationFrame(() => {
      panelReady = true;
    });
  });

  $effect(() => {
    const pathname = $page.url.pathname;
    if (!panelReady) return;
    void loadPanelContext(pathname);
  });

  let accountSecurity = $state<UserAccountSecurity | null>(null);
  let notificationPreferences = $state<UserNotificationPreferences | null>(null);
  let taskWorkflowPreferences = $state<UserTaskWorkflowPreferences | null>(null);
  let profileSettings = $state<UserSettingsProfile | null>(null);
  let configurationHealthLoaded = $state(false);
  let configurationHealthLoading = $state(false);

  async function loadConfigurationHealthSignal() {
    configurationHealthLoading = true;
    try {
      const [security, notifications, workflow, profile] = await Promise.all([
        api.get<UserAccountSecurity>("/auth/account-security/"),
        api.get<UserNotificationPreferences>("/auth/notification-preferences/"),
        api.get<UserTaskWorkflowPreferences>("/auth/task-workflow-preferences/"),
        api.get<UserSettingsProfile>("/auth/profile/"),
      ]);
      accountSecurity = security;
      notificationPreferences = notifications;
      taskWorkflowPreferences = workflow;
      profileSettings = profile;
    } catch {
      accountSecurity = null;
      notificationPreferences = null;
      taskWorkflowPreferences = null;
      profileSettings = null;
    }
    configurationHealthLoading = false;
    configurationHealthLoaded = true;
  }

  $effect(() => {
    const pathname = $page.url.pathname;
    if (!panelReady || !pathname.startsWith("/user-settings")) {
      accountSecurity = null;
      notificationPreferences = null;
      taskWorkflowPreferences = null;
      profileSettings = null;
      configurationHealthLoaded = false;
      configurationHealthLoading = false;
      return;
    }
    if (!configurationHealthLoaded && !configurationHealthLoading) {
      void loadConfigurationHealthSignal();
    }
  });

  const configurationHealth = $derived.by((): ConfigurationHealth | null => {
    if (!configurationHealthLoaded) return null;

    const securityOk = Boolean(accountSecurity?.mfa_enabled);
    const notificationsOk = Boolean(
      notificationPreferences
      && (
        notificationPreferences.channel_in_app_enabled
        || notificationPreferences.channel_email_enabled
        || notificationPreferences.channel_push_enabled
        || notificationPreferences.channel_sms_enabled
      )
      && notificationPreferences.categories.some((row) => row.enabled)
    );
    const delegationOk = Boolean(
      taskWorkflowPreferences
      && (
        taskWorkflowPreferences.approval_delegation_rule === "use_active_delegations"
        || taskWorkflowPreferences.approval_delegation_rule === "auto_when_out_of_office"
      )
    );
    const profileOk = Boolean(
      profileSettings
      && profileSettings.full_name.trim()
      && profileSettings.job_title.trim()
      && profileSettings.department_id !== null
    );

    const items: ConfigurationHealthItem[] = [
      { label: "Security", ok: securityOk, detail: securityOk ? "Configured" : "Missing" },
      { label: "Notifications", ok: notificationsOk, detail: notificationsOk ? "Configured" : "Missing" },
      { label: "Delegation", ok: delegationOk, detail: delegationOk ? "Configured" : "Missing" },
      { label: "Profile", ok: profileOk, detail: profileOk ? "Configured" : "Missing" },
    ];

    const passCount = items.filter((item) => item.ok).length;
    const warnCount = items.length - passCount;
    const score = Math.max(
      0,
      Math.min(
        100,
        Math.round(((passCount + warnCount * 0.28) / items.length) * 100)
      )
    );

    return {
      items,
      score,
    };
  });

  const smartRecommendation = $derived.by((): SmartRecommendation | null => {
    if (!panelReady) return null;
    if (!$page.url.pathname.startsWith("/user-settings/account-login")) return null;
    if (!configurationHealthLoaded || !accountSecurity) return null;
    if (!accountSecurity.mfa_enabled) {
      return {
        title: "Security Warning",
        lines: [
          "You have not enabled Two-Factor Authentication.",
          "Enable it to prevent unauthorized access.",
        ],
        actionLabel: "Enable 2FA",
        actionHref: "/user-settings/account-login",
      };
    }
    return null;
  });
</script>

<div class="h-screen flex flex-col bg-neutral-50 font-sans">
  <header class="bg-neutral-900 shrink-0">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <a href="/" class="text-lg">
          <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
        </a>
        <span class="text-neutral-600">|</span>
        <h1 class="text-sm font-semibold text-white">User Settings</h1>
      </div>
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to app
      </a>
    </div>
  </header>

  <div class="max-w-7xl mx-auto px-6 flex gap-8 flex-1 min-h-0 w-full">
    <aside class="w-56 shrink-0 overflow-y-auto py-8">
      {#each menuSections as section}
        <div class="mb-8">
          <p class="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3 px-3">
            {section.title}
          </p>
          <nav class="space-y-0.5">
            {#each section.items as item}
              <a
                href={item.href}
                class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                       {isActive(item.href, item.exact)
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>
      {/each}
    </aside>

    <div class="flex-1 min-w-0 overflow-y-auto py-8">
      <div class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div class="min-w-0">
          {@render children()}
        </div>

        <aside class="hidden xl:block">
          <div class="space-y-4">
            {#if !panelReady || panelLoading || !panelContent}
              <section class="rounded-xl border border-neutral-200 bg-white p-4">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Right Panel</p>
                <div class="mt-3 space-y-2">
                  <div class="h-3 w-3/4 animate-pulse rounded bg-neutral-200"></div>
                  <div class="h-3 w-full animate-pulse rounded bg-neutral-200"></div>
                  <div class="h-3 w-5/6 animate-pulse rounded bg-neutral-200"></div>
                </div>
              </section>
            {:else}
            {#if smartRecommendation}
              <section class="rounded-xl border border-amber-300 bg-amber-50 p-4">
                <div class="flex items-start gap-2">
                  <svg
                    class="mt-0.5 h-4 w-4 shrink-0 text-amber-700"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                    aria-hidden="true"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.72 3h16.92a2 2 0 0 0 1.72-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
                  </svg>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-amber-900">{smartRecommendation.title}</p>
                    <div class="mt-1 space-y-1">
                      {#each smartRecommendation.lines as line}
                        <p class="text-xs text-amber-800">{line}</p>
                      {/each}
                    </div>
                    {#if smartRecommendation.actionLabel && smartRecommendation.actionHref}
                      <a
                        href={smartRecommendation.actionHref}
                        class="mt-3 inline-flex rounded-lg border border-amber-500 bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-200"
                      >
                        {smartRecommendation.actionLabel}
                      </a>
                    {/if}
                  </div>
                </div>
              </section>
            {/if}

            {#if configurationHealth}
              <section class="rounded-xl border border-neutral-200 bg-white p-4">
                <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 0a8.25 8.25 0 1 1 16.5 0m-16.5 0a8.25 8.25 0 0 0 16.5 0" />
                  </svg>
                  <span>Configuration Health</span>
                </p>
                <h2 class="mt-2 text-sm font-semibold text-neutral-900">System Configuration Health</h2>
                <ul class="mt-2 space-y-2">
                  {#each configurationHealth.items as item}
                    <li class="flex items-center justify-between gap-2 text-xs">
                      <span class="text-neutral-700">{item.label}</span>
                      {#if item.ok}
                        <span class="inline-flex items-center gap-1 font-semibold text-emerald-700">
                          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m5 13 4 4L19 7" />
                          </svg>
                        </span>
                      {:else}
                        <span class="inline-flex items-center gap-1 font-semibold text-amber-700">
                          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.72 3h16.92a2 2 0 0 0 1.72-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
                          </svg>
                          <span>{item.detail}</span>
                        </span>
                      {/if}
                    </li>
                  {/each}
                </ul>
                <p class="mt-3 text-xs text-neutral-700">
                  <span class="font-semibold">Overall Score:</span>
                  <span class="ml-1">{configurationHealth.score}%</span>
                </p>
              </section>
            {/if}

            {#if panelContent.spotlight}
              <section class="rounded-xl border border-neutral-200 bg-white p-4">
                <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m12 3 2.25 6.75H21l-5.25 3.75L17.25 21 12 17.25 6.75 21l1.5-7.5L3 9.75h6.75L12 3Z" />
                  </svg>
                  <span>Page Spotlight</span>
                </p>
                <h2 class="mt-2 text-sm font-semibold text-neutral-900">{panelContent.spotlight.title}</h2>

                {#if panelContent.spotlight.paragraphs.length > 0}
                  <ul class="mt-2 space-y-1.5">
                    {#each panelContent.spotlight.paragraphs as paragraph}
                      <li class="flex items-start gap-1.5">
                        <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75" />
                        </svg>
                        <span class="text-xs leading-relaxed text-neutral-600">{compact(paragraph)}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}

                {#if panelContent.spotlight.scoreRows && panelContent.spotlight.scoreRows.length > 0}
                  <div class="mt-3 space-y-2">
                    {#each panelContent.spotlight.scoreRows as row}
                      <div class="flex items-center justify-between gap-2 text-xs">
                        <span class="text-neutral-700">{row.label}</span>
                        <span class="inline-flex items-center gap-1 font-semibold {row.isPositive ? 'text-emerald-700' : 'text-red-700'}">
                          {#if row.isPositive}
                            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                              <path stroke-linecap="round" stroke-linejoin="round" d="m5 13 4 4L19 7" />
                            </svg>
                          {:else}
                            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                            </svg>
                          {/if}
                          <span>{row.value}</span>
                        </span>
                      </div>
                    {/each}
                  </div>
                {/if}

                {#if panelContent.spotlight.rating}
                  <p class="mt-3 text-xs text-neutral-700">
                    <span class="font-semibold">Security Rating:</span>
                    <span class="ml-1">{panelContent.spotlight.rating}</span>
                  </p>
                {/if}

                {#if panelContent.spotlight.recommendation}
                  <p class="mt-2 text-xs text-neutral-700">
                    <span class="font-semibold">Recommendation:</span>
                    <span class="ml-1">{panelContent.spotlight.recommendation}</span>
                  </p>
                {/if}

                {#if panelContent.spotlight.listTitle && panelContent.spotlight.list && panelContent.spotlight.list.length > 0}
                  <div class="mt-3">
                    <p class="text-xs font-semibold text-neutral-700">{panelContent.spotlight.listTitle}</p>
                    <ul class="mt-1.5 space-y-1.5">
                      {#each panelContent.spotlight.list as item}
                        <li class="flex items-start gap-1.5 text-xs text-neutral-600">
                          <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m9 12.75 2.25 2.25L15 9.75" />
                          </svg>
                          <span>{compact(item, 60)}</span>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              </section>
            {/if}

            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 17h.01M12 13.5V7.5m9 4.5a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                <span>Contextual Help</span>
              </p>
              <h2 class="mt-2 text-sm font-semibold text-neutral-900">{panelContent.helpTitle}</h2>
              <ul class="mt-2 space-y-1.5">
                {#each panelContent.helpBody as paragraph}
                  <li class="flex items-start gap-1.5">
                    <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75" />
                    </svg>
                    <span class="text-xs leading-relaxed text-neutral-600">{compact(paragraph)}</span>
                  </li>
                {/each}
              </ul>
            </section>

            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 3a4.5 4.5 0 0 0-2.95 7.9c.45.39.7.95.7 1.54V13.5h4.5v-1.06c0-.59.25-1.15.7-1.54A4.5 4.5 0 0 0 12 3Zm-2.25 13.5h4.5m-4.5 3h4.5" />
                </svg>
                <span>Best Practices</span>
              </p>
              <h3 class="mt-2 text-sm font-semibold text-neutral-900">{panelContent.recommendationsTitle}</h3>
              <ul class="mt-2 space-y-1.5">
                {#each panelContent.recommendations as recommendation}
                  <li class="flex items-start gap-1.5">
                    <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5 13 4 4L19 7" />
                    </svg>
                    <span class="text-xs leading-relaxed text-neutral-600">{compact(recommendation)}</span>
                  </li>
                {/each}
              </ul>
            </section>

            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m13 10 5-5m0 0h-4m4 0v4M11 14l-5 5m0 0h4m-4 0v-4" />
                </svg>
                <span>Quick Actions</span>
              </p>
              <div class="mt-2 space-y-2">
                {#each panelContent.quickActions as action}
                  <a
                    href={action.href}
                    class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs font-semibold text-neutral-700 transition-colors hover:bg-neutral-100"
                  >
                    <span>{compact(action.label, 34)}</span>
                    <svg class="h-3.5 w-3.5 shrink-0 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
                    </svg>
                  </a>
                {/each}
              </div>
            </section>

            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l4 2m5-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                <span>Activity</span>
              </p>
              <h3 class="mt-2 text-sm font-semibold text-neutral-900">{panelContent.activityTitle}</h3>
              <ul class="mt-2 space-y-2">
                {#each panelContent.activity as item}
                  <li class="flex items-start gap-1.5 text-xs text-neutral-600">
                    <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l4 2" />
                    </svg>
                    <span>
                      <span class="font-semibold text-neutral-700">{item.date}</span>
                      <span class="mx-1">-</span>
                      <span>{compact(item.event, 54)}</span>
                    </span>
                  </li>
                {/each}
              </ul>
            </section>
            {/if}
          </div>
        </aside>
      </div>
    </div>
  </div>
</div>
