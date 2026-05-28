<script lang="ts">
  import type {
    WidgetConfig,
    PortfolioAnalytics,
    BoardKpiSnapshot,
    FinanceOverview,
    FinanceCashFlow,
  } from "$lib/types";
  import { getTypeLabel } from "$lib/dashboard/widget-catalog";
  import WidgetRenderer from "./WidgetRenderer.svelte";

  let {
    widgets = $bindable<WidgetConfig[]>(),
    portfolioData = null,
    boardKpiData = null,
    financeData = null,
    cashFlowData = null,
    onremove,
  }: {
    widgets: WidgetConfig[];
    portfolioData?: PortfolioAnalytics | null;
    boardKpiData?: BoardKpiSnapshot | null;
    financeData?: FinanceOverview | null;
    cashFlowData?: FinanceCashFlow | null;
    onremove: (index: number) => void;
  } = $props();

  const COLS = 12;
  const ROW_HEIGHT_PX = 80;
  const GAP_PX = 16;
  const MIN_ROWS = 6;

  let canvasEl: HTMLDivElement | undefined = $state();

  type DragKind = "move" | "resize";
  type DragState = {
    kind: DragKind;
    index: number;
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startX: number;
    startY: number;
    startW: number;
    startH: number;
    stepX: number;
    stepY: number;
  };

  let drag = $state<DragState | null>(null);

  function rectsOverlap(a: WidgetConfig["position"], b: WidgetConfig["position"]): boolean {
    return !(
      a.x + a.w <= b.x ||
      b.x + b.w <= a.x ||
      a.y + a.h <= b.y ||
      b.y + b.h <= a.y
    );
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  const overlapIndices = $derived.by(() => {
    const set = new Set<number>();
    for (let a = 0; a < widgets.length; a += 1) {
      for (let b = a + 1; b < widgets.length; b += 1) {
        if (rectsOverlap(widgets[a].position, widgets[b].position)) {
          set.add(a);
          set.add(b);
        }
      }
    }
    return set;
  });

  const totalRows = $derived(
    widgets.length === 0
      ? MIN_ROWS
      : Math.max(MIN_ROWS, ...widgets.map((w) => w.position.y + w.position.h)),
  );

  function startDrag(event: PointerEvent, kind: DragKind, index: number) {
    if (event.button !== 0 || !canvasEl) return;
    event.preventDefault();

    const rect = canvasEl.getBoundingClientRect();
    const cellWidth = (rect.width - GAP_PX * (COLS - 1)) / COLS;
    const widget = widgets[index];

    drag = {
      kind,
      index,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: widget.position.x,
      startY: widget.position.y,
      startW: widget.position.w,
      startH: widget.position.h,
      stepX: cellWidth + GAP_PX,
      stepY: ROW_HEIGHT_PX + GAP_PX,
    };

    (event.currentTarget as Element).setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: PointerEvent) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = event.clientX - drag.startClientX;
    const dy = event.clientY - drag.startClientY;
    const dCols = Math.round(dx / drag.stepX);
    const dRows = Math.round(dy / drag.stepY);
    const widget = widgets[drag.index];

    if (drag.kind === "move") {
      widget.position.x = clamp(drag.startX + dCols, 0, COLS - widget.position.w);
      widget.position.y = Math.max(0, drag.startY + dRows);
    } else {
      widget.position.w = clamp(drag.startW + dCols, 1, COLS - widget.position.x);
      widget.position.h = Math.max(1, drag.startH + dRows);
    }
  }

  function endDrag(event: PointerEvent) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    drag = null;
  }
</script>

<div
  bind:this={canvasEl}
  onpointermove={onPointerMove}
  onpointerup={endDrag}
  onpointercancel={endDrag}
  class="relative select-none rounded-2xl border border-neutral-200 bg-[linear-gradient(to_right,rgba(0,0,0,0.04)_1px,transparent_1px)] bg-neutral-50/40 p-4"
  style="background-size: calc((100% - {GAP_PX * (COLS - 1)}px) / {COLS} + {GAP_PX}px) 100%; touch-action: none;"
>
  {#if widgets.length === 0}
    <div class="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-white px-8 py-16 text-center">
      <svg class="mb-3 h-12 w-12 text-neutral-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
      </svg>
      <p class="text-sm font-medium text-neutral-700">Pick widgets from the sidebar</p>
      <p class="mt-1 text-xs text-neutral-500">Each widget snaps to a 12-column grid. Drag the header to move; drag the corner to resize.</p>
    </div>
  {:else}
    <div
      class="grid"
      style="grid-template-columns: repeat({COLS}, 1fr); grid-template-rows: repeat({totalRows}, {ROW_HEIGHT_PX}px); gap: {GAP_PX}px;"
    >
      {#each widgets as widget, i (i)}
        {@const isDragging = drag?.index === i}
        {@const isOverlapping = overlapIndices.has(i)}
        <article
          class="group relative overflow-hidden rounded-xl border bg-white {isOverlapping ? 'border-rose-300 ring-2 ring-rose-200' : 'border-neutral-200'} {isDragging ? 'z-10 shadow-lg' : 'shadow-sm hover:shadow'}"
          style="grid-column: {widget.position.x + 1} / span {widget.position.w}; grid-row: {widget.position.y + 1} / span {widget.position.h};"
        >
          <header
            role="button"
            tabindex="-1"
            aria-label="Drag to move widget"
            onpointerdown={(event) => startDrag(event, "move", i)}
            class="flex items-center justify-between gap-2 border-b border-neutral-100 bg-neutral-50/70 px-3 py-1.5 {isDragging && drag?.kind === 'move' ? 'cursor-grabbing' : 'cursor-grab'}"
          >
            <div class="inline-flex min-w-0 items-center gap-2">
              <span class="text-neutral-400" aria-hidden="true">⋮⋮</span>
              <p class="truncate text-[11px] font-semibold text-neutral-700">{getTypeLabel(widget.widget_type)}</p>
              {#if widget.kpi_key}
                <span class="truncate text-[10px] text-neutral-400">{widget.kpi_key.replace(/_/g, " ")}</span>
              {/if}
            </div>
            <div class="flex items-center gap-1.5">
              <span class="rounded-full bg-neutral-100 px-1.5 py-0.5 text-[9px] font-semibold tabular-nums text-neutral-600">
                {widget.position.w}×{widget.position.h}
              </span>
              <button
                type="button"
                onpointerdown={(event) => event.stopPropagation()}
                onclick={() => onremove(i)}
                aria-label="Remove widget"
                class="rounded p-1 text-neutral-400 hover:bg-rose-50 hover:text-rose-600"
              >
                <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </header>

          <div class="h-[calc(100%-2.25rem)] overflow-hidden">
            <WidgetRenderer config={widget} {portfolioData} {boardKpiData} {financeData} {cashFlowData} />
          </div>

          <button
            type="button"
            onpointerdown={(event) => startDrag(event, "resize", i)}
            aria-label="Drag to resize widget"
            class="absolute bottom-0 right-0 h-4 w-4 cursor-nwse-resize border-l border-t border-neutral-200 bg-white text-neutral-400 hover:bg-neutral-50 hover:text-neutral-700"
            style="border-radius: 0 0 0.65rem 0;"
          >
            <svg class="m-auto h-2.5 w-2.5" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
              <path d="M9 9 H7 V7 H9 Z M9 5 H7 V3 H9 Z M5 9 H3 V7 H5 Z" />
            </svg>
          </button>
        </article>
      {/each}
    </div>
  {/if}

  {#if drag}
    <div
      class="pointer-events-none absolute right-3 top-3 rounded-full bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white shadow-lg"
    >
      {drag.kind === "move" ? "Moving" : "Resizing"} ·
      col {widgets[drag.index].position.x}, row {widgets[drag.index].position.y} ·
      {widgets[drag.index].position.w}×{widgets[drag.index].position.h}
    </div>
  {/if}

  {#if overlapIndices.size > 0 && !drag}
    <div class="pointer-events-none absolute bottom-3 right-3 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-semibold text-rose-700">
      {overlapIndices.size / 2} overlapping widget{overlapIndices.size === 2 ? "" : "s"}
    </div>
  {/if}
</div>
