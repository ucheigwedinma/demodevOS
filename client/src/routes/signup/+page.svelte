<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  let fullName = $state("");
  let email = $state("");
  let orgName = $state("");
  let password = $state("");
  let confirmPassword = $state("");
  let showPassword = $state(false);
  let agreedToTerms = $state(false);
  let loading = $state(false);
  let honeypot = $state("");
  let success = $state(false);
  let passwordsMatch = $derived(password.length > 0 && password === confirmPassword);

  // Password policy checks (mirrors backend AUTH_PASSWORD_VALIDATORS)
  let pwHasLength = $derived(password.length >= 10);
  let pwHasUpper = $derived(/[A-Z]/.test(password));
  let pwHasLower = $derived(/[a-z]/.test(password));
  let pwHasSpecial = $derived(/[^A-Za-z0-9]/.test(password));
  let pwAllRulesPass = $derived(pwHasLength && pwHasUpper && pwHasLower && pwHasSpecial);

  // Org name validation
  let orgNameChecking = $state(false);
  let orgNameAvailable = $state<boolean | null>(null);
  let orgNameError = $state("");
  let orgNameMatchType = $state<"exact" | "similar" | "none" | null>(null);
  let orgSuggestions = $state<{ id: number; name: string }[]>([]);
  let domainMatches = $state<{ id: number; name: string }[]>([]);
  let userConfirmedUnique = $state(false);
  let orgCheckTimer: ReturnType<typeof setTimeout>;

  interface CheckCompanyResponse {
    exists: boolean;
    match_type: "exact" | "similar" | "none";
    message: string;
    suggestions: { id: number; name: string }[];
    domain_matches: { id: number; name: string }[];
  }

  function checkOrgName(value: string) {
    clearTimeout(orgCheckTimer);
    const trimmed = value.trim();
    if (!trimmed) {
      orgNameAvailable = null;
      orgNameError = "";
      orgNameMatchType = null;
      orgSuggestions = [];
      domainMatches = [];
      userConfirmedUnique = false;
      orgNameChecking = false;
      return;
    }
    orgNameChecking = true;
    orgNameAvailable = null;
    orgNameError = "";
    orgNameMatchType = null;
    orgSuggestions = [];
    domainMatches = [];
    userConfirmedUnique = false;
    orgCheckTimer = setTimeout(async () => {
      try {
        const res = await api.post<CheckCompanyResponse>("/auth/check-company-public/", {
          name: trimmed,
          email: email.trim() || undefined,
        });
        orgNameMatchType = res.match_type;
        orgSuggestions = res.suggestions ?? [];
        domainMatches = res.domain_matches ?? [];

        if (res.match_type === "exact") {
          orgNameAvailable = false;
          orgNameError = res.message;
        } else if (res.match_type === "similar") {
          orgNameAvailable = null;
          orgNameError = "";
        } else {
          orgNameAvailable = true;
          orgNameError = "";
        }
      } catch {
        orgNameAvailable = null;
        orgNameError = "";
      } finally {
        orgNameChecking = false;
      }
    }, 400);
  }

  function confirmOrgUnique() {
    userConfirmedUnique = true;
    orgNameAvailable = true;
    orgNameMatchType = "none";
  }

  // Invitation support
  let invitationToken = $derived($page.url.searchParams.get("invitation") ?? "");
  let invitationOrg = $state("");
  let invitationEmail = $state("");
  let invitationLoading = $state(false);

  let orgNameValid = $derived(
    !invitationToken
      ? orgName.trim().length > 0 && (orgNameAvailable === true || userConfirmedUnique)
      : true
  );
  let canSubmit = $derived(!loading && agreedToTerms && passwordsMatch && pwAllRulesPass && orgNameValid);

  $effect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem("access_token")) {
      goto("/");
    }
  });

  // Validate invitation token on load
  $effect(() => {
    if (!invitationToken) return;
    invitationLoading = true;
    api
      .post<{ email: string; organization_name: string }>("/auth/validate-invitation/", {
        token: invitationToken,
      })
      .then((res) => {
        invitationOrg = res.organization_name;
        invitationEmail = res.email;
        email = res.email;
      })
      .catch(() => {
        toast.error("Invalid invitation", "This invitation link is invalid or has expired.");
      })
      .finally(() => {
        invitationLoading = false;
      });
  });

  async function signup(event: SubmitEvent) {
    event.preventDefault();

    if (!fullName || !email || !password || !confirmPassword || (!invitationToken && !orgName.trim())) {
      toast.error("Missing fields", "Please fill in all fields.");
      return;
    }

    if (!pwAllRulesPass) {
      toast.error("Weak password", "Password does not meet all requirements.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Password mismatch", "Password and confirm password must match.");
      return;
    }

    if (!agreedToTerms) {
      toast.error("Terms required", "Please agree to the Terms of Service and Privacy Policy.");
      return;
    }

    loading = true;
    try {
      await api.post("/auth/register/", {
        full_name: fullName,
        email,
        password,
        org_name: invitationToken ? undefined : orgName.trim(),
        invitation_token: invitationToken || undefined,
        hp_field: honeypot,
      });
      success = true;
    } catch (err) {
      if (err instanceof ApiError) {
        const errors = err.fieldErrors as Record<string, string | string[]>;
        const firstKey = Object.keys(errors)[0];
        if (firstKey) {
          const val = errors[firstKey];
          const message = Array.isArray(val) ? val[0] : val;
          toast.error("Signup failed", typeof message === "string" ? message : "Please try again.");
        } else {
          toast.error("Signup failed", "Please try again.");
        }
      } else {
        toast.error("Signup failed", "Something went wrong. Please try again.");
      }
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Sign Up | developerOS</title></svelte:head>

{#if success}
  <!-- Success Screen -->
  <div class="min-h-screen flex flex-col items-center justify-center p-6">
    <div class="w-full max-w-md text-center">
      <!-- Animated checkmark -->
      <div class="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-neutral-800 text-white success-check">
        <svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
          <path class="check-path" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </div>

      <h1 class="text-2xl font-bold text-neutral-800 success-fade-in" style="animation-delay: 0.3s;">
        Welcome aboard!
      </h1>
      <p class="mt-3 text-sm text-neutral-500 leading-relaxed success-fade-in" style="animation-delay: 0.45s;">
        {#if invitationToken}
          Your account has been created and verified.<br />
          You can now sign in to join <span class="font-medium text-neutral-700">{invitationOrg}</span>.
        {:else}
          A verification link has been sent to<br />
          <span class="font-medium text-neutral-700">{email}</span>.<br />
          Please click it to activate your account.
        {/if}
      </p>

      {#if invitationToken}
        <div class="mt-8 border-t border-neutral-200 pt-6 success-fade-in" style="animation-delay: 0.6s;">
          <button
            onclick={() => goto("/login")}
            class="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
          >
            Proceed to login
          </button>
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="fixed bottom-0 left-0 right-0 border-t border-neutral-200 bg-white/80 backdrop-blur-sm px-6 py-4 flex items-center justify-between text-xs text-neutral-400">
      <p>&copy; {new Date().getFullYear()} <span class="font-normal text-neutral-800">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.</p>
      <div class="flex gap-4">
        <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
        <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
        <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
      </div>
    </div>
  </div>
{:else}
  <!-- Signup Form -->
  <div class="min-h-screen flex flex-col items-center justify-center p-6">
    <!-- Horizontal Signup Card -->
    <div class="w-full max-w-5xl rounded-2xl overflow-hidden shadow-sm flex flex-col md:flex-row">

      <!-- Left Panel — Dark Branding -->
      <div class="relative md:w-5/12 overflow-hidden bg-neutral-800 flex flex-col items-center justify-center p-10">
        <div class="dot-grid"></div>
        <div class="absolute inset-0 bg-linear-to-br from-neutral-800/80 via-neutral-800/60 to-neutral-950/90"></div>
        <div class="relative z-10 flex flex-col items-center text-center">
          <img src="/logo-dark.png" alt="developerOS" class="h-28" />
          <p class="text-xs text-neutral-500 mt-3 tracking-wide">Ground Up, Data Driven!</p>

          <h1 class="mt-8 text-2xl font-bold text-white">
            {invitationOrg ? `Join ${invitationOrg}` : "Create an account"}
          </h1>
          {#if invitationOrg}
            <p class="mt-2 text-sm text-neutral-400">You've been invited to join <span class="font-medium text-neutral-300">{invitationOrg}</span>.</p>
          {:else}
            <p class="mt-1.5 text-sm text-neutral-400">Start building with us today.</p>
          {/if}

          <!-- Login link -->
          <p class="mt-8 text-center text-sm text-neutral-400">
            Already have an account?
            <a href="/login" class="font-semibold text-white hover:underline">Log In</a>
          </p>
        </div>
      </div>

      <!-- Right Panel — White Form -->
      <div class="md:w-7/12 border border-neutral-200 bg-white p-10 flex flex-col justify-center rounded-b-2xl md:rounded-bl-none md:rounded-r-2xl">
        <form class="space-y-4 max-w-sm mx-auto w-full" onsubmit={signup}>
          <!-- Full Name -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="fullName">
              Full Name
            </label>
            <input
              id="fullName"
              type="text"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              placeholder="Enter your full name"
              bind:value={fullName}
              autocomplete="name"
            />
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="email">
              Email address
            </label>
            <input
              id="email"
              type="email"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow {invitationEmail ? 'bg-neutral-50 text-neutral-500' : ''}"
              placeholder="you@example.com"
              bind:value={email}
              readonly={!!invitationEmail}
              autocomplete="email"
            />
          </div>

          <!-- Organization Name (hidden for invited users) -->
          {#if !invitationToken}
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="orgName">
                Organization Name
              </label>
              <div class="relative">
                <input
                  id="orgName"
                  type="text"
                  class="w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-shadow {orgNameError ? 'border-red-300 focus:ring-red-500' : orgNameAvailable ? 'border-neutral-300 focus:ring-neutral-800' : 'border-neutral-300 focus:ring-neutral-800'}"
                  placeholder="Your company or organization"
                  bind:value={orgName}
                  oninput={() => checkOrgName(orgName)}
                  autocomplete="organization"
                />
                {#if orgNameChecking}
                  <div class="absolute right-3 top-1/2 -translate-y-1/2">
                    <div class="w-4 h-4 border-2 border-neutral-200 border-t-neutral-500 rounded-full animate-spin"></div>
                  </div>
                {:else if orgNameAvailable === true}
                  <div class="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-500">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                {:else if orgNameAvailable === false}
                  <div class="absolute right-3 top-1/2 -translate-y-1/2 text-red-500">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                {/if}
              </div>
              {#if orgNameError}
                <p class="mt-1.5 text-xs text-red-500">{orgNameError}</p>
              {:else if orgNameAvailable === true && !orgNameChecking}
                <p class="mt-1.5 text-xs text-emerald-600">Organization name is available.</p>
              {/if}

              <!-- Suggestion panel for similar matches -->
              {#if orgNameMatchType === "similar" && !userConfirmedUnique && (orgSuggestions.length > 0 || domainMatches.length > 0)}
                <div class="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                  {#if orgSuggestions.length > 0}
                    <p class="text-xs font-medium text-amber-800 mb-2">Did you mean one of these?</p>
                    <div class="flex flex-wrap gap-1.5 mb-2">
                      {#each orgSuggestions as suggestion}
                        <span class="inline-flex items-center rounded-md bg-white border border-amber-200 px-2.5 py-1 text-xs font-medium text-neutral-700">
                          {suggestion.name}
                        </span>
                      {/each}
                    </div>
                    <p class="text-xs text-amber-700">If your company is listed above, contact their admin for an invitation.</p>
                  {/if}

                  {#if domainMatches.length > 0}
                    <div class={orgSuggestions.length > 0 ? "mt-2 pt-2 border-t border-amber-200" : ""}>
                      <p class="text-xs text-amber-800">
                        Your email domain matches:
                        {#each domainMatches as match, i}
                          <span class="font-medium">{match.name}</span>{i < domainMatches.length - 1 ? ", " : ""}
                        {/each}
                      </p>
                    </div>
                  {/if}

                  <button
                    type="button"
                    onclick={confirmOrgUnique}
                    class="mt-2.5 w-full rounded-md border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-50"
                  >
                    None of these — my company is different
                  </button>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Password -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="password">
              Password
            </label>
            <div class="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
                placeholder="Create a password"
                bind:value={password}
                autocomplete="new-password"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors z-10"
                onclick={(e) => { e.preventDefault(); e.stopPropagation(); showPassword = !showPassword; }}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {#if showPassword}
                  <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                {:else}
                  <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                {/if}
              </button>
            </div>
            {#if password.length > 0}
              <ul class="mt-2 space-y-1">
                {#each [
                  { met: pwHasLength, label: "At least 10 characters" },
                  { met: pwHasUpper, label: "One uppercase letter (A\u2013Z)" },
                  { met: pwHasLower, label: "One lowercase letter (a\u2013z)" },
                  { met: pwHasSpecial, label: "One special character (!@#$\u2026)" },
                ] as rule}
                  <li class="flex items-center gap-1.5 text-xs {rule.met ? 'text-neutral-500' : 'text-neutral-300'}">
                    {#if rule.met}
                      <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    {:else}
                      <span class="w-3 h-3 shrink-0 flex items-center justify-center">
                        <span class="block w-1 h-1 rounded-full bg-neutral-300"></span>
                      </span>
                    {/if}
                    {rule.label}
                  </li>
                {/each}
              </ul>
            {/if}
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="confirmPassword">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type={showPassword ? "text" : "password"}
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              placeholder="Re-enter your password"
              bind:value={confirmPassword}
              autocomplete="new-password"
            />
            {#if confirmPassword}
              <p class="mt-1.5 text-xs {passwordsMatch ? 'text-neutral-400' : 'text-red-500'}">
                {passwordsMatch ? "Passwords match." : "Passwords do not match."}
              </p>
            {/if}
          </div>

          <!-- Terms -->
          <div class="flex items-start gap-2.5 pt-1">
            <input
              id="terms"
              type="checkbox"
              class="mt-0.5 h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800"
              bind:checked={agreedToTerms}
            />
            <label for="terms" class="text-xs text-neutral-500 leading-relaxed">
              I agree to the
              <a href="/terms" class="text-neutral-700 font-medium hover:underline">Terms of Service</a>
              and
              <a href="/privacy" class="text-neutral-700 font-medium hover:underline">Privacy Policy</a>
            </label>
          </div>

          <!-- Honeypot (hidden from humans) -->
          <input type="text" name="website" bind:value={honeypot} class="absolute opacity-0 -z-10 pointer-events-none" tabindex="-1" autocomplete="off" aria-hidden="true" />

          <!-- Submit -->
          <button
            type="submit"
            disabled={!canSubmit}
            class="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed mt-2 flex items-center justify-center h-10"
          >
            {#if loading}
              <span class="bouncing-dots"><span></span><span></span><span></span></span>
            {:else}
              Sign Up
            {/if}
          </button>
        </form>
      </div>
    </div>

    <!-- Footer -->
    <div class="mt-8 text-center text-xs text-neutral-400">
      <div class="flex items-center justify-center gap-2 mb-3">
        <a href="/help" class="hover:text-neutral-600 transition-colors">Help Center</a>
        <span class="text-neutral-300">&middot;</span>
        <a href="/privacy" class="hover:text-neutral-600 transition-colors">Privacy Policy</a>
        <span class="text-neutral-300">&middot;</span>
        <a href="/terms" class="hover:text-neutral-600 transition-colors">Terms of Service</a>
      </div>
      <p>&copy; {new Date().getFullYear()} <span class="font-normal text-neutral-800">developer</span><span class="font-bold text-neutral-400">OS</span>. All rights reserved.</p>
    </div>
  </div>
{/if}

<style>
  .dot-grid {
    position: absolute;
    inset: 0;
    background-image: radial-gradient(circle, rgba(255, 255, 255, 0.12) 1px, transparent 1px);
    background-size: 16px 16px;
  }

  /* Success animations */
  .success-check {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .check-path {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawCheck 0.4s ease-out 0.35s forwards;
  }

  .success-fade-in {
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

  .bouncing-dots span:nth-child(1) { animation-delay: -0.32s; }
  .bouncing-dots span:nth-child(2) { animation-delay: -0.16s; }
  .bouncing-dots span:nth-child(3) { animation-delay: 0s; }

  @keyframes dotBounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }
</style>
