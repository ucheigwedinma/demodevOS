<script lang="ts">
  type SupportDeskSectionProps = {
    title: string;
    description: string;
    focusAreas: string[];
    operatingControls: string[];
    implementationNote: string;
  };

  let {
    title,
    description,
    focusAreas,
    operatingControls,
    implementationNote,
  }: SupportDeskSectionProps = $props();
</script>

<div class="space-y-8">
  <section class="overflow-hidden rounded-[28px] border border-neutral-200 bg-[radial-gradient(circle_at_top_right,rgba(14,116,144,0.14),transparent_40%),linear-gradient(180deg,#ffffff,#f7faf9)] p-8 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-6">
      <div class="max-w-3xl space-y-4">
        <span class="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-800">
          Support Desk
        </span>
        <div class="space-y-2">
          <h1 class="text-3xl font-semibold tracking-tight text-neutral-950">{title}</h1>
          <p class="max-w-2xl text-sm leading-6 text-neutral-600">{description}</p>
        </div>
      </div>

      <div class="grid min-w-[240px] gap-3 sm:grid-cols-3 sm:gap-2 xl:w-[360px] xl:grid-cols-1">
        {#each focusAreas.slice(0, 3) as area}
          <div class="rounded-2xl border border-white/70 bg-white/80 p-4 shadow-sm">
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Focus</p>
            <p class="mt-2 text-sm font-medium leading-5 text-neutral-800">{area}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.9fr)]">
    <section class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-neutral-900 text-white">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12h15m-15 4.5h9m-9-9h15" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-neutral-950">Focus Areas</h2>
          <p class="text-sm text-neutral-500">The core operating surface for this part of Support Desk.</p>
        </div>
      </div>

      <div class="mt-6 space-y-4">
        {#each focusAreas as area}
          <div class="flex gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
            <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-cyan-800">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13.5 9 17.5 19 7.5" />
              </svg>
            </div>
            <p class="text-sm leading-6 text-neutral-700">{area}</p>
          </div>
        {/each}
      </div>
    </section>

    <aside class="space-y-6">
      <section class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Operating Controls</h2>
        <p class="mt-1 text-sm text-neutral-500">Configuration elements that typically back this workspace.</p>

        <div class="mt-5 space-y-3">
          {#each operatingControls as control}
            <div class="flex items-start gap-3 rounded-2xl border border-neutral-200 px-4 py-3">
              <div class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-neutral-900"></div>
              <p class="text-sm leading-6 text-neutral-700">{control}</p>
            </div>
          {/each}
        </div>
      </section>

      <section class="rounded-3xl border border-cyan-200 bg-cyan-50 p-7 shadow-sm">
        <h2 class="text-lg font-semibold text-cyan-950">Implementation Note</h2>
        <p class="mt-3 text-sm leading-6 text-cyan-900/80">{implementationNote}</p>
      </section>
    </aside>
  </div>
</div>
