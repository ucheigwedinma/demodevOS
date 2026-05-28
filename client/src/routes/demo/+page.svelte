<script lang="ts">
  const modules = [
    {
      title: "Finance Intelligence",
      description: "Cash flow analytics, budgets, invoices, and payment tracking across all projects.",
      icon: "finance",
    },
    {
      title: "Project Management",
      description: "Construction tracking, milestones, risk management, and contractor coordination.",
      icon: "project",
    },
    {
      title: "CRM & Sales",
      description: "Lead pipeline, reservations, unit inventory, and buyer lifecycle management.",
      icon: "crm",
    },
    {
      title: "Document Governance",
      description: "Compliance-grade retention policies, version control, and approval workflows.",
      icon: "document",
    },
    {
      title: "Procurement",
      description: "Vendor management, RFQs, purchase orders, and contract lifecycle tracking.",
      icon: "procurement",
    },
    {
      title: "HR & Workforce",
      description: "Employee records, attendance, payroll processing, and workforce scheduling.",
      icon: "hr",
    },
  ];
</script>

<svelte:head><title>See developerOS in Action</title></svelte:head>

<div class="min-h-screen flex flex-col">
  <!-- Top Nav -->
  <div class="bg-white/80 backdrop-blur-md border-b border-neutral-200/60 sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-6 py-2 flex items-center justify-between">
      <a href="/">
        <img src="/logo-light.png" alt="developerOS" class="h-14 w-auto" />
      </a>
      <div class="flex items-center gap-3">
        <a
          href="/request-demo"
          class="text-sm font-semibold text-white bg-neutral-900 rounded-lg px-4 py-2 hover:bg-neutral-800 transition-colors"
        >
          Request Demo
        </a>
        <a
          href="/login"
          class="text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg px-4 py-2 hover:bg-neutral-50 transition-colors"
        >
          Login
        </a>
      </div>
    </div>
  </div>

  <!-- Hero -->
  <div class="bg-white">
    <div class="max-w-4xl mx-auto px-6 py-24 text-center">
      <div class="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-4 py-1.5 text-xs font-medium text-neutral-600 mb-8 hero-badge">
        <span class="h-1.5 w-1.5 rounded-full bg-neutral-900"></span>
        Live Interactive Demo
      </div>

      <h1 class="text-4xl sm:text-5xl font-bold text-neutral-900 tracking-tight leading-tight hero-title">
        See <span class="font-normal">developer</span><span class="font-bold text-neutral-400">OS</span> in action
      </h1>

      <p class="mt-6 text-lg text-neutral-500 max-w-2xl mx-auto leading-relaxed hero-subtitle">
        The all-in-one platform for real estate development management. Explore a fully loaded demo with real data — finance, projects, CRM, and more.
      </p>

      <div class="mt-10 flex items-center justify-center gap-4 hero-actions">
        <a
          href="/request-demo"
          class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-6 py-3 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors shadow-sm"
        >
          Request a Demo
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
          </svg>
        </a>
        <a
          href="/login"
          class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-6 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Login to Demo
        </a>
      </div>
    </div>
  </div>

  <!-- Module Showcase -->
  <div class="bg-neutral-50 border-t border-neutral-200/60">
    <div class="max-w-5xl mx-auto px-6 py-20">
      <div class="text-center mb-14">
        <h2 class="text-2xl font-bold text-neutral-900">Everything you need, in one platform</h2>
        <p class="mt-3 text-sm text-neutral-500 max-w-lg mx-auto">
          Built for real estate developers who need operational leverage, revenue visibility, and execution control.
        </p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each modules as mod, i}
          <div class="group rounded-2xl border border-neutral-200/80 bg-white p-7 hover:shadow-md hover:border-neutral-300 transition-all duration-300 module-card" style="animation-delay: {i * 0.08}s;">
            <div class="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-neutral-100 group-hover:bg-neutral-900 transition-colors duration-300">
              {#if mod.icon === "finance"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
                </svg>
              {:else if mod.icon === "project"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
                </svg>
              {:else if mod.icon === "crm"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
                </svg>
              {:else if mod.icon === "document"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
              {:else if mod.icon === "procurement"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
                </svg>
              {:else if mod.icon === "hr"}
                <svg class="w-5 h-5 text-neutral-600 group-hover:text-white transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0Z" />
                </svg>
              {/if}
            </div>
            <h3 class="text-base font-semibold text-neutral-900">{mod.title}</h3>
            <p class="mt-2 text-sm text-neutral-500 leading-relaxed">{mod.description}</p>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Stats Bar -->
  <div class="bg-white border-t border-neutral-200/60">
    <div class="max-w-5xl mx-auto px-6 py-16">
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
        <div class="stat-item" style="animation-delay: 0s;">
          <p class="text-3xl font-bold text-neutral-900">12+</p>
          <p class="mt-1 text-sm text-neutral-500">Integrated Modules</p>
        </div>
        <div class="stat-item" style="animation-delay: 0.1s;">
          <p class="text-3xl font-bold text-neutral-900">100%</p>
          <p class="mt-1 text-sm text-neutral-500">Multi-Tenant Isolated</p>
        </div>
        <div class="stat-item" style="animation-delay: 0.2s;">
          <p class="text-3xl font-bold text-neutral-900">14</p>
          <p class="mt-1 text-sm text-neutral-500">Day Free Trial</p>
        </div>
        <div class="stat-item" style="animation-delay: 0.3s;">
          <p class="text-3xl font-bold text-neutral-900">0</p>
          <p class="mt-1 text-sm text-neutral-500">Credit Card Required</p>
        </div>
      </div>
    </div>
  </div>

  <!-- CTA Footer -->
  <div class="bg-neutral-900">
    <div class="max-w-4xl mx-auto px-6 py-20 text-center">
      <h2 class="text-2xl font-bold text-white">Ready to see it live?</h2>
      <p class="mt-3 text-sm text-neutral-400 max-w-md mx-auto">
        Get your own demo environment in under a minute. Pre-loaded with sample data so you can explore everything.
      </p>
      <div class="mt-8">
        <a
          href="/request-demo"
          class="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-neutral-900 hover:bg-neutral-100 transition-colors"
        >
          Request a Demo
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
          </svg>
        </a>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="bg-neutral-950 px-6 py-6">
    <p class="text-center text-xs text-neutral-500">
      &copy; {new Date().getFullYear()} <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
    </p>
  </div>
</div>

<style>
  .hero-badge {
    animation: fadeUp 0.5s ease-out both;
  }

  .hero-title {
    animation: fadeUp 0.5s ease-out 0.1s both;
  }

  .hero-subtitle {
    animation: fadeUp 0.5s ease-out 0.2s both;
  }

  .hero-actions {
    animation: fadeUp 0.5s ease-out 0.3s both;
  }

  .module-card {
    animation: fadeUp 0.4s ease-out both;
  }

  .stat-item {
    animation: fadeUp 0.4s ease-out both;
  }

  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(12px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
