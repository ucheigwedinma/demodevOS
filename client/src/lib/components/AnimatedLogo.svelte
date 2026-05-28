<script lang="ts">
  let { size = 48, animate = true }: { size?: number; animate?: boolean } = $props();
</script>

<div
  class="inline-flex items-center justify-center"
  class:animate-logo={animate}
  style="width: {size}px; height: {size}px;"
>
  <svg
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
  >
    <!-- Building body -->
    <rect class="building-base" x="10" y="20" width="55" height="70" rx="4" fill="currentColor" />

    <!-- Grid dots - row by row, staggered animation -->
    <!-- Row 1 -->
    <circle class="dot dot-1" cx="24" cy="35" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-2" cx="37" cy="35" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-3" cx="50" cy="35" r="3" fill="var(--dot-color, #fff)" />

    <!-- Row 2 -->
    <circle class="dot dot-4" cx="24" cy="48" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-5" cx="37" cy="48" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-6" cx="50" cy="48" r="3" fill="var(--dot-color, #fff)" />

    <!-- Row 3 -->
    <circle class="dot dot-7" cx="24" cy="61" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-8" cx="37" cy="61" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-9" cx="50" cy="61" r="3" fill="var(--dot-color, #fff)" />

    <!-- Row 4 -->
    <circle class="dot dot-10" cx="24" cy="74" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-11" cx="37" cy="74" r="3" fill="var(--dot-color, #fff)" />
    <circle class="dot dot-12" cx="50" cy="74" r="3" fill="var(--dot-color, #fff)" />

    <!-- Folded corner / document flap -->
    <path class="flap" d="M65 20 L65 38 L83 38 Z" fill="currentColor" opacity="0.6" />
  </svg>
</div>

<style>
  .animate-logo .building-base {
    animation: slideUp 0.6s ease-out both;
  }

  .animate-logo .flap {
    animation: flapIn 0.4s ease-out 0.5s both;
  }

  .animate-logo .dot {
    opacity: 0;
    animation: dotPop 0.3s ease-out both;
  }

  .animate-logo .dot-1  { animation-delay: 0.3s; }
  .animate-logo .dot-2  { animation-delay: 0.38s; }
  .animate-logo .dot-3  { animation-delay: 0.46s; }
  .animate-logo .dot-4  { animation-delay: 0.4s; }
  .animate-logo .dot-5  { animation-delay: 0.48s; }
  .animate-logo .dot-6  { animation-delay: 0.56s; }
  .animate-logo .dot-7  { animation-delay: 0.5s; }
  .animate-logo .dot-8  { animation-delay: 0.58s; }
  .animate-logo .dot-9  { animation-delay: 0.66s; }
  .animate-logo .dot-10 { animation-delay: 0.6s; }
  .animate-logo .dot-11 { animation-delay: 0.68s; }
  .animate-logo .dot-12 { animation-delay: 0.76s; }

  @keyframes slideUp {
    from {
      transform: translateY(12px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  @keyframes dotPop {
    from {
      transform: scale(0);
      opacity: 0;
    }
    to {
      transform: scale(1);
      opacity: 1;
    }
  }

  @keyframes flapIn {
    from {
      transform: scale(0) rotate(-10deg);
      transform-origin: 65px 38px;
      opacity: 0;
    }
    to {
      transform: scale(1) rotate(0deg);
      transform-origin: 65px 38px;
      opacity: 0.6;
    }
  }
</style>
