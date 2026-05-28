<script lang="ts">
  import { onboarding } from "$lib/stores/onboarding.svelte";

  let currentStep = $state(0);

  const steps = [
    {
      icon: "rocket",
      title: "Welcome to your",
      subtitle: "Experience a fully loaded demo environment with real data. Explore every module and see how it transforms real estate development management.",
      accent: "from-neutral-800 to-neutral-950",
    },
    {
      icon: "dashboard",
      title: "Your Portfolio at a Glance",
      subtitle: "The executive dashboard gives you instant visibility into KPIs, active projects, cash flow, and operational signals — all in a single view.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "finance",
      title: "Financial Intelligence",
      subtitle: "Manage bills, invoices, and payments with complete cash flow analytics. Track payables and receivables across all your projects in real time.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "project",
      title: "Project Command Center",
      subtitle: "Track construction progress from planning to handover. Monitor phases, milestones, budgets, and contractor performance with drill-down detail.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "crm",
      title: "Sales & Client Pipeline",
      subtitle: "Manage leads, reservations, and buyer journeys. Track unit inventory, payment schedules, and pipeline forecasting in one unified view.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "document",
      title: "Document Governance",
      subtitle: "Compliance-grade document management with retention policies, version control, approval workflows, and full audit trails.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "check",
      title: "Explore Freely",
      subtitle: "Your demo is fully unlocked for 14 days. Dive into any module — Finance, Projects, CRM, Documents, Procurement, HR, and more.",
      accent: "from-neutral-800 to-neutral-950",
    },
  ];

  function next() {
    if (currentStep < steps.length - 1) {
      currentStep++;
    } else {
      onboarding.completeDemoTour();
    }
  }

  function back() {
    if (currentStep > 0) currentStep--;
  }

  function skip() {
    onboarding.completeDemoTour();
  }

  let step = $derived(steps[currentStep]);
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50 backdrop-blur-sm tour-backdrop"></div>

  <!-- Modal -->
  <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden tour-modal">
    <!-- Illustration Area -->
    <div class="relative h-52 bg-neutral-900 flex items-center justify-center overflow-hidden">
      <div class="dot-grid"></div>
      <div class="absolute inset-0 bg-linear-to-br {step.accent} opacity-80"></div>

      <div class="relative z-10 text-center">
        {#if step.icon === "rocket"}
          <img src="/logo-dark.png" alt="developerOS" class="h-32 mx-auto tour-icon" />
        {:else if step.icon === "dashboard"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z" />
            </svg>
          </div>
        {:else if step.icon === "finance"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
            </svg>
          </div>
        {:else if step.icon === "project"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
            </svg>
          </div>
        {:else if step.icon === "crm"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
            </svg>
          </div>
        {:else if step.icon === "document"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
        {:else if step.icon === "check"}
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z" />
            </svg>
          </div>
        {/if}
      </div>
    </div>

    <!-- Content -->
    <div class="p-8">
      {#key currentStep}
        <div class="tour-content">
          <h2 class="text-xl font-bold text-neutral-900">
            {#if currentStep === 0}
              {step.title} <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span> demo
            {:else}
              {step.title}
            {/if}
          </h2>
          <p class="mt-3 text-sm text-neutral-500 leading-relaxed">{step.subtitle}</p>
        </div>
      {/key}

      <!-- Step Indicators -->
      <div class="mt-6 flex items-center justify-center gap-1.5">
        {#each steps as _, i}
          <button
            class="h-1.5 rounded-full transition-all duration-300 {i === currentStep ? 'w-6 bg-neutral-900' : 'w-1.5 bg-neutral-200'}"
            onclick={() => (currentStep = i)}
            aria-label="Go to step {i + 1}"
          ></button>
        {/each}
      </div>

      <!-- Actions -->
      <div class="mt-8 flex items-center justify-between">
        <button
          onclick={skip}
          class="text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          Skip tour
        </button>

        <div class="flex items-center gap-3">
          {#if currentStep > 0}
            <button
              onclick={back}
              class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Back
            </button>
          {/if}
          <button
            onclick={next}
            class="rounded-lg bg-neutral-900 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
          >
            {currentStep === steps.length - 1 ? "Start Exploring" : "Next"}
          </button>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .dot-grid {
    position: absolute;
    inset: 0;
    background-image: radial-gradient(circle, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
    background-size: 16px 16px;
  }

  .tour-backdrop {
    animation: fadeIn 0.3s ease-out both;
  }

  .tour-modal {
    animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .tour-icon {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .tour-content {
    animation: fadeUp 0.3s ease-out both;
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

  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
