<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  let credential = $state("");
  let password = $state("");
  let otp = $state("");
  let loading = $state(false);
  let step = $state<"credentials" | "otp">("credentials");
  let otpSession = $state("");

  async function handleLogin() {
    if (!credential || !password) return;
    loading = true;
    try {
      const res = await api.post<{ otp_session: string }>("/auth/login/", {
        credential,
        password,
        remember_me: true,
      });
      otpSession = res.otp_session;
      step = "otp";
      toast.info("Verification code sent", "Check your email for the 6-digit code.");
    } catch (e) {
      if (e instanceof ApiError) {
        toast.error("Login failed", e.data?.detail as string ?? "Invalid credentials");
      }
    } finally {
      loading = false;
    }
  }

  async function handleOtp() {
    if (!otp) return;
    loading = true;
    try {
      const res = await api.post<{ access: string; refresh: string }>("/auth/verify-otp/", {
        otp_session: otpSession,
        code: otp,
      });
      localStorage.setItem("access_token", res.access);
      localStorage.setItem("refresh_token", res.refresh);
      toast.success("Login successful", "Welcome back");
      window.location.href = "/";
    } catch (e) {
      if (e instanceof ApiError) {
        const detail = e.data?.detail;
        const msg = Array.isArray(detail) ? detail[0] : typeof detail === "string" ? detail : "Invalid code";
        toast.error("Verification failed", msg);
      }
    } finally {
      loading = false;
    }
  }
</script>

<div class="min-h-screen bg-black flex items-center justify-center p-4">
  <div class="w-full max-w-sm">
    <!-- Brand -->
    <div class="text-center mb-8">
      <h1 class="text-2xl">
        <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
      </h1>
      <p class="text-sm text-neutral-500 mt-1">Command Center</p>
    </div>

    <!-- Form -->
    <div class="bg-neutral-900 rounded-2xl shadow-sm border border-neutral-800 p-6">
      {#if step === "credentials"}
        <form onsubmit={(e) => { e.preventDefault(); handleLogin(); }} class="space-y-4">
          <div>
            <label for="credential" class="block text-sm font-medium text-neutral-300 mb-1">Email</label>
            <input
              id="credential"
              type="email"
              bind:value={credential}
              class="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent"
              placeholder="admin@developeros.pro"
              required
            />
          </div>
          <div>
            <label for="password" class="block text-sm font-medium text-neutral-300 mb-1">Password</label>
            <input
              id="password"
              type="password"
              bind:value={password}
              class="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent"
              placeholder="Enter your password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            class="w-full py-2.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-neutral-200 disabled:opacity-50 transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      {:else}
        <form onsubmit={(e) => { e.preventDefault(); handleOtp(); }} class="space-y-4">
          <p class="text-sm text-neutral-400">Enter the verification code sent to your email.</p>
          <div>
            <label for="otp" class="block text-sm font-medium text-neutral-300 mb-1">Verification Code</label>
            <input
              id="otp"
              type="text"
              bind:value={otp}
              class="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-sm text-white text-center tracking-widest placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent"
              placeholder="000000"
              maxlength="6"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            class="w-full py-2.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-neutral-200 disabled:opacity-50 transition-colors"
          >
            {loading ? "Verifying..." : "Verify"}
          </button>
          <button
            type="button"
            onclick={() => { step = "credentials"; otp = ""; }}
            class="w-full py-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
          >
            Back to login
          </button>
        </form>
      {/if}
    </div>
  </div>
</div>
