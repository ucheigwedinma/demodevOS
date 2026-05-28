<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  let password = $state("");
  let confirmPassword = $state("");
  let loading = $state(false);
  let success = $state(false);

  let token = $derived($page.url.searchParams.get("token") ?? "");

  let hasMinLength = $derived(password.length >= 8);
  let hasSpecialChar = $derived(/[^a-zA-Z0-9]/.test(password));
  let passwordsMatch = $derived(password.length > 0 && password === confirmPassword);

  let canSubmit = $derived(hasMinLength && hasSpecialChar && passwordsMatch && !loading);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();

    if (!token) {
      toast.error("Invalid link", "This reset link is invalid or has expired.");
      return;
    }

    loading = true;
    try {
      await api.post("/auth/reset-password/", { token, password });
      success = true;
    } catch (err) {
      let message = "Something went wrong. Please try again.";
      if (err instanceof ApiError) {
        const errors = err.fieldErrors as Record<string, string | string[]>;
        const firstKey = Object.keys(errors)[0];
        if (firstKey) {
          const val = errors[firstKey];
          message = Array.isArray(val) ? val[0] : (typeof val === "string" ? val : message);
        }
      }
      toast.error("Reset failed", message);
    } finally {
      loading = false;
    }
  }
</script>

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
    {#if success}
      <!-- Success State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-900 text-white success-icon">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path class="check-path" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Password reset!</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          Your password has been successfully updated.<br />You can now sign in with your new password.
        </p>
        <div class="mt-8 fade-in" style="animation-delay: 0.5s;">
          <button
            onclick={() => goto("/login")}
            class="w-full max-w-xs mx-auto rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    {:else}
      <!-- Reset Form Card -->
      <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-neutral-900">Reset Password</h1>
          <p class="mt-2 text-sm text-neutral-500">Choose a secure password to protect your account.</p>
        </div>

        <form onsubmit={handleSubmit} class="space-y-5">
          <!-- New Password -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="password">
              New Password
            </label>
            <div class="relative">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
              </svg>
              <input
                id="password"
                type="password"
                class="w-full rounded-lg border border-neutral-300 pl-11 pr-4 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="At least 8 characters"
                bind:value={password}
                autocomplete="new-password"
              />
            </div>
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm font-semibold text-neutral-900 mb-2" for="confirmPassword">
              Confirm Password
            </label>
            <div class="relative">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
              <input
                id="confirmPassword"
                type="password"
                class="w-full rounded-lg border border-neutral-300 pl-11 pr-4 py-3 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                placeholder="Re-type your password"
                bind:value={confirmPassword}
                autocomplete="new-password"
              />
            </div>
          </div>

          <!-- Requirements -->
          <div class="space-y-2 pt-1">
            <div class="flex items-center gap-2">
              <svg
                class="w-4 h-4 transition-colors {hasMinLength ? 'text-neutral-900' : 'text-neutral-300'}"
                fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span class="text-xs transition-colors {hasMinLength ? 'text-neutral-700' : 'text-neutral-400'}">Minimum 8 characters</span>
            </div>
            <div class="flex items-center gap-2">
              <svg
                class="w-4 h-4 transition-colors {hasSpecialChar ? 'text-neutral-900' : 'text-neutral-300'}"
                fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span class="text-xs transition-colors {hasSpecialChar ? 'text-neutral-700' : 'text-neutral-400'}">At least one special character</span>
            </div>
            <div class="flex items-center gap-2">
              <svg
                class="w-4 h-4 transition-colors {passwordsMatch ? 'text-neutral-900' : 'text-neutral-300'}"
                fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span class="text-xs transition-colors {passwordsMatch ? 'text-neutral-700' : 'text-neutral-400'}">Passwords match</span>
            </div>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            disabled={!canSubmit}
            class="w-full rounded-lg bg-neutral-900 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Resetting..." : "Reset Password"}
          </button>
        </form>

        <!-- Divider -->
        <div class="mt-6 border-t border-neutral-200"></div>

        <!-- Back to Sign In -->
        <div class="mt-5 text-center">
          <a
            href="/login"
            class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Back to Sign In
          </a>
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="bg-neutral-50 border-t border-neutral-200 px-6 py-5">
    <div class="max-w-5xl mx-auto flex items-center justify-between">
      <p class="text-xs text-neutral-400">
        <span class="inline-flex items-center gap-1.5">&copy; {new Date().getFullYear()} <img src="/logo-light.png" alt="developerOS" class="h-5 inline" />. All rights reserved.</span>
      </p>
      <div class="flex gap-5 text-xs text-neutral-400">
        <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
        <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
        <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
      </div>
    </div>
  </div>
</div>

<style>
  .success-icon {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .check-path {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawCheck 0.4s ease-out 0.35s forwards;
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
