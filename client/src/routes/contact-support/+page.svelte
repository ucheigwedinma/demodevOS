<script lang="ts">
  import { toast } from "$lib/stores/toast.svelte";

  let name = $state("");
  let email = $state("");
  let category = $state("");
  let message = $state("");
  let submitted = $state(false);
  let loading = $state(false);

  const categories = [
    "Account & Login Issues",
    "Password Recovery Help",
    "Billing & Payments",
    "Technical Issue",
    "Feature Request",
    "Other",
  ];

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!name || !email || !category || !message) {
      toast.error("Missing fields", "Please fill in all required fields.");
      return;
    }

    loading = true;
    // Submission routing will be connected once Support Desk is built
    await new Promise((resolve) => setTimeout(resolve, 600));
    loading = false;
    submitted = true;
  }
</script>

<svelte:head><title>Contact Support | developerOS</title></svelte:head>

<div class="min-h-screen flex flex-col">
  <!-- Top Nav -->
  <div class="bg-white/80 backdrop-blur-md border-b border-neutral-200/60">
    <div class="max-w-5xl mx-auto px-6 py-2 flex items-center justify-between">
      <a href="/">
        <img src="/logo-light.png" alt="developerOS" class="h-14 w-auto" />
      </a>
      <a
        href="/login"
        class="text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg px-4 py-2 hover:bg-neutral-50 transition-colors"
      >
        Login
      </a>
    </div>
  </div>

  <!-- Content -->
  <div class="flex-1 bg-neutral-50 flex items-center justify-center px-6 py-8">
    {#if submitted}
      <!-- Success State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-900 text-white success-icon">
          <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path class="check-path" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Message Received</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          We've received your support request and will get back to you at<br />
          <span class="font-medium text-neutral-700">{email}</span> as soon as possible.
        </p>
        <div class="mt-8 flex items-center justify-center gap-4 fade-in" style="animation-delay: 0.5s;">
          <a
            href="/login"
            class="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-900 hover:underline"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Return to Login
          </a>
        </div>
      </div>
    {:else}
      <!-- Form -->
      <div class="w-full max-w-lg">
        <!-- Icon -->
        <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <svg class="w-6 h-6 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z" />
          </svg>
        </div>

        <h1 class="text-3xl font-bold text-neutral-900">Contact Support</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed max-w-sm">
          Need help? Fill in the details below and our team will get back to you shortly.
        </p>

        <form class="mt-8 space-y-5" onsubmit={handleSubmit}>
          <!-- Name & Email row -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="name">
                Full Name
              </label>
              <input
                id="name"
                type="text"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="John Doe"
                bind:value={name}
                autocomplete="name"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="email">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="name@company.com"
                bind:value={email}
                autocomplete="email"
              />
            </div>
          </div>

          <!-- Category -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="category">
              Category
            </label>
            <div class="relative">
              <select
                id="category"
                bind:value={category}
                class="w-full appearance-none rounded-lg border border-neutral-300 px-3.5 py-3 pr-10 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow {!category ? 'text-neutral-400' : ''}"
              >
                <option value="" disabled>Select a category</option>
                {#each categories as cat}
                  <option value={cat}>{cat}</option>
                {/each}
              </select>
              <svg class="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </div>
          </div>

          <!-- Message -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="message">
              Message
            </label>
            <textarea
              id="message"
              rows="5"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow resize-none"
              placeholder="Describe your issue or question in detail..."
              bind:value={message}
            ></textarea>
          </div>

          <button
            type="submit"
            disabled={loading}
            class="w-full rounded-lg bg-neutral-900 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
          >
            {loading ? "Submitting..." : "Submit Request"}
          </button>
        </form>

        <!-- Back to login -->
        <div class="mt-6 text-center">
          <a
            href="/login"
            class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Return to Login
          </a>
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="bg-neutral-50 px-6 pb-8">
    <p class="text-center text-xs text-neutral-400">
      &copy; {new Date().getFullYear()} <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
    </p>
  </div>
</div>

<style>
  .success-icon {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .check-path {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawCheck 0.4s ease-out 0.3s forwards;
  }

  .fade-in {
    opacity: 0;
    animation: fadeUp 0.4s ease-out forwards;
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

  @keyframes drawCheck {
    to {
      stroke-dashoffset: 0;
    }
  }

  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
