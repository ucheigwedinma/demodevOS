<script lang="ts">
  /**
   * Inline "this is roadmapped, not broken" notice for IAM scaffold pages.
   *
   * Replaces the generic "Coming soon" placeholder with a specific
   * description of what the page WILL do, which roadmap cluster it
   * belongs to, and a link to docs/iam-roadmap.md so the next reader
   * (human or AI) can find context.
   *
   * Intentionally does NOT pretend to be functional — no fake
   * controls, no disabled forms. The user should leave the page
   * knowing exactly what's missing and where it sits in the build
   * order.
   */
  type Props = {
    summary: string;
    will: string[];
    cluster: string;
    note?: string;
  };

  let { summary, will, cluster, note = "" }: Props = $props();
</script>

<div class="rounded-xl border border-neutral-200 bg-white p-6 max-w-3xl space-y-5">
  <div class="flex items-start gap-3">
    <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
      <svg class="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
      </svg>
    </div>
    <div class="min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          Roadmap
        </span>
        <span class="text-xs text-neutral-500">{cluster}</span>
      </div>
      <p class="mt-2 text-sm text-neutral-700">{summary}</p>
    </div>
  </div>

  {#if will.length > 0}
    <div>
      <p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">When built, this page will let you</p>
      <ul class="space-y-1.5 text-sm text-neutral-700">
        {#each will as item}
          <li class="flex items-start gap-2">
            <span class="mt-1.5 w-1 h-1 rounded-full bg-neutral-400 shrink-0"></span>
            <span>{item}</span>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  {#if note}
    <div class="rounded-lg bg-neutral-50 border border-neutral-200 p-3 text-xs text-neutral-600">
      {note}
    </div>
  {/if}

  <div class="pt-3 border-t border-neutral-100 text-xs text-neutral-500">
    Track progress and dependencies in
    <code class="bg-neutral-100 text-neutral-700 px-1.5 py-0.5 rounded">docs/iam-roadmap.md</code>.
    No backend exists for this page yet — calling it directly is safe (no orphaned API requests).
  </div>
</div>
