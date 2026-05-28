<script lang="ts">
  import { onboarding } from "$lib/stores/onboarding.svelte";

  let currentStep = $state(0);

  const steps = [
    {
      icon: "rocket",
      title: "Welcome to",
      subtitle: "The Real Estate Development Operating System. Let's take a quick tour of what you can do.",
      accent: "from-neutral-800 to-neutral-950",
    },
    {
      icon: "building",
      title: "Manage Properties",
      subtitle: "Track your entire real estate portfolio — land, buildings, estates. Monitor valuations, ownership records, and encumbrances all in one place.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "project",
      title: "Track Projects",
      subtitle: "Oversee construction and development projects from planning to completion. Manage phases, milestones, tasks, and budgets with full visibility.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "finance",
      title: "Handle Finances",
      subtitle: "Manage bills, invoices, and customers. Track payables and receivables with a clear financial overview of your operations.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "documents",
      title: "Organize Documents",
      subtitle: "Store, version, and share contracts, permits, drawings, and legal documents. Keep everything organized and accessible across your entire portfolio.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "compliance",
      title: "Stay Compliant",
      subtitle: "Track regulatory requirements, certifications, and approvals. Monitor deadlines and ensure every project meets local and national compliance standards.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "procurement",
      title: "Manage Procurement",
      subtitle: "Handle RFQs, purchase orders, and vendor management. Compare bids, track deliveries, and maintain a full audit trail of every procurement decision.",
      accent: "from-neutral-800 to-neutral-900",
    },
    {
      icon: "check",
      title: "You're all set!",
      subtitle: "You're ready to start managing your real estate portfolio. Dive in and explore your workspace.",
      accent: "from-neutral-800 to-neutral-950",
    },
  ];

  function next() {
    if (currentStep < steps.length - 1) {
      currentStep++;
    } else {
      onboarding.completeTour();
    }
  }

  function back() {
    if (currentStep > 0) currentStep--;
  }

  function skip() {
    onboarding.completeTour();
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

      <div class="relative z-10 text-center flex flex-col items-center justify-center">
        {#if step.icon === "rocket"}
          <img src="/logo-dark.png" alt="developerOS" class="h-32 mx-auto tour-icon" />
        {:else if step.icon === "building"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Properties</p>
        {:else if step.icon === "project"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Projects</p>
        {:else if step.icon === "finance"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Finances</p>
        {:else if step.icon === "documents"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Documents</p>
        {:else if step.icon === "compliance"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Compliance</p>
        {:else if step.icon === "procurement"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Procurement</p>
        {:else if step.icon === "check"}
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm tour-icon">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </div>
          <p class="mt-3 text-sm font-semibold text-white/40 tracking-wide uppercase tour-label">Ready</p>
        {/if}
      </div>
    </div>

    <!-- Content -->
    <div class="p-8">
      {#key currentStep}
        <div class="tour-content">
          <h2 class="text-xl text-neutral-900 {currentStep === 0 ? 'font-normal' : 'font-bold'}">
            {#if currentStep === 0}
              {step.title} <span class="font-bold text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>
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
            {currentStep === steps.length - 1 ? "Get Started" : "Next"}
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

  .tour-label {
    animation: fadeUp 0.3s ease-out 0.2s both;
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
