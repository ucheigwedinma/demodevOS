<script lang="ts">
  import { onboarding } from "$lib/stores/onboarding.svelte";

  let trialEndFormatted = $derived(() => {
    const sub = onboarding.user?.subscription;
    if (sub?.trial_end) {
      return new Date(sub.trial_end).toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    }
    return "14 days";
  });

  function goToDashboard() {
    onboarding.dismissTrialSuccess();
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50 backdrop-blur-sm trial-success-backdrop"></div>

  <!-- Modal -->
  <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl overflow-hidden trial-success-modal">
    <div class="h-1 bg-neutral-900"></div>

    <div class="p-8 text-center">
      <!-- Animated checkmark -->
      <div class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white trial-success-icon">
        <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path class="trial-check-path" stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
        </svg>
      </div>

      <h2 class="text-xl font-bold text-neutral-900">Your trial is active!</h2>
      <p class="mt-3 text-sm text-neutral-500 leading-relaxed">
        You now have full access to
        <span class="font-semibold text-neutral-700">
          <span class="font-normal">developer</span><span class="font-bold text-neutral-400">OS</span> {onboarding.user?.subscription?.edition_name ?? "Growth"}
        </span>
        until <span class="font-semibold text-neutral-700">{trialEndFormatted()}</span>.
      </p>
      <p class="mt-2 text-xs text-neutral-400">
        A confirmation email has been sent to your registered email address.
      </p>

      <button
        onclick={goToDashboard}
        class="mt-7 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
      >
        Go to Dashboard
      </button>
    </div>
  </div>
</div>

<style>
  .trial-success-backdrop {
    animation: fadeIn 0.3s ease-out both;
  }

  .trial-success-modal {
    animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .trial-success-icon {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .trial-check-path {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawCheck 0.4s ease-out 0.35s forwards;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes modalSlideUp {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }

  @keyframes scaleIn {
    from { transform: scale(0); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  @keyframes drawCheck {
    to { stroke-dashoffset: 0; }
  }
</style>
