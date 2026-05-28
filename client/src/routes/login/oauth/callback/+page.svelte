<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import { api, ApiError, clearTokens } from "$lib/api";
  import { setSessionFingerprint } from "$lib/sessionGuard";
  import { toast } from "$lib/stores/toast.svelte";

  type OAuthCallbackResponse =
    | { access: string; refresh: string; session_id: string }
    | { otp_session: string };

  let step = $state<"exchanging" | "otp" | "error">("exchanging");
  let error = $state("");
  let otpSession = $state("");
  let otpDigits: string[] = $state(["", "", "", "", "", ""]);
  let otpInputs: HTMLInputElement[] = [];
  let verifyingOtp = $state(false);

  function saveTokens(access: string, refresh: string, sessionId: string) {
    clearTokens();
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    setSessionFingerprint(sessionId);
  }

  onMount(async () => {
    const code = $page.url.searchParams.get("code");
    const state = $page.url.searchParams.get("state");

    if (!code || !state) {
      error = "Invalid callback parameters. Please try logging in again.";
      step = "error";
      return;
    }

    try {
      const res = await api.post<OAuthCallbackResponse>(
        "/auth/oauth/callback/",
        { code, state },
      );
      if ("otp_session" in res) {
        otpSession = res.otp_session;
        step = "otp";
        setTimeout(() => otpInputs[0]?.focus(), 50);
      } else {
        saveTokens(res.access, res.refresh, res.session_id);
        toast.success("Login successful", "Welcome back");
        await goto("/");
      }
    } catch (err) {
      let message = "OAuth login failed. Please try again.";
      if (err instanceof ApiError) {
        const detail =
          (typeof err.data.detail === "string" ? err.data.detail : undefined) ??
          ((err.fieldErrors as Record<string, unknown>).detail as string | undefined);
        if (typeof detail === "string") message = detail;
      }
      error = message;
      step = "error";
    }
  });

  function handleOtpInput(index: number, event: Event) {
    const input = event.target as HTMLInputElement;
    const value = input.value;

    if (value && !/^\d$/.test(value)) {
      input.value = otpDigits[index];
      return;
    }

    otpDigits[index] = value;

    if (value && index < 5) {
      otpInputs[index + 1]?.focus();
    }

    if (otpDigits.every((digit) => digit !== "")) {
      void verifyOtp();
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
    if (chars.length === 6) {
      void verifyOtp();
    }
  }

  async function verifyOtp() {
    if (verifyingOtp) return;

    const code = otpDigits.join("");
    if (code.length !== 6) {
      toast.error("Invalid code", "Please enter all 6 digits.");
      return;
    }

    verifyingOtp = true;
    try {
      const res = await api.post<{ access: string; refresh: string; session_id: string }>(
        "/auth/verify-otp/",
        { otp_session: otpSession, code },
      );
      saveTokens(res.access, res.refresh, res.session_id);
      toast.success("Login successful", "Welcome back");
      await goto("/");
    } catch (err) {
      let message = "Invalid verification code.";
      if (err instanceof ApiError) {
        const detail =
          (typeof err.data.detail === "string" ? err.data.detail : undefined) ??
          ((err.fieldErrors as Record<string, unknown>).detail as string | undefined);
        if (typeof detail === "string") message = detail;
      }
      toast.error("Verification failed", message);
      otpDigits = ["", "", "", "", "", ""];
      otpInputs[0]?.focus();
    } finally {
      verifyingOtp = false;
    }
  }

  function restartLogin() {
    void goto("/login");
  }
</script>

<div class="min-h-screen flex flex-col items-center justify-center p-6">
  <div class="text-center mb-5">
    <img src="/logo-light.png" alt="developerOS" class="h-28 mx-auto" />
  </div>

  <div class="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-8 shadow-sm text-center">
    {#if step === "exchanging"}
      <div class="flex flex-col items-center gap-4">
        <div class="w-10 h-10 border-2 border-neutral-600 border-t-white rounded-full animate-spin"></div>
        <p class="text-sm text-neutral-400">Completing sign-in...</p>
      </div>
    {:else if step === "otp"}
      <div class="flex flex-col items-center gap-4">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-neutral-800 text-white">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">Verify your sign-in</h1>
        <p class="text-sm text-neutral-400">Enter the 6-digit code sent to your email.</p>
      </div>

      <div class="mt-8 flex justify-center gap-3" onpaste={handleOtpPaste}>
        {#each otpDigits as digit, i}
          <input
            bind:this={otpInputs[i]}
            type="text"
            inputmode="numeric"
            maxlength="1"
            class="w-12 h-14 text-center text-xl font-semibold text-white border-b-2 border-neutral-600 bg-transparent focus:border-white focus:outline-none transition-colors"
            value={digit}
            oninput={(e) => handleOtpInput(i, e)}
            onkeydown={(e) => handleOtpKeydown(i, e)}
          />
        {/each}
      </div>

      <button
        onclick={verifyOtp}
        disabled={verifyingOtp || otpDigits.some((digit) => digit === "")}
        class="mt-8 w-full rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-100 disabled:opacity-60"
      >
        {verifyingOtp ? "Verifying..." : "Verify"}
      </button>

      <button
        onclick={restartLogin}
        class="mt-4 inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to login
      </button>
    {:else if error}
      <div class="flex flex-col items-center gap-4">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 text-red-400">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <p class="text-sm text-red-400">{error}</p>
        <a
          href="/login"
          class="mt-2 inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white transition-colors"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back to login
        </a>
      </div>
    {/if}
  </div>
</div>
