<script lang="ts">
  import { toast } from "$lib/stores/toast.svelte";

  let fullName = $state("");
  let email = $state("");
  let companyName = $state("");
  let companySize = $state("");
  let phone = $state("");
  let message = $state("");
  let submitted = $state(false);
  let loading = $state(false);

  const companySizes = ["1-10", "11-50", "51-200", "201-500", "500+"];

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!fullName || !email || !companyName) {
      toast.error("Missing fields", "Please fill in all required fields.");
      return;
    }

    loading = true;
    try {
      const res = await fetch("/api/auth/request-demo/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email,
          company_name: companyName,
          company_size: companySize,
          phone,
          message,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail || data.email?.[0] || "Something went wrong. Please try again.";
        toast.error("Request failed", detail);
        loading = false;
        return;
      }
      submitted = true;
    } catch {
      toast.error("Network error", "Could not reach the server. Please try again.");
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Request a Demo | developerOS</title></svelte:head>

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
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Your Demo is Being Prepared</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          We're setting up a fully loaded demo environment just for you.<br />
          Check your inbox at <span class="font-medium text-neutral-700">{email}</span> for login credentials.
        </p>
        <p class="mt-2 text-xs text-neutral-400 fade-in" style="animation-delay: 0.45s;">
          This usually takes less than a minute.
        </p>
        <div class="mt-8 flex items-center justify-center gap-4 fade-in" style="animation-delay: 0.5s;">
          <a
            href="/login"
            class="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-900 hover:underline"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Go to Login
          </a>
        </div>
      </div>
    {:else}
      <!-- Form -->
      <div class="w-full max-w-lg">
        <!-- Icon -->
        <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <svg class="w-6 h-6 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
          </svg>
        </div>

        <h1 class="text-3xl font-bold text-neutral-900">Request a Demo</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed max-w-sm">
          Get a hands-on demo environment pre-loaded with sample data. Explore every module at your own pace.
        </p>

        <form class="mt-8 space-y-5" onsubmit={handleSubmit}>
          <!-- Name & Email row -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="fullName">
                Full Name <span class="text-neutral-400">*</span>
              </label>
              <input
                id="fullName"
                type="text"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="John Doe"
                bind:value={fullName}
                autocomplete="name"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="email">
                Work Email <span class="text-neutral-400">*</span>
              </label>
              <input
                id="email"
                type="email"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="name@company.com"
                bind:value={email}
                autocomplete="email"
                required
              />
            </div>
          </div>

          <!-- Company Name & Size row -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="companyName">
                Company Name <span class="text-neutral-400">*</span>
              </label>
              <input
                id="companyName"
                type="text"
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="Acme Corp"
                bind:value={companyName}
                autocomplete="organization"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-neutral-900 mb-2" for="companySize">
                Company Size
              </label>
              <div class="relative">
                <select
                  id="companySize"
                  bind:value={companySize}
                  class="w-full appearance-none rounded-lg border border-neutral-300 px-3.5 py-3 pr-10 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow {!companySize ? 'text-neutral-400' : ''}"
                >
                  <option value="" disabled>Select size</option>
                  {#each companySizes as size}
                    <option value={size}>{size} employees</option>
                  {/each}
                </select>
                <svg class="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Phone -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="phone">
              Phone Number
            </label>
            <input
              id="phone"
              type="tel"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
              placeholder="+1 (555) 000-0000"
              bind:value={phone}
              autocomplete="tel"
            />
          </div>

          <!-- Message -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="message">
              What are you looking for?
            </label>
            <textarea
              id="message"
              rows="3"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow resize-none"
              placeholder="Tell us about your requirements or what you'd like to explore..."
              bind:value={message}
            ></textarea>
          </div>

          <button
            type="submit"
            disabled={loading}
            class="w-full rounded-lg bg-neutral-900 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
          >
            {loading ? "Submitting..." : "Request Demo"}
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
