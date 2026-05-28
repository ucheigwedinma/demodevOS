<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";

  let emails: string[] = $state(["", ""]);
  let loading = $state(false);
  let sent = $state(false);
  let invitedCount = $state(0);

  function addRow() {
    if (emails.length < 10) {
      emails.push("");
    }
  }

  function removeRow(index: number) {
    if (emails.length > 1) {
      emails.splice(index, 1);
    }
  }

  function updateEmail(index: number, value: string) {
    emails[index] = value;
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();

    const validEmails = emails.filter((e) => e.trim() && e.includes("@"));
    if (validEmails.length === 0) {
      toast.error("No emails", "Please enter at least one valid email address.");
      return;
    }

    loading = true;
    try {
      const res = await api.post<{ invited: string[]; message: string }>(
        "/auth/invite-staff/",
        { emails: validEmails },
      );
      invitedCount = res.invited.length;
      sent = true;
      toast.success("Invitations sent", res.message);
    } catch (err) {
      if (err instanceof ApiError) {
        const errors = err.fieldErrors as Record<string, string | string[]>;
        const detail = errors.detail;
        const message = detail
          ? Array.isArray(detail)
            ? detail[0]
            : detail
          : "Failed to send invitations.";
        toast.error("Invite failed", typeof message === "string" ? message : "Please try again.");
      } else {
        toast.error("Invite failed", "Something went wrong. Please try again.");
      }
    } finally {
      loading = false;
    }
  }

  async function finish() {
    await onboarding.completeOnboarding();
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50 backdrop-blur-sm invite-backdrop"></div>

  <!-- Modal -->
  <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden invite-modal">
    <div class="h-1 bg-neutral-900"></div>

    <div class="p-8">
      {#if sent}
        <!-- Success State -->
        <div class="text-center">
          <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white invite-success-icon">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path class="invite-check-path" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h2 class="text-xl font-bold text-neutral-900">Invitations sent!</h2>
          <p class="mt-3 text-sm text-neutral-500 leading-relaxed">
            {invitedCount} invitation{invitedCount !== 1 ? "s" : ""} sent successfully.<br />
            Your team members will receive a signup link via email.
          </p>

          <button
            onclick={finish}
            class="mt-7 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      {:else}
        <!-- Invite Form -->
        <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-100 invite-icon">
          <svg class="w-7 h-7 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM3 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 9.374 21c-2.331 0-4.512-.645-6.374-1.766Z" />
          </svg>
        </div>

        <div class="text-center mb-7">
          <h2 class="text-xl font-bold text-neutral-900">Invite your team</h2>
          <p class="mt-2 text-sm text-neutral-500">
            Add team members to
            {#if onboarding.user?.organization}
              <span class="font-medium text-neutral-700">{onboarding.user.organization.name}</span>
            {:else}
              your company
            {/if}
          </p>
        </div>

        <form onsubmit={handleSubmit} class="space-y-3">
          {#each emails as email, i}
            <div class="flex items-center gap-2">
              <div class="relative flex-1">
                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
                </svg>
                <input
                  type="email"
                  class="w-full rounded-lg border border-neutral-300 pl-9 pr-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
                  placeholder="colleague@company.com"
                  value={email}
                  oninput={(e) => updateEmail(i, (e.target as HTMLInputElement).value)}
                />
              </div>
              {#if emails.length > 1}
                <button
                  type="button"
                  onclick={() => removeRow(i)}
                  class="p-2 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
                  aria-label="Remove"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              {/if}
            </div>
          {/each}

          {#if emails.length < 10}
            <button
              type="button"
              onclick={addRow}
              class="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add another
            </button>
          {/if}

          <div class="pt-3 flex flex-col gap-2.5">
            <button
              type="submit"
              disabled={loading}
              class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send Invitations"}
            </button>
            <button
              type="button"
              onclick={finish}
              class="w-full text-sm text-neutral-400 hover:text-neutral-600 transition-colors py-1"
            >
              Skip for now
            </button>
          </div>
        </form>
      {/if}
    </div>
  </div>
</div>

<style>
  .invite-backdrop {
    animation: fadeIn 0.3s ease-out both;
  }

  .invite-modal {
    animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .invite-icon {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .invite-success-icon {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .invite-check-path {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawCheck 0.4s ease-out 0.35s forwards;
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

  @keyframes drawCheck {
    to {
      stroke-dashoffset: 0;
    }
  }
</style>
