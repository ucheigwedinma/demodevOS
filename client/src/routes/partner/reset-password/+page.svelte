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
          const value = errors[firstKey];
          message = Array.isArray(value) ? value[0] : (typeof value === "string" ? value : message);
        }
      }
      toast.error("Reset failed", message);
    } finally {
      loading = false;
    }
  }
</script>

<div class="relative min-h-screen px-6 py-6 text-neutral-100">
  <a href="/partner/login" class="absolute left-6 top-6 z-10 inline-flex items-center" aria-label="Partner login home">
    <img src="/logo-dark.png" alt="developerOS" class="h-10 w-auto" />
  </a>

  <div class="mx-auto flex min-h-screen w-full max-w-5xl items-center justify-center">
    <div class="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <section class="hidden rounded-3xl border border-neutral-800 bg-neutral-900 p-10 shadow-2xl lg:block">
        <div class="mb-8 inline-flex items-center gap-2 rounded-full border border-neutral-700 bg-neutral-800 px-4 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-200">
          Password Reset
        </div>
        <h1 class="text-3xl font-bold text-white">Secure Partner Access</h1>
        <p class="mt-3 text-sm leading-relaxed text-neutral-300">
          Set a new password for your partner account. Use a strong password to protect sensitive project and financial data.
        </p>
      </section>

      <section class="rounded-3xl border border-neutral-200 bg-white p-8 shadow-2xl">
        {#if success}
          <div class="text-center">
            <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white">
              <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-neutral-900">Password reset successful</h2>
            <p class="mt-2 text-sm text-neutral-500">You can now sign in to the partner portal with your new password.</p>
            <button
              onclick={() => goto("/partner/login")}
              class="mt-7 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
            >
              Back to Partner Login
            </button>
          </div>
        {:else}
          <h2 class="mt-2 text-center text-2xl font-bold text-neutral-900">Reset Password</h2>
          <p class="mt-1 text-center text-sm text-neutral-500">Choose a secure password for your partner account.</p>

          <form class="mt-6 space-y-4" onsubmit={handleSubmit}>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-neutral-700" for="password">New password</label>
              <input
                id="password"
                type="password"
                bind:value={password}
                autocomplete="new-password"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-neutral-700" for="confirmPassword">Confirm password</label>
              <input
                id="confirmPassword"
                type="password"
                bind:value={confirmPassword}
                autocomplete="new-password"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                placeholder="Re-type your password"
              />
            </div>

            <div class="space-y-1.5 pt-1 text-xs">
              <p class={hasMinLength ? "text-neutral-700" : "text-neutral-400"}>Minimum 8 characters</p>
              <p class={hasSpecialChar ? "text-neutral-700" : "text-neutral-400"}>At least one special character</p>
              <p class={passwordsMatch ? "text-neutral-700" : "text-neutral-400"}>Passwords match</p>
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Resetting..." : "Reset Password"}
            </button>
          </form>

          <p class="mt-6 text-center text-xs text-neutral-500">
            <a href="/partner/login" class="font-medium text-neutral-700 hover:text-neutral-900">Back to Partner Login</a>
          </p>
        {/if}
      </section>
    </div>
  </div>

  <p class="mt-3 text-center text-xs text-neutral-500">
    &copy; {new Date().getFullYear()} <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
  </p>
</div>
