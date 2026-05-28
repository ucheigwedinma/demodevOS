<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { onboarding } from "$lib/stores/onboarding.svelte";

  interface SetupTask {
    key: string;
    label: string;
    href: string;
  }

  interface OperationalAction {
    label: string;
    href: string;
    description: string;
    iconPath: string;
  }

  const SETUP_TASKS: SetupTask[] = [
    { key: "profile_complete", label: "Complete your profile", href: "/user-settings" },
    { key: "first_project_created", label: "Create your first project", href: "/projects/new" },
    { key: "team_invited", label: "Invite team members", href: "/iam/users/invite" },
  ];

  // Icons travel with their action (not bound to a slot index), so we can
  // re-order without misaligning the glyphs.
  const ICON_DASHBOARD = "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z";
  const ICON_GRID = "M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25A2.25 2.25 0 0 1 8.25 10.5H6A2.25 2.25 0 0 1 3.75 8.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z";
  const ICON_PLAY = "M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z";
  const ICON_HELP = "M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25";

  const OPERATIONAL_ACTIONS: OperationalAction[] = [
    { label: "Browse your dashboard", href: "/dashboard/executive", description: "View KPIs, project status, and financial summaries", iconPath: ICON_DASHBOARD },
    { label: "Build a custom dashboard", href: "/dashboard/custom/builder", description: "Pick the widgets you care about and arrange your own grid", iconPath: ICON_GRID },
    { label: "Take a quick tour", href: "__tour__", description: "Revisit the platform feature walkthrough", iconPath: ICON_PLAY },
    { label: "Visit the Help Center", href: "/help", description: "Guides, FAQs, and support resources", iconPath: ICON_HELP },
  ];

  let status = $state<Record<string, boolean>>({});
  let loading = $state(true);

  let completedCount = $derived(
    SETUP_TASKS.filter((t) => status[t.key]).length,
  );
  let allSetupDone = $derived(completedCount === SETUP_TASKS.length);
  let pendingTasks = $derived(SETUP_TASKS.filter((t) => !status[t.key]));

  onMount(async () => {
    try {
      const res = await api.get<Record<string, boolean>>("/auth/getting-started-status/");
      status = res;
    } catch {
      // Default to all incomplete
    }
    loading = false;
  });

  function handleSetupTask(task: SetupTask) {
    onboarding.dismissGettingStarted();
    goto(task.href);
  }

  function handleOperationalAction(action: OperationalAction) {
    onboarding.dismissGettingStarted();
    if (action.href === "__tour__") {
      onboarding.replayTour();
    } else {
      goto(action.href);
    }
  }

  function handleDismiss() {
    onboarding.dismissGettingStarted();
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
  <div class="absolute inset-0 bg-black/50 backdrop-blur-sm gs-backdrop"></div>

  <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden gs-modal">
    <div class="h-1 bg-neutral-900"></div>

    <div class="p-8">
      <!-- Header -->
      <div class="text-center mb-6">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-100 gs-icon">
          {#if allSetupDone}
            <svg class="w-7 h-7 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.841m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z" />
            </svg>
          {:else}
            <svg class="w-7 h-7 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
          {/if}
        </div>
        <h2 class="text-xl font-bold text-neutral-900">
          {allSetupDone ? "You're ready to go!" : "Let's get you set up"}
        </h2>
        <p class="mt-2 text-sm text-neutral-500">
          {allSetupDone
            ? "Your workspace is configured. Here's what to explore next."
            : "A few quick steps to get the most out of your workspace."}
        </p>
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-10">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if !allSetupDone}
        <!-- Progress bar -->
        <div class="mb-6">
          <div class="flex items-center justify-between mb-2">
            <p class="text-xs font-medium text-neutral-500">Setup progress</p>
            <p class="text-xs font-semibold text-neutral-700">{completedCount} of {SETUP_TASKS.length}</p>
          </div>
          <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
            <div
              class="h-full rounded-full bg-neutral-900 transition-all duration-500 ease-out"
              style="width: {(completedCount / SETUP_TASKS.length) * 100}%"
            ></div>
          </div>
        </div>

        <!-- Setup tasks -->
        <div class="space-y-2.5">
          <!-- Completed tasks -->
          {#each SETUP_TASKS.filter((t) => status[t.key]) as task}
            <div class="flex items-center gap-3 rounded-xl border border-neutral-100 bg-neutral-50/50 px-4 py-3">
              <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-900">
                <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              </div>
              <span class="text-sm text-neutral-400 line-through">{task.label}</span>
            </div>
          {/each}

          <!-- Pending tasks — visual hierarchy: first pending = primary, second = secondary, third = tertiary -->
          {#each pendingTasks as task, i}
            {#if i === 0}
              <!-- Primary: high-contrast filled button -->
              <button
                onclick={() => handleSetupTask(task)}
                class="group flex w-full items-center gap-3 rounded-xl bg-neutral-900 px-4 py-3.5 text-left transition-all hover:bg-neutral-800"
              >
                <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-neutral-600">
                  <span class="text-[10px] font-bold text-neutral-400">{completedCount + 1}</span>
                </div>
                <span class="text-sm font-semibold text-white">{task.label}</span>
                <svg class="ml-auto w-4 h-4 text-neutral-500 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {:else if i === 1}
              <!-- Secondary: outlined -->
              <button
                onclick={() => handleSetupTask(task)}
                class="group flex w-full items-center gap-3 rounded-xl border border-neutral-200 px-4 py-3 text-left transition-all hover:border-neutral-300 hover:bg-neutral-50"
              >
                <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-neutral-200">
                  <span class="text-[10px] font-bold text-neutral-400">{completedCount + i + 1}</span>
                </div>
                <span class="text-sm font-medium text-neutral-700">{task.label}</span>
                <svg class="ml-auto w-4 h-4 text-neutral-300 opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {:else}
              <!-- Tertiary: text-only -->
              <button
                onclick={() => handleSetupTask(task)}
                class="group flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-all hover:bg-neutral-50"
              >
                <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-neutral-100">
                  <span class="text-[10px] font-bold text-neutral-300">{completedCount + i + 1}</span>
                </div>
                <span class="text-sm text-neutral-500">{task.label}</span>
                <svg class="ml-auto w-4 h-4 text-neutral-200 opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {/if}
          {/each}
        </div>

        <!-- Dismiss -->
        <div class="mt-6 text-center">
          <button
            onclick={handleDismiss}
            class="text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            I'll do this later
          </button>
        </div>
      {:else}
        <!-- All setup done — show operational actions -->
        <div class="space-y-2.5">
          {#each OPERATIONAL_ACTIONS as action, i}
            {#if i === 0}
              <!-- Primary -->
              <button
                onclick={() => handleOperationalAction(action)}
                class="group flex w-full items-center gap-3.5 rounded-xl bg-neutral-900 px-4 py-3.5 text-left transition-all hover:bg-neutral-800"
              >
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
                  <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d={action.iconPath} />
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-semibold text-white">{action.label}</p>
                  <p class="mt-0.5 text-xs text-neutral-400">{action.description}</p>
                </div>
                <svg class="w-4 h-4 text-neutral-500 shrink-0 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {:else if i === 1}
              <!-- Secondary -->
              <button
                onclick={() => handleOperationalAction(action)}
                class="group flex w-full items-center gap-3.5 rounded-xl border border-neutral-200 px-4 py-3 text-left transition-all hover:border-neutral-300 hover:bg-neutral-50"
              >
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100">
                  <svg class="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d={action.iconPath} />
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium text-neutral-700">{action.label}</p>
                  <p class="mt-0.5 text-xs text-neutral-400">{action.description}</p>
                </div>
                <svg class="ml-auto w-4 h-4 text-neutral-300 opacity-0 shrink-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {:else}
              <!-- Tertiary -->
              <button
                onclick={() => handleOperationalAction(action)}
                class="group flex w-full items-center gap-3.5 rounded-xl px-4 py-3 text-left transition-all hover:bg-neutral-50"
              >
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-50">
                  <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d={action.iconPath} />
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm text-neutral-500">{action.label}</p>
                  <p class="mt-0.5 text-xs text-neutral-300">{action.description}</p>
                </div>
                <svg class="ml-auto w-4 h-4 text-neutral-200 opacity-0 shrink-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            {/if}
          {/each}
        </div>

        <!-- Dismiss -->
        <div class="mt-6 text-center">
          <button
            onclick={handleDismiss}
            class="rounded-lg bg-neutral-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .gs-backdrop {
    animation: fadeIn 0.3s ease-out both;
  }

  .gs-modal {
    animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .gs-icon {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes modalSlideUp {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  @keyframes scaleIn {
    from {
      transform: scale(0);
      opacity: 0;
    }
    to {
      transform: scale(1);
      opacity: 1;
    }
  }
</style>
