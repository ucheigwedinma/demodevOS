<script lang="ts">
  import { api } from "$lib/api";

  interface LifecycleStages {
    pending_invitations: number;
    pending_onboarding: number;
    active: number;
    suspended: number;
    locked: number;
    never_logged_in: number;
  }

  interface TimelineEvent {
    type: string;
    label: string;
    status: string;
    timestamp: string;
  }

  interface LifecycleResponse {
    stages: LifecycleStages;
    timeline: TimelineEvent[];
  }

  let stages = $state<LifecycleStages>({
    pending_invitations: 0,
    pending_onboarding: 0,
    active: 0,
    suspended: 0,
    locked: 0,
    never_logged_in: 0,
  });
  let timeline = $state<TimelineEvent[]>([]);
  let loading = $state(true);

  let totalUsers = $derived(stages.active + stages.suspended + stages.locked);

  const stageDefinitions = [
    {
      key: "pending_invitations" as const,
      label: "Invited",
      description: "Invitation sent, account not yet created",
      icon: "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
    },
    {
      key: "pending_onboarding" as const,
      label: "Onboarding",
      description: "Account created, setup not completed",
      icon: "M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z",
    },
    {
      key: "active" as const,
      label: "Active",
      description: "Fully provisioned and operational",
      icon: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    },
    {
      key: "suspended" as const,
      label: "Suspended",
      description: "Access temporarily revoked",
      icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
    },
    {
      key: "locked" as const,
      label: "Locked",
      description: "Account locked due to policy violation",
      icon: "M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z",
    },
  ];

  const eventIcons: Record<string, string> = {
    invitation: "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
    joined: "M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM3 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 9.374 21c-2.331 0-4.512-.645-6.374-1.766Z",
  };

  const eventColors: Record<string, string> = {
    invitation: "bg-amber-50 text-amber-600",
    joined: "bg-emerald-50 text-emerald-600",
  };

  function formatRelative(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  async function fetchLifecycle() {
    loading = true;
    try {
      const res = await api.get<LifecycleResponse>("/iam/users/lifecycle/");
      stages = res.stages;
      timeline = res.timeline;
    } catch {
      // error state
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchLifecycle();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">User Lifecycle</h1>
    <p class="mt-1 text-sm text-neutral-500">Track onboarding progress, account states, and recent identity events.</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else}
    <!-- Pipeline -->
    <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
      <div class="px-6 py-5">
        <h2 class="text-sm font-semibold text-neutral-900">Lifecycle Pipeline</h2>
        <p class="mt-0.5 text-xs text-neutral-400">Current distribution of users across lifecycle stages.</p>
      </div>

      <div class="px-6 py-6">
        <!-- Stage flow -->
        <div class="flex items-stretch gap-0">
          {#each stageDefinitions as stage, i}
            {@const count = stages[stage.key]}
            <div class="flex-1 flex flex-col items-center text-center relative">
              <!-- Connector line -->
              {#if i > 0}
                <div class="absolute left-0 top-6 w-full h-px bg-neutral-200 -translate-x-1/2 z-0"></div>
              {/if}

              <!-- Icon circle -->
              <div class="relative z-10 flex h-12 w-12 items-center justify-center rounded-full
                          {count > 0 ? 'bg-neutral-900' : 'bg-neutral-100'}">
                <svg class="w-5 h-5 {count > 0 ? 'text-white' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d={stage.icon} />
                </svg>
              </div>

              <!-- Count -->
              <p class="mt-3 text-2xl font-bold {count > 0 ? 'text-neutral-900' : 'text-neutral-300'}">{count}</p>
              <p class="mt-0.5 text-xs font-semibold uppercase tracking-wider {count > 0 ? 'text-neutral-600' : 'text-neutral-400'}">{stage.label}</p>
              <p class="mt-1 text-[11px] text-neutral-400 leading-snug max-w-[140px]">{stage.description}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Health indicators -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Provisioned</p>
        <p class="mt-2 text-2xl font-bold text-neutral-900">{totalUsers}</p>
        <p class="mt-1 text-xs text-neutral-400">Users with created accounts</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Pending Invitations</p>
        <p class="mt-2 text-2xl font-bold {stages.pending_invitations > 0 ? 'text-amber-700' : 'text-neutral-300'}">{stages.pending_invitations}</p>
        <p class="mt-1 text-xs text-neutral-400">Awaiting account creation</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Never Logged In</p>
        <p class="mt-2 text-2xl font-bold {stages.never_logged_in > 0 ? 'text-amber-700' : 'text-neutral-300'}">{stages.never_logged_in}</p>
        <p class="mt-1 text-xs text-neutral-400">Account exists but no login recorded</p>
      </div>
    </div>

    <!-- Timeline -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-6 py-5 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900">Recent Activity</h2>
        <p class="mt-0.5 text-xs text-neutral-400">Lifecycle events from the past 30 days.</p>
      </div>

      {#if timeline.length === 0}
        <div class="flex flex-col items-center justify-center py-16 text-center">
          <div class="text-neutral-300 mb-3">
            <svg class="mx-auto h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </div>
          <p class="text-sm text-neutral-500">No recent activity</p>
        </div>
      {:else}
        <div class="divide-y divide-neutral-100">
          {#each timeline as event}
            <div class="flex items-center gap-4 px-6 py-3.5 hover:bg-neutral-50 transition-colors">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full {eventColors[event.type] ?? 'bg-neutral-100 text-neutral-500'}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d={eventIcons[event.type] ?? ""} />
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-neutral-700">{event.label}</p>
              </div>
              <p class="text-xs text-neutral-400 shrink-0">{formatRelative(event.timestamp)}</p>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
