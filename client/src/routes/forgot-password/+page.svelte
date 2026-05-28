<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  let email = $state("");
  let loading = $state(false);
  let sent = $state(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!email) {
      toast.error("Missing email", "Please enter your email address.");
      return;
    }

    loading = true;
    try {
      await api.post("/auth/forgot-password/", { email });
      sent = true;
    } catch (err) {
      let message = "Something went wrong. Please try again.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Request failed", message);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Forgot Password | developerOS</title></svelte:head>

<div class="min-h-screen flex flex-col">
  <!-- Top Nav -->
  <div class="bg-white border-b border-neutral-200">
    <div class="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
      <a href="/help">
        <img src="/logo-light.png" alt="developerOS" class="h-10" />
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
  <div class="flex-1 bg-neutral-50 flex items-center justify-center px-6">
    {#if sent}
      <!-- Success State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-900 text-white success-icon">
          <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path class="check-path" stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Check your email</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          We've sent a password reset link to<br />
          <span class="font-medium text-neutral-700">{email}</span>
        </p>
        <div class="mt-8 fade-in" style="animation-delay: 0.5s;">
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
      <div class="w-full max-w-md">
        <!-- Icon -->
        <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <svg class="w-6 h-6 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
          </svg>
        </div>

        <h1 class="text-3xl font-bold text-neutral-900">Forgot Password</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed max-w-sm">
          No worries, it happens. Enter your email address below and we'll send you a secure link to reset your password.
        </p>

        <form class="mt-8" onsubmit={handleSubmit}>
          <label class="block text-sm font-semibold text-neutral-900 mb-2" for="email">
            Email Address
          </label>
          <div class="relative">
            <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
            </svg>
            <input
              id="email"
              type="email"
              class="w-full rounded-lg border border-neutral-300 pl-11 pr-4 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
              placeholder="e.g. name@company.com"
              bind:value={email}
              autocomplete="email"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            class="mt-5 w-full rounded-lg bg-neutral-900 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
          >
            {loading ? "Sending..." : "Send Reset Link"}
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
      Having trouble? <a href="/contact-support" class="text-neutral-500 hover:text-neutral-700 underline transition-colors">Contact Support</a>
    </p>
  </div>
</div>

<style>
  .success-icon {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
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
