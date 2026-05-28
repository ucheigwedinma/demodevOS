<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { api, ApiError, clearTokens } from "$lib/api";
  import { setSessionFingerprint } from "$lib/sessionGuard";
  import { toast } from "$lib/stores/toast.svelte";
  import CookieConsent from "$lib/components/CookieConsent.svelte";


  let step: "credentials" | "otp" = $state("credentials");
  let credential = $state("");
  let password = $state("");
  let showPassword = $state(false);
  let rememberMe = $state(false);
  let loading = $state(false);
  let honeypot = $state("");
  let otpSession = $state("");
  let otpDigits: string[] = $state(["", "", "", "", "", ""]);
  let otpInputs: HTMLInputElement[] = [];
  let resending = $state(false);
  onMount(() => {
    if (localStorage.getItem("access_token") || sessionStorage.getItem("access_token")) {
      goto("/");
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
        remember_me: rememberMe,
      });
      otpSession = res.otp_session;
      step = "otp";
      // Focus first OTP input after transition
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

    // Only allow digits
    if (value && !/^\d$/.test(value)) {
      input.value = otpDigits[index];
      return;
    }

    otpDigits[index] = value;

    // Auto-advance to next input
    if (value && index < 5) {
      otpInputs[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits are filled
    if (otpDigits.every((d) => d !== "")) {
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
    for (let i = 0; i < 6; i++) {
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
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem("access_token", res.access);
      storage.setItem("refresh_token", res.refresh);
      setSessionFingerprint(res.session_id);
      toast.success("Login successful", "Welcome back");
      await goto("/");
    } catch (err) {
      let message = "Invalid verification code.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Verification failed", message);
      // Clear OTP inputs on failure
      otpDigits = ["", "", "", "", "", ""];
      otpInputs[0]?.focus();
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
        remember_me: rememberMe,
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

  async function loginWithGoogle() {
    loading = true;
    try {
      const res = await api.post<{ redirect_url: string }>("/auth/oauth/authorize/", { provider: "google" });
      window.location.href = res.redirect_url;
    } catch (err) {
      let message = "Could not start Google sign-in.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Google sign-in failed", message);
      loading = false;
    }
  }

  async function loginWithMicrosoft() {
    loading = true;
    try {
      const res = await api.post<{ redirect_url: string }>("/auth/oauth/authorize/", { provider: "microsoft" });
      window.location.href = res.redirect_url;
    } catch (err) {
      let message = "Could not start Microsoft sign-in.";
      if (err instanceof ApiError) {
        const detail = (err.fieldErrors as Record<string, unknown>).detail;
        if (typeof detail === "string") message = detail;
      }
      toast.error("Microsoft sign-in failed", message);
      loading = false;
    }
  }
</script>

<svelte:head><title>Sign In | developerOS</title></svelte:head>

<div class="min-h-screen flex flex-col items-center justify-center p-6">
  {#if step === "credentials"}
    <!-- Horizontal Login Card -->
    <div class="w-full max-w-4xl rounded-2xl border border-neutral-800 bg-neutral-900 shadow-sm flex flex-col md:flex-row overflow-hidden">

      <!-- Left Panel — Branding -->
      <div class="md:w-5/12 flex flex-col items-center justify-center p-10 border-b md:border-b-0 md:border-r border-neutral-800">
        <img src="/logo-dark.png" alt="developerOS" class="h-28" />
        <p class="text-xs text-neutral-500 mt-3 tracking-wide">Ground Up, Data Driven!</p>
        <h1 class="mt-6 text-2xl font-bold text-white">Welcome back</h1>
        <p class="mt-1.5 text-sm text-neutral-400 text-center">Please enter your details to log in.</p>

        <!-- OAuth buttons -->
        <div class="mt-6 w-full max-w-[280px] space-y-2.5">
          <button
            type="button"
            onclick={loginWithGoogle}
            disabled={loading}
            class="w-full flex items-center justify-center gap-2.5 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors disabled:opacity-60"
          >
            <svg class="w-4.5 h-4.5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
          <button
            type="button"
            onclick={loginWithMicrosoft}
            disabled={loading}
            class="w-full flex items-center justify-center gap-2.5 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors disabled:opacity-60"
          >
            <svg class="w-4.5 h-4.5" viewBox="0 0 24 24">
              <rect fill="#F25022" x="1" y="1" width="10.5" height="10.5"/>
              <rect fill="#7FBA00" x="12.5" y="1" width="10.5" height="10.5"/>
              <rect fill="#00A4EF" x="1" y="12.5" width="10.5" height="10.5"/>
              <rect fill="#FFB900" x="12.5" y="12.5" width="10.5" height="10.5"/>
            </svg>
            Continue with Microsoft
          </button>
        </div>

        <!-- Sign up link -->
        <p class="mt-6 text-center text-sm text-neutral-400">
          Don't have an account?
          <a href="/signup" class="font-semibold text-white hover:underline">Create an account</a>
        </p>
      </div>

      <!-- Right Panel — Form -->
      <div class="md:w-7/12 p-10 flex flex-col justify-center">
        <form class="space-y-4 max-w-sm mx-auto w-full" action="/login" method="post" onsubmit={handleLogin}>
          <!-- Credential (username or email) -->
          <div>
            <label class="block text-sm font-medium text-neutral-300 mb-1.5" for="credential">
              Username or email
            </label>
            <input
              id="credential"
              type="text"
              class="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3.5 py-2.5 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-shadow"
              placeholder="username or name@company.com"
              bind:value={credential}
              autocomplete="username"
            />
          </div>

          <!-- Password -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-sm font-medium text-neutral-300" for="password">
                Password
              </label>
              <a href="/forgot-password" class="text-xs font-medium text-neutral-500 hover:text-neutral-300 transition-colors">
                Forgot password?
              </a>
            </div>
            <div class="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                class="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3.5 py-2.5 pr-10 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-shadow"
                placeholder="Enter your password"
                bind:value={password}
                autocomplete="current-password"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300 transition-colors"
                onclick={() => (showPassword = !showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {#if showPassword}
                  <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                {:else}
                  <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                {/if}
              </button>
            </div>
          </div>

          <!-- Remember me -->
          <div class="flex items-center gap-2.5">
            <input
              id="remember"
              type="checkbox"
              class="h-4 w-4 rounded border-neutral-600 bg-neutral-800 text-white focus:ring-white"
              bind:checked={rememberMe}
            />
            <label for="remember" class="text-sm text-neutral-400">Remember for 30 days</label>
          </div>

          <!-- Honeypot (hidden from humans) -->
          <input type="text" name="website" bind:value={honeypot} class="absolute opacity-0 -z-10 pointer-events-none" tabindex="-1" autocomplete="off" aria-hidden="true" />

          <!-- Submit -->
          <button
            type="submit"
            disabled={loading}
            class="w-full rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-100 disabled:opacity-60 flex items-center justify-center h-10"
          >
            {#if loading}
              <span class="bouncing-dots dark"><span></span><span></span><span></span></span>
            {:else}
              Log In
            {/if}
          </button>
        </form>
      </div>
    </div>

    <!-- Footer -->
    <div class="mt-8 flex items-center justify-center gap-2 text-xs text-neutral-400">
      <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
      <span class="text-neutral-300">&middot;</span>
      <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
      <span class="text-neutral-300">&middot;</span>
      <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
    </div>
    <p class="mt-3 text-center text-xs text-neutral-400">
      &copy; {new Date().getFullYear()} <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
    </p>
  {:else}
    <!-- OTP Verification -->
    <div class="text-center mb-5">
      <img src="/logo-light.png" alt="developerOS" class="h-28 mx-auto" />
    </div>
    <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm text-center">
      <!-- Lock icon -->
      <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white otp-icon-enter">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
        </svg>
      </div>

      <h1 class="text-2xl font-bold text-neutral-900">Verify your identity</h1>
      <p class="mt-2 text-sm text-neutral-500 leading-relaxed">
        We've sent a 6-digit verification code to<br />your email address.
      </p>

      <!-- OTP Inputs -->
      <div class="mt-8 flex justify-center gap-3" onpaste={handleOtpPaste}>
        {#each otpDigits as digit, i}
          <input
            bind:this={otpInputs[i]}
            type="text"
            inputmode="numeric"
            maxlength="1"
            class="w-12 h-14 text-center text-xl font-semibold text-neutral-900 border-b-2 border-neutral-300 bg-transparent focus:border-neutral-900 focus:outline-none transition-colors otp-input-enter"
            style="animation-delay: {i * 0.06}s;"
            value={digit}
            oninput={(e) => handleOtpInput(i, e)}
            onkeydown={(e) => handleOtpKeydown(i, e)}
          />
        {/each}
      </div>

      <!-- Verify button -->
      <button
        onclick={verifyOtp}
        disabled={loading || otpDigits.some((d) => !d)}
        class="mt-8 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60 flex items-center justify-center h-10"
      >
        {#if loading}
          <span class="bouncing-dots"><span></span><span></span><span></span></span>
        {:else}
          Verify
        {/if}
      </button>

      <!-- Resend -->
      <p class="mt-5 text-sm text-neutral-500">
        Didn't receive the code?
        <button
          onclick={resendCode}
          disabled={resending}
          class="font-semibold text-neutral-900 hover:underline disabled:opacity-60"
        >
          {resending ? "Sending..." : "Resend Code"}
        </button>
      </p>

      <!-- Back -->
      <button
        onclick={backToLogin}
        class="mt-4 inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to login
      </button>
    </div>

    <!-- Footer -->
    <div class="mt-8 flex items-center justify-center gap-2 text-xs text-neutral-400">
      <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
      <span class="text-neutral-300">&middot;</span>
      <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
      <span class="text-neutral-300">&middot;</span>
      <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
    </div>
    <p class="mt-3 text-center text-xs text-neutral-400">
      &copy; {new Date().getFullYear()} <span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.
    </p>
  {/if}

  <CookieConsent inverted />
</div>

<style>
  .otp-icon-enter {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .otp-input-enter {
    opacity: 0;
    animation: fadeSlideUp 0.3s ease-out forwards;
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

  @keyframes fadeSlideUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Bouncing dots loader */
  .bouncing-dots {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .bouncing-dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: white;
    animation: dotBounce 1.4s infinite ease-in-out both;
  }

  .bouncing-dots.dark span {
    background-color: #0a0a0a;
  }

  .bouncing-dots span:nth-child(1) { animation-delay: -0.32s; }
  .bouncing-dots span:nth-child(2) { animation-delay: -0.16s; }
  .bouncing-dots span:nth-child(3) { animation-delay: 0s; }

  @keyframes dotBounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }
</style>
