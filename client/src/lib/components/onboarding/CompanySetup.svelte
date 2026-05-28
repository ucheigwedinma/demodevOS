<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";

  let companyName = $state("");
  let industry = $state("");
  let companySize = $state("");
  let loading = $state(false);
  let showContactAdmin = $state(false);

  // Real-time org name checking
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
        const res = await api.post<CheckCompanyResponse>("/auth/check-company/", {
          name: trimmed,
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

  const industries = [
    "Real Estate Development",
    "Construction",
    "Property Management",
    "Architecture & Design",
    "Civil Engineering",
    "Infrastructure",
    "Mixed-Use Development",
    "Other",
  ];

  const sizes = [
    { value: "1-10", label: "1–10 employees" },
    { value: "11-50", label: "11–50 employees" },
    { value: "51-200", label: "51–200 employees" },
    { value: "201-500", label: "201–500 employees" },
    { value: "500+", label: "500+ employees" },
  ];

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();

    if (!companyName.trim()) {
      toast.error("Missing field", "Please enter your company name.");
      return;
    }

    loading = true;
    try {
      const res = await api.post<{ id: number; name: string; message: string }>(
        "/auth/setup-company/",
        {
          name: companyName.trim(),
          industry,
          size: companySize,
        },
      );

      toast.success("Company created", res.message);
      onboarding.completeCompanySetup({
        id: res.id,
        name: res.name,
        industry,
        size: companySize,
        role: "admin",
        assigned_role: null,
        permissions: ["*"],
        is_setup_complete: true,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        const errors = err.fieldErrors as Record<string, string | string[]>;
        const nameErr = errors.name;
        if (nameErr) {
          // Company already exists
          showContactAdmin = true;
        } else {
          const firstKey = Object.keys(errors)[0];
          const val = firstKey ? errors[firstKey] : null;
          const message = val
            ? Array.isArray(val)
              ? val[0]
              : val
            : "Something went wrong.";
          toast.error("Setup failed", typeof message === "string" ? message : "Please try again.");
        }
      } else {
        toast.error("Setup failed", "Something went wrong. Please try again.");
      }
    } finally {
      loading = false;
    }
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50 backdrop-blur-sm setup-backdrop"></div>

  {#if showContactAdmin}
    <!-- Contact Admin Modal -->
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl overflow-hidden setup-modal">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-8 text-center">
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
          <svg class="w-6 h-6 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
        </div>

        <h2 class="text-lg font-bold text-neutral-900">Company already exists</h2>
        <p class="mt-3 text-sm text-neutral-500 leading-relaxed">
          <span class="font-medium text-neutral-700">{companyName}</span> is already registered on
          <span class="font-normal">developer</span><span class="font-bold text-neutral-400">OS</span>.<br /><br />
          Please contact your company administrator to receive an invitation to join.
        </p>

        <button
          onclick={() => (showContactAdmin = false)}
          class="mt-7 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
        >
          Try a different name
        </button>
      </div>
    </div>
  {:else}
    <!-- Setup Form Modal -->
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden setup-modal">
      <!-- Top accent -->
      <div class="h-1 bg-neutral-900"></div>

      <div class="p-8">
        <!-- Icon -->
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-100 setup-icon">
          <svg class="w-7 h-7 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
          </svg>
        </div>

        <div class="text-center mb-7">
          <h2 class="text-xl font-bold text-neutral-900">Set up your company</h2>
          <p class="mt-2 text-sm text-neutral-500">Tell us about your organization to get started.</p>
        </div>

        <form onsubmit={handleSubmit} class="space-y-4">
          <!-- Company Name -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="companyName">
              Company Name <span class="text-red-400">*</span>
            </label>
            <div class="relative">
              <input
                id="companyName"
                type="text"
                class="w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-shadow {orgNameError ? 'border-red-300 focus:ring-red-500' : 'border-neutral-300 focus:ring-neutral-900'}"
                placeholder="e.g. Acme Development Corp"
                bind:value={companyName}
                oninput={() => checkOrgName(companyName)}
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

          <!-- Industry -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="industry">
              Industry
            </label>
            <select
              id="industry"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
              bind:value={industry}
            >
              <option value="">Select an industry</option>
              {#each industries as ind}
                <option value={ind}>{ind}</option>
              {/each}
            </select>
          </div>

          <!-- Company Size -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1.5" for="companySize">
              Company Size
            </label>
            <select
              id="companySize"
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
              bind:value={companySize}
            >
              <option value="">Select size</option>
              {#each sizes as s}
                <option value={s.value}>{s.label}</option>
              {/each}
            </select>
          </div>

          <!-- Admin badge -->
          <div class="flex items-center gap-2 rounded-lg bg-neutral-50 border border-neutral-200 px-3.5 py-3">
            <svg class="w-4 h-4 text-neutral-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
            </svg>
            <p class="text-xs text-neutral-500">You'll be set as the <span class="font-semibold text-neutral-700">Company Admin</span></p>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            disabled={loading || !companyName.trim() || orgNameAvailable === false || (orgNameMatchType === "similar" && !userConfirmedUnique)}
            class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Creating..." : "Create Company"}
          </button>
        </form>
      </div>
    </div>
  {/if}
</div>

<style>
  .setup-backdrop {
    animation: fadeIn 0.3s ease-out both;
  }

  .setup-modal {
    animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .setup-icon {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes modalSlideUp {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
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
</style>
