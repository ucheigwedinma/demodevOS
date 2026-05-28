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

<div class="relative min-h-screen px-6 py-6 text-neutral-100">
  <a href="/partner/login" class="absolute left-6 top-6 z-10 inline-flex items-center" aria-label="Partner login home">
    <img src="/logo-dark.png" alt="developerOS" class="h-10 w-auto" />
  </a>

  <div class="mx-auto flex min-h-screen w-full max-w-5xl items-center justify-center">
    <div class="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <section class="hidden rounded-3xl border border-neutral-800 bg-neutral-900 p-10 shadow-2xl lg:block">
        <div class="mb-8 inline-flex items-center gap-2 rounded-full border border-neutral-700 bg-neutral-800 px-4 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-200">
          Password Recovery
        </div>
        <h1 class="text-3xl font-bold text-white">Partner Access Recovery</h1>
        <p class="mt-3 text-sm leading-relaxed text-neutral-300">
          Reset your password for partner portal access. If your email is registered, you will receive a secure recovery link.
        </p>
      </section>

      <section class="rounded-3xl border border-neutral-200 bg-white p-8 shadow-2xl">
        {#if sent}
          <div class="text-center">
            <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white">
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-neutral-900">Check your email</h2>
            <p class="mt-2 text-sm text-neutral-500">
              If <span class="font-medium text-neutral-700">{email}</span> is registered, a reset link has been sent.
            </p>
            <a
              href="/partner/login"
              class="mt-7 inline-flex items-center gap-1.5 text-sm font-medium text-neutral-700 hover:text-neutral-900"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
              </svg>
              Back to Partner Login
            </a>
          </div>
        {:else}
          <h2 class="mt-2 text-center text-2xl font-bold text-neutral-900">Forgot Password</h2>
          <p class="mt-1 text-center text-sm text-neutral-500">Enter your email to receive a reset link.</p>

          <form class="mt-6 space-y-4" onsubmit={handleSubmit}>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-neutral-700" for="email">Email address</label>
              <input
                id="email"
                type="email"
                bind:value={email}
                autocomplete="email"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                placeholder="name@company.com"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send Reset Link"}
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
