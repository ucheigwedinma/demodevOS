<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";

  let loading = $state(true);
  let success = $state(false);
  let errorMessage = $state("");

  let token = $derived($page.url.searchParams.get("token") ?? "");

  $effect(() => {
    if (!token) {
      loading = false;
      errorMessage = "No verification token found.";
      return;
    }

    api
      .post("/auth/verify-email/", { token })
      .then(() => {
        success = true;
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          const errors = err.fieldErrors as Record<string, string | string[]>;
          const tokenErr = errors.token;
          if (tokenErr) {
            errorMessage = Array.isArray(tokenErr) ? tokenErr[0] : tokenErr;
          } else {
            errorMessage = "This verification link is invalid or has expired.";
          }
        } else {
          errorMessage = "Something went wrong. Please try again.";
        }
      })
      .finally(() => {
        loading = false;
      });
  });
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
    {#if loading}
      <!-- Loading State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-200 animate-pulse">
          <svg class="w-7 h-7 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900">Verifying your email...</h1>
        <p class="mt-3 text-sm text-neutral-500">Please wait while we verify your email address.</p>
      </div>
    {:else if success}
      <!-- Success State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-900 text-white success-icon">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path class="check-path" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Email verified!</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          Your email has been successfully verified.<br />You can now sign in to your account.
        </p>
        <div class="mt-8 fade-in" style="animation-delay: 0.5s;">
          <button
            onclick={() => goto("/login")}
            class="w-full max-w-xs mx-auto rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
          >
            Proceed to login
          </button>
        </div>
      </div>
    {:else}
      <!-- Error State -->
      <div class="w-full max-w-md text-center">
        <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-100 error-icon">
          <svg class="w-8 h-8 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900 fade-in" style="animation-delay: 0.2s;">Verification failed</h1>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed fade-in" style="animation-delay: 0.35s;">
          {errorMessage}
        </p>
        <div class="mt-8 flex flex-col items-center gap-3 fade-in" style="animation-delay: 0.5s;">
          <a
            href="/signup"
            class="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-900 hover:underline"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Back to Sign Up
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

  .error-icon {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
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
