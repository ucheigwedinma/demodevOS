<script lang="ts">
  import type { ProjectTimelineData } from "$lib/types";

  let { data }: { data: ProjectTimelineData } = $props();

  const ROW_HEIGHT = 48;
  const HEADER_HEIGHT = 40;
  const LEFT_MARGIN = 180;
  const DAY_WIDTH = 3;
  const PADDING_DAYS = 14;

  // Collect all dates to compute range
  const allDates = $derived.by(() => {
    const dates: Date[] = [];
    if (data.project.start_date) dates.push(new Date(data.project.start_date));
    if (data.project.target_end_date) dates.push(new Date(data.project.target_end_date));
    for (const phase of data.phases) {
      if (phase.planned_start_date) dates.push(new Date(phase.planned_start_date));
      if (phase.planned_end_date) dates.push(new Date(phase.planned_end_date));
      if (phase.actual_start_date) dates.push(new Date(phase.actual_start_date));
      if (phase.actual_end_date) dates.push(new Date(phase.actual_end_date));
      for (const m of phase.milestones) {
        if (m.target_date) dates.push(new Date(m.target_date));
        if (m.completed_date) dates.push(new Date(m.completed_date));
      }
    }
    dates.push(new Date()); // always include today
    return dates;
  });

  const minDate = $derived.by(() => {
    if (allDates.length === 0) return new Date();
    const min = new Date(Math.min(...allDates.map((d) => d.getTime())));
    min.setDate(min.getDate() - PADDING_DAYS);
    min.setDate(1); // snap to first of month
    return min;
  });

  const maxDate = $derived.by(() => {
    if (allDates.length === 0) return new Date();
    const max = new Date(Math.max(...allDates.map((d) => d.getTime())));
    max.setDate(max.getDate() + PADDING_DAYS);
    return max;
  });

  const totalDays = $derived(Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24))));
  const svgWidth = $derived(LEFT_MARGIN + totalDays * DAY_WIDTH);
  const svgHeight = $derived(HEADER_HEIGHT + data.phases.length * ROW_HEIGHT + 20);

  function dateToX(date: Date): number {
    const days = (date.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
    return LEFT_MARGIN + days * DAY_WIDTH;
  }

  const today = new Date();
  const todayX = $derived(dateToX(today));

  // Generate month markers
  const monthMarkers = $derived.by(() => {
    const markers: Array<{ x: number; label: string }> = [];
    const d = new Date(minDate);
    d.setDate(1);
    while (d <= maxDate) {
      markers.push({
        x: dateToX(d),
        label: d.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      });
      d.setMonth(d.getMonth() + 1);
    }
    return markers;
  });

  const hasData = $derived(data.phases.some(
    (p) => p.planned_start_date || p.actual_start_date || p.milestones.some((m) => m.target_date),
  ));
</script>

<div class="bg-white rounded-xl border border-neutral-200 p-6">
  <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Project Timeline</h3>

  {#if !hasData}
    <div class="py-12 text-center">
      <p class="text-neutral-400 text-sm">Add dates to your phases to see the timeline.</p>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <svg width={svgWidth} height={svgHeight} class="font-sans">
        <!-- Month grid lines and headers -->
        {#each monthMarkers as month}
          <line
            x1={month.x} y1={HEADER_HEIGHT}
            x2={month.x} y2={svgHeight}
            stroke="#f5f5f5" stroke-width="1"
          />
          <text
            x={month.x + 4} y={16}
            class="text-[10px] fill-neutral-400" font-family="inherit"
          >{month.label}</text>
        {/each}

        <!-- Separator line -->
        <line
          x1={0} y1={HEADER_HEIGHT}
          x2={svgWidth} y2={HEADER_HEIGHT}
          stroke="#e5e5e5" stroke-width="1"
        />

        <!-- Phase rows -->
        {#each data.phases as phase, i}
          {@const rowY = HEADER_HEIGHT + i * ROW_HEIGHT}
          {@const centerY = rowY + ROW_HEIGHT / 2}

          <!-- Row background (alternating) -->
          {#if i % 2 === 0}
            <rect x={0} y={rowY} width={svgWidth} height={ROW_HEIGHT} fill="#fafafa" />
          {/if}

          <!-- Phase label -->
          <text
            x={12} y={centerY + 4}
            class="text-[11px] fill-neutral-700 font-medium" font-family="inherit"
          >{phase.name.length > 20 ? phase.name.slice(0, 20) + "..." : phase.name}</text>

          <!-- Planned bar -->
          {#if phase.planned_start_date && phase.planned_end_date}
            {@const x1 = dateToX(new Date(phase.planned_start_date))}
            {@const x2 = dateToX(new Date(phase.planned_end_date))}
            <rect
              x={x1} y={centerY - 7}
              width={Math.max(x2 - x1, 4)} height={6}
              rx={3} fill="#e5e5e5"
            />
          {/if}

          <!-- Actual bar -->
          {#if phase.actual_start_date}
            {@const x1 = dateToX(new Date(phase.actual_start_date))}
            {@const endDate = phase.actual_end_date ? new Date(phase.actual_end_date) : today}
            {@const x2 = dateToX(endDate)}
            <rect
              x={x1} y={centerY + 1}
              width={Math.max(x2 - x1, 4)} height={6}
              rx={3}
              fill={phase.status === "completed" ? "#171717" : "#737373"}
            />
          {/if}

          <!-- Milestones -->
          {#each phase.milestones as milestone}
            {#if milestone.target_date}
              {@const mx = dateToX(new Date(milestone.target_date))}
              <g transform="translate({mx},{centerY}) rotate(45)">
                <rect
                  x={-4} y={-4} width={8} height={8}
                  fill={milestone.is_completed ? "#171717" : "white"}
                  stroke={milestone.is_completed ? "#171717" : "#a3a3a3"}
                  stroke-width="1.5"
                />
              </g>
              <title>{milestone.name}{milestone.target_date ? ` — ${milestone.target_date}` : ""}</title>
            {/if}
          {/each}
        {/each}

        <!-- Today line -->
        <line
          x1={todayX} y1={HEADER_HEIGHT}
          x2={todayX} y2={svgHeight}
          stroke="#dc2626" stroke-width="1"
          stroke-dasharray="4 3"
        />
        <text
          x={todayX + 4} y={HEADER_HEIGHT - 6}
          class="text-[9px] fill-red-500 font-medium" font-family="inherit"
        >Today</text>
      </svg>
    </div>

    <!-- Legend -->
    <div class="flex items-center gap-6 mt-4 text-xs text-neutral-400">
      <div class="flex items-center gap-2">
        <div class="w-8 h-1.5 rounded-full bg-neutral-200"></div>
        <span>Planned</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-8 h-1.5 rounded-full bg-neutral-900"></div>
        <span>Actual</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rotate-45 bg-neutral-900"></div>
        <span>Milestone (done)</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rotate-45 border border-neutral-400 bg-white"></div>
        <span>Milestone (pending)</span>
      </div>
    </div>
  {/if}
</div>
