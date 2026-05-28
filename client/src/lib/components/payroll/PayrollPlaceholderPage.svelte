<script lang="ts">
  type Props = {
    title: string;
    description: string;
  };

  let { title, description }: Props = $props();
</script>

<svelte:head>
  <title>{title} | developerOS</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6">
  <section class="overflow-hidden rounded-[28px] border border-neutral-200 bg-[radial-gradient(circle_at_top_left,_rgba(244,114,182,0.14),_transparent_38%),linear-gradient(135deg,_#ffffff_0%,_#fff9fb_45%,_#f7f7f7_100%)] p-8 shadow-sm">
    <p class="text-xs font-semibold uppercase tracking-[0.35em] text-rose-500">Payroll</p>
    <h1 class="mt-4 text-3xl font-semibold tracking-tight text-neutral-950">{title}</h1>
    <p class="mt-3 max-w-2xl text-base leading-7 text-neutral-600">{description}</p>
  </section>

  <div class="grid gap-4 lg:grid-cols-[1.4fr,1fr]">
    <div class="rounded-[24px] border border-neutral-200 bg-white p-6 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Status</p>
      <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-900">Page scaffolded and linked</h2>
      <p class="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
        This screen is now available from the Payroll sidebar and is ready for the next round of build-out.
      </p>
    </div>

    <div class="rounded-[24px] border border-dashed border-neutral-300 bg-neutral-50 p-6">
      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Next</p>
      <p class="mt-3 text-sm leading-6 text-neutral-600">
        Share the layout, table, KPI, or workflow details you want here and I can build the full page on top of this stub.
      </p>
    </div>
  </div>
</div>
