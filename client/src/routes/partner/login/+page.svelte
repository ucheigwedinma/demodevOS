<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { ApiError, api, clearTokens } from "$lib/api";
  import { setSessionFingerprint } from "$lib/sessionGuard";
  import { toast } from "$lib/stores/toast.svelte";
  import CookieConsent from "$lib/components/CookieConsent.svelte";

  let step: "credentials" | "otp" = $state("credentials");
  let credential = $state("");
  let password = $state("");
  let showPassword = $state(false);
  let loading = $state(false);
  let honeypot = $state("");
  let otpSession = $state("");
  let otpDigits: string[] = $state(["", "", "", "", "", ""]);
  let otpInputs: HTMLInputElement[] = [];
  let resending = $state(false);

  onMount(() => {
    if (localStorage.getItem("access_token")) {
      goto("/partner");
    }
  });

  async function handleLogin(event: SubmitEvent) {
    event.preventDefault();
    if (!credential || !password) {
      toast.error("Login failed", "Username/email and password are required.");
      return;
    }

    loading = true;
    try {
      const res = await api.post<{ otp_session: string }>("/auth/login/", {
        credential,
        password,
        hp_field: honeypot,
      });
      otpSession = res.otp_session;
      step = "otp";
      setTimeout(() => otpInputs[0]?.focus(), 50);
    } catch (err) {
      let message = "Invalid credentials.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Login failed", message);
    } finally {
      loading = false;
    }
  }

  function handleOtpInput(index: number, event: Event) {
    const input = event.target as HTMLInputElement;
    const value = input.value;

    if (value && !/^\d$/.test(value)) {
      input.value = otpDigits[index];
      return;
    }

    otpDigits[index] = value;
    if (value && index < 5) otpInputs[index + 1]?.focus();
    if (otpDigits.every((digit) => digit !== "")) {
      verifyOtp();
    }
  }

  function handleOtpKeydown(index: number, event: KeyboardEvent) {
    if (event.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpInputs[index - 1]?.focus();
    }
  }

  function handleOtpPaste(event: ClipboardEvent) {
    event.preventDefault();
    const pasted = event.clipboardData?.getData("text")?.replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;

    const chars = pasted.split("");
    for (let i = 0; i < 6; i += 1) {
      otpDigits[i] = chars[i] || "";
    }
    const focusIndex = Math.min(chars.length, 5);
    otpInputs[focusIndex]?.focus();
    if (chars.length === 6) verifyOtp();
  }

  async function verifyOtp() {
    const code = otpDigits.join("");
    if (code.length !== 6) {
      toast.error("Invalid code", "Please enter all 6 digits.");
      return;
    }

    loading = true;
    try {
      const res = await api.post<{ access: string; refresh: string; session_id: string }>("/auth/verify-otp/", {
        otp_session: otpSession,
        code,
      });
      clearTokens();
      localStorage.setItem("access_token", res.access);
      localStorage.setItem("refresh_token", res.refresh);
      setSessionFingerprint(res.session_id);
      toast.success("Login successful", "Redirecting to partner portal...");
      await goto("/partner");
    } catch (err) {
      let message = "Invalid verification code.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Verification failed", message);
      otpDigits = ["", "", "", "", "", ""];
      otpInputs[0]?.focus();
    } finally {
      loading = false;
    }
  }

  async function resendCode() {
    resending = true;
    try {
      const res = await api.post<{ otp_session: string }>("/auth/login/", {
        credential,
        password,
        hp_field: honeypot,
      });
      otpSession = res.otp_session;
      otpDigits = ["", "", "", "", "", ""];
      otpInputs[0]?.focus();
      toast.success("Code resent", "A new verification code has been sent.");
    } catch {
      toast.error("Resend failed", "Please try logging in again.");
      step = "credentials";
    } finally {
      resending = false;
    }
  }

  function backToLogin() {
    step = "credentials";
    otpDigits = ["", "", "", "", "", ""];
    otpSession = "";
  }
</script>

<div class="relative flex min-h-screen flex-col px-6 py-6 text-neutral-100">
  <a href="/partner/login" class="absolute left-6 top-6 z-10 inline-flex items-center" aria-label="Partner login home">
    <img src="/logo-dark.png" alt="developerOS" class="h-11 w-auto" />
  </a>

  <div class="mx-auto flex w-full max-w-5xl flex-1 items-center justify-center">
    <div class="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
    <section class="hidden rounded-3xl border border-neutral-800 bg-neutral-900 p-10 shadow-2xl lg:block">
      <div class="mb-8 inline-flex items-center gap-2 rounded-full border border-neutral-700 bg-neutral-800 px-4 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-200">
        External Access
      </div>
      <h1 class="text-3xl font-bold text-white">Partner-Agnostic Portal</h1>
      <p class="mt-3 text-sm leading-relaxed text-neutral-300">
        Secure access for clients, contractors, and investors with role-scoped visibility and immutable governance controls.
      </p>

      <div class="mt-8 space-y-4">
        <div class="rounded-xl border border-neutral-700 bg-neutral-800/80 p-4">
          <p class="text-sm font-semibold text-white">Contract-scoped data partitioning</p>
          <p class="mt-1 text-xs text-neutral-300">Each user sees only assigned project, contract, SPV, and investment data.</p>
        </div>
        <div class="rounded-xl border border-neutral-700 bg-neutral-800/80 p-4">
          <p class="text-sm font-semibold text-white">Approval and legal traceability</p>
          <p class="mt-1 text-xs text-neutral-300">Session access is gated by accepted legal terms and audit logging.</p>
        </div>
      </div>
    </section>

    {#if step === "credentials"}
      <section class="rounded-3xl border border-neutral-200 bg-white p-8 shadow-2xl">
        <h2 class="mt-2 text-center text-2xl font-bold text-neutral-900">Partner Login</h2>
        <p class="mt-1 text-center text-sm text-neutral-500">Enter your credentials to continue.</p>

        <form class="mt-6 space-y-4" onsubmit={handleLogin}>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-neutral-700" for="credential">Username or email</label>
            <input
              id="credential"
              type="text"
              bind:value={credential}
              autocomplete="username"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="username or name@company.com"
            />
          </div>

          <div>
            <div class="mb-1.5 flex items-center justify-between">
              <label class="block text-sm font-medium text-neutral-700" for="password">Password</label>
              <a href="/partner/forgot-password" class="text-xs font-medium text-neutral-500 hover:text-neutral-700">Forgot password?</a>
            </div>
            <div class="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                bind:value={password}
                autocomplete="current-password"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 pr-10 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                placeholder="Enter your password"
              />
              <button
                type="button"
                onclick={() => (showPassword = !showPassword)}
                class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {#if showPassword}
                  <svg class="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                {:else}
                  <svg class="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                {/if}
              </button>
            </div>
          </div>

          <!-- Honeypot (hidden from humans) -->
          <input type="text" name="website" bind:value={honeypot} class="absolute opacity-0 -z-10 pointer-events-none" tabindex="-1" autocomplete="off" aria-hidden="true" />

          <button
            type="submit"
            disabled={loading}
            class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
          >
            {loading ? "Logging in..." : "Log In"}
          </button>
        </form>

        <p class="mt-5 text-center text-xs text-neutral-500">
          Need access? Contact your project administrator.
        </p>
      </section>
    {:else}
      <section class="rounded-3xl border border-neutral-200 bg-white p-8 shadow-2xl">
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
        </div>

        <h2 class="text-center text-2xl font-bold text-neutral-900">Verify your identity</h2>
        <p class="mt-2 text-center text-sm text-neutral-500">Enter the 6-digit code sent to your email.</p>

        <div class="mt-8 flex justify-center gap-3" onpaste={handleOtpPaste}>
          {#each otpDigits as digit, i}
            <input
              bind:this={otpInputs[i]}
              type="text"
              inputmode="numeric"
              maxlength="1"
              class="h-14 w-12 border-b-2 border-neutral-300 bg-transparent text-center text-xl font-semibold text-neutral-900 focus:border-neutral-900 focus:outline-none"
              value={digit}
              oninput={(e) => handleOtpInput(i, e)}
              onkeydown={(e) => handleOtpKeydown(i, e)}
            />
          {/each}
        </div>

        <button
          onclick={verifyOtp}
          disabled={loading || otpDigits.some((digit) => !digit)}
          class="mt-8 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
        >
          {loading ? "Verifying..." : "Verify"}
        </button>

        <p class="mt-5 text-center text-sm text-neutral-500">
          Didn't receive the code?
          <button onclick={resendCode} disabled={resending} class="font-semibold text-neutral-900 hover:underline disabled:opacity-60">
            {resending ? "Sending..." : "Resend code"}
          </button>
        </p>

        <button
          onclick={backToLogin}
          class="mt-4 inline-flex items-center gap-1.5 text-sm text-neutral-500 transition-colors hover:text-neutral-700"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back to login
        </button>
      </section>
    {/if}
    </div>
  </div>

  <p class="mt-3 text-center text-xs text-white">
    &copy; {new Date().getFullYear()} <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
  </p>

  <CookieConsent />
</div>
