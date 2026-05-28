<script lang="ts">
  let {
    label,
    value,
    subtitle,
    icon,
    trend,
    href,
  }: {
    label: string;
    value: string | number;
    subtitle?: string;
    icon?: string;
    trend?: { value: number; label: string };
    href?: string;
  } = $props();
</script>

{#if href}
  <a {href} class="block bg-white rounded-xl border border-neutral-200 p-5 hover:border-neutral-300 hover:shadow-sm transition-all group">
    <div class="flex items-start justify-between">
      <div class="space-y-1">
        <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">{label}</p>
        <p class="text-2xl font-semibold text-neutral-900 tabular-nums">{value}</p>
        {#if subtitle}
          <p class="text-xs text-neutral-400">{subtitle}</p>
        {/if}
        {#if trend}
          <p class="text-xs font-medium {trend.value >= 0 ? 'text-emerald-600' : 'text-red-600'}">
            {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
          </p>
        {/if}
      </div>
      {#if icon}
        <div class="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 group-hover:bg-neutral-200 transition-colors">
          <svg class="w-4.5 h-4.5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d={icon} />
          </svg>
        </div>
      {/if}
    </div>
  </a>
{:else}
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="flex items-start justify-between">
      <div class="space-y-1">
        <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">{label}</p>
        <p class="text-2xl font-semibold text-neutral-900 tabular-nums">{value}</p>
        {#if subtitle}
          <p class="text-xs text-neutral-400">{subtitle}</p>
        {/if}
        {#if trend}
          <p class="text-xs font-medium {trend.value >= 0 ? 'text-emerald-600' : 'text-red-600'}">
            {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
          </p>
        {/if}
      </div>
      {#if icon}
        <div class="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
          <svg class="w-4.5 h-4.5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d={icon} />
          </svg>
        </div>
      {/if}
    </div>
  </div>
{/if}
