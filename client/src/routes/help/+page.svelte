<script lang="ts">
  let searchQuery = $state("");

  const categories = [
    {
      title: "Getting Started",
      description: "Setting up your environment.",
      articles: ["Creating your Org Profile", "Inviting Team Members"],
      icon: "rocket",
    },
    {
      title: "Project Planning",
      description: "Managing the pre-construction phase.",
      articles: ["Uploading Blueprints", "Budgeting Basics"],
      icon: "blueprint",
    },
    {
      title: "Site Management",
      description: "Real-time tools for the field.",
      articles: ["Daily Logs", "Safety Checklists", "Vendor Tracking"],
      icon: "site",
    },
    {
      title: "Financials & Ops",
      description: 'The "OS" of your business.',
      articles: ["Invoicing", "Contract Management", "Draw Requests"],
      icon: "finance",
    },
    {
      title: "Data & Analytics",
      description: "Viewing your development at scale.",
      articles: ["Portfolio Reporting", "ROI Forecasting"],
      icon: "analytics",
    },
    {
      title: "Account & Security",
      description: "Keeping your data locked down.",
      articles: ["Resetting Passwords", "Two-Factor Auth (2FA)"],
      icon: "security",
    },
  ];

  const mostViewed = [
    { title: "How to set up your Company Profile (Step-by-Step)", href: "/help/articles/company-profile" },
    { title: "Integrating with your existing CRM", href: "/help" },
    { title: "Understanding Project Permissions and Roles", href: "/help" },
    { title: "Exporting Year-End Development Reports", href: "/help" },
  ];
</script>

<svelte:head><title>Help Center | developerOS</title></svelte:head>

<div class="min-h-screen bg-neutral-50 font-sans">
  <!-- Top Nav -->
  <div class="sticky top-0 z-20 bg-neutral-900/80 backdrop-blur-md border-b border-white/10">
    <div class="max-w-5xl mx-auto px-6 py-2 flex items-center justify-between">
      <a href="/help">
        <img src="/logo-dark.png" alt="developerOS" class="h-14 w-auto" />
      </a>
      <div class="flex items-center gap-4">
        <a href="/contact-support" class="text-sm text-neutral-400 hover:text-white transition-colors">Contact Support</a>
        <a href="/login" class="text-sm text-neutral-400 hover:text-white transition-colors">Sign in</a>
      </div>
    </div>
  </div>

  <!-- Hero Section -->
  <div class="relative bg-neutral-900 overflow-hidden">
    <div class="dot-grid"></div>
    <div class="absolute inset-0 bg-linear-to-b from-neutral-900/90 via-neutral-900/80 to-neutral-900"></div>

    <div class="relative z-10 max-w-3xl mx-auto px-6 pt-12 pb-24 text-center">
      <h1 class="text-3xl font-bold text-white">
        How can we help you build today?
      </h1>
      <p class="mt-3 text-sm text-neutral-400">
        Search our blueprints, tutorials, and documentation for <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>.
      </p>

      <!-- Search -->
      <div class="mt-8 relative">
        <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          type="text"
          class="w-full rounded-xl border border-neutral-700 bg-neutral-800/60 backdrop-blur-sm pl-12 pr-4 py-3.5 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-transparent transition-shadow"
          placeholder="Search for 'How to add a new project' or 'API integrations'..."
          bind:value={searchQuery}
        />
      </div>
    </div>
  </div>

  <!-- Category Grid -->
  <div class="relative z-10 max-w-5xl mx-auto px-6 -mt-14">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each categories as category}
        <div class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
          <div class="flex items-start gap-4">
            <div class="w-10 h-10 rounded-xl bg-neutral-100 flex items-center justify-center shrink-0 group-hover:bg-neutral-900 group-hover:text-white transition-colors text-neutral-600">
              {#if category.icon === "rocket"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z" />
                </svg>
              {:else if category.icon === "blueprint"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
                </svg>
              {:else if category.icon === "site"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
                </svg>
              {:else if category.icon === "finance"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
              {:else if category.icon === "analytics"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                </svg>
              {:else if category.icon === "security"}
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
                </svg>
              {/if}
            </div>
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">{category.title}</h3>
              <p class="text-xs text-neutral-500 mt-0.5">{category.description}</p>
            </div>
          </div>
          <ul class="mt-4 space-y-1.5 pl-14">
            {#each category.articles as article}
              <li class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors cursor-pointer flex items-center gap-1.5">
                <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
                {article}
              </li>
            {/each}
          </ul>
        </div>
      {/each}
    </div>
  </div>

  <!-- Most Viewed -->
  <div class="max-w-5xl mx-auto px-6 mt-16">
    <h2 class="text-lg font-semibold text-neutral-900 mb-4">Most viewed</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {#each mostViewed as item, i}
        <a
          href={item.href}
          class="flex items-center gap-4 rounded-xl border border-neutral-200 bg-white px-5 py-4 hover:shadow-sm transition-shadow group"
        >
          <span class="flex items-center justify-center w-8 h-8 rounded-lg bg-neutral-100 text-xs font-semibold text-neutral-500 shrink-0 group-hover:bg-neutral-900 group-hover:text-white transition-colors">
            {i + 1}
          </span>
          <span class="text-sm text-neutral-700 group-hover:text-neutral-900 transition-colors">{item.title}</span>
          <svg class="w-4 h-4 text-neutral-300 ml-auto shrink-0 group-hover:text-neutral-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </a>
      {/each}
    </div>
  </div>

  <!-- Support Footer -->
  <div class="max-w-5xl mx-auto px-6 mt-16 mb-12">
    <div class="rounded-2xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-6 py-5 border-b border-neutral-100">
        <h2 class="text-lg font-semibold text-neutral-900">The Site Office</h2>
        <p class="text-xs text-neutral-500 mt-0.5">Can't find what you need? Our team is here to help.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-neutral-100">
        <!-- Live Chat -->
        <div class="px-6 py-5 group cursor-pointer hover:bg-neutral-50 transition-colors">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center group-hover:bg-neutral-900 group-hover:text-white transition-colors text-neutral-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-neutral-900">Live Chat</h3>
          </div>
          <p class="text-xs text-neutral-500 leading-relaxed">
            Speak with a <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span> Specialist.
          </p>
          <p class="text-xs text-neutral-400 mt-1">Response time: &lt; 5 mins</p>
        </div>

        <!-- Submit Ticket -->
        <div class="px-6 py-5 group cursor-pointer hover:bg-neutral-50 transition-colors">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center group-hover:bg-neutral-900 group-hover:text-white transition-colors text-neutral-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-neutral-900">Submit a Ticket</h3>
          </div>
          <p class="text-xs text-neutral-500 leading-relaxed">
            Need a custom feature? Let us know.
          </p>
        </div>

        <!-- Community Forum -->
        <div class="px-6 py-5 group cursor-pointer hover:bg-neutral-50 transition-colors">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center group-hover:bg-neutral-900 group-hover:text-white transition-colors text-neutral-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
              </svg>
            </div>
            <h3 class="text-sm font-semibold text-neutral-900">Community Forum</h3>
          </div>
          <p class="text-xs text-neutral-500 leading-relaxed">
            Talk shop with other estate developers using the OS.
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- Page Footer -->
  <div class="border-t border-neutral-200 bg-white px-6 py-5">
    <div class="max-w-5xl mx-auto flex items-center justify-between">
      <p class="text-xs text-neutral-400">
        &copy; {new Date().getFullYear()} <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
      </p>
      <div class="flex gap-5 text-xs text-neutral-400">
        <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
        <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
        <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
      </div>
    </div>
  </div>
</div>

<style>
  .dot-grid {
    position: absolute;
    inset: 0;
    background-image: radial-gradient(circle, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
    background-size: 20px 20px;
  }
</style>
