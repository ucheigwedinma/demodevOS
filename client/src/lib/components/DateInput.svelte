<script lang="ts">
  let {
    value = $bindable("") as string | null | undefined,
    id = undefined as string | undefined,
    placeholder = "Select date",
    required = false,
    disabled = false,
  } = $props();

  const effectiveValue = $derived(value ?? "");

  let open = $state(false);
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());
  let pendingDate = $state("");
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let popoverEl = $state<HTMLDivElement | null>(null);

  const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
  const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  function daysInMonth(year: number, month: number): number {
    return new Date(year, month + 1, 0).getDate();
  }

  function firstDayOfMonth(year: number, month: number): number {
    return new Date(year, month, 1).getDay();
  }

  const calendarDays = $derived.by(() => {
    const total = daysInMonth(viewYear, viewMonth);
    const startDay = firstDayOfMonth(viewYear, viewMonth);
    const prevTotal = daysInMonth(viewYear, viewMonth - 1);
    const rows: Array<Array<{ day: number; iso: string; current: boolean; today: boolean }>> = [];
    let cells: Array<{ day: number; iso: string; current: boolean; today: boolean }> = [];
    const todayStr = new Date().toISOString().split("T")[0];

    // Previous month padding
    for (let i = startDay - 1; i >= 0; i--) {
      const d = prevTotal - i;
      const m = viewMonth === 0 ? 11 : viewMonth - 1;
      const y = viewMonth === 0 ? viewYear - 1 : viewYear;
      const iso = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      cells.push({ day: d, iso, current: false, today: iso === todayStr });
    }

    // Current month
    for (let d = 1; d <= total; d++) {
      const iso = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      cells.push({ day: d, iso, current: true, today: iso === todayStr });
      if (cells.length === 7) {
        rows.push(cells);
        cells = [];
      }
    }

    // Next month padding
    if (cells.length > 0) {
      let d = 1;
      const m = viewMonth === 11 ? 0 : viewMonth + 1;
      const y = viewMonth === 11 ? viewYear + 1 : viewYear;
      while (cells.length < 7) {
        const iso = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        cells.push({ day: d, iso, current: false, today: iso === todayStr });
        d++;
      }
      rows.push(cells);
    }

    // Pad to 6 rows for fixed height
    while (rows.length < 6) {
      const lastIso = rows[rows.length - 1][6].iso;
      const lastDate = new Date(lastIso + "T00:00:00");
      const week: typeof cells = [];
      for (let i = 1; i <= 7; i++) {
        const nd = new Date(lastDate);
        nd.setDate(nd.getDate() + i);
        const iso = nd.toISOString().split("T")[0];
        week.push({ day: nd.getDate(), iso, current: false, today: iso === todayStr });
      }
      rows.push(week);
    }

    return rows;
  });

  function formatDisplay(str: string): string {
    if (!str) return "";
    const d = new Date(str + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function formatHeader(str: string): string {
    if (!str) return "No date selected";
    const d = new Date(str + "T00:00:00");
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  }

  function openPicker() {
    if (disabled) return;
    pendingDate = effectiveValue;
    if (effectiveValue) {
      const parts = effectiveValue.split("-");
      viewYear = Number(parts[0]);
      viewMonth = Number(parts[1]) - 1;
    } else {
      const now = new Date();
      viewYear = now.getFullYear();
      viewMonth = now.getMonth();
    }
    open = true;
  }

  function prevMonth() {
    if (viewMonth === 0) { viewYear--; viewMonth = 11; }
    else viewMonth--;
  }

  function nextMonth() {
    if (viewMonth === 11) { viewYear++; viewMonth = 0; }
    else viewMonth++;
  }

  function selectDay(iso: string) {
    pendingDate = iso;
  }

  function handleConfirm() {
    if (pendingDate) value = pendingDate;
    open = false;
  }

  function handleCancel() {
    open = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape" && open) {
      e.stopPropagation();
      open = false;
    }
  }

  function handleClickOutside(e: MouseEvent) {
    if (
      open &&
      triggerEl &&
      popoverEl &&
      !triggerEl.contains(e.target as Node) &&
      !popoverEl.contains(e.target as Node)
    ) {
      open = false;
    }
  }
</script>

<svelte:document onclick={handleClickOutside} onkeydown={handleKeydown} />

<div class="relative">
  <button
    type="button"
    {id}
    bind:this={triggerEl}
    onclick={openPicker}
    {disabled}
    class="w-full flex items-center justify-between px-3 py-2 text-sm border rounded-lg text-left transition-colors
           {disabled ? 'bg-neutral-50 text-neutral-400 cursor-not-allowed border-neutral-200' : 'bg-white border-neutral-200 hover:border-neutral-300 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent cursor-pointer'}
           {required && !effectiveValue ? 'border-neutral-200' : ''}"
  >
    <span class={effectiveValue ? "text-neutral-900" : "text-neutral-400"}>
      {effectiveValue ? formatDisplay(effectiveValue) : placeholder}
    </span>
    <svg class="w-4 h-4 text-neutral-400 shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
    </svg>
  </button>

  {#if open}
    <div
      bind:this={popoverEl}
      class="absolute z-50 mt-1 left-0 rounded-2xl shadow-2xl border border-neutral-200 bg-white overflow-hidden dateinput-enter"
      style="width: 320px;"
    >
      <!-- Header -->
      <div class="bg-neutral-900 px-6 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-neutral-400 mb-1">Select date</p>
        <p class="text-xl font-semibold text-white">{formatHeader(pendingDate)}</p>
      </div>

      <!-- Month navigation -->
      <div class="flex items-center justify-between px-4 pt-3 pb-1">
        <button type="button" onclick={prevMonth} aria-label="Previous month" class="h-8 w-8 flex items-center justify-center rounded-full hover:bg-neutral-100 transition-colors text-neutral-600">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <span class="text-sm font-semibold text-neutral-900">{MONTH_NAMES[viewMonth]} {viewYear}</span>
        <button type="button" onclick={nextMonth} aria-label="Next month" class="h-8 w-8 flex items-center justify-center rounded-full hover:bg-neutral-100 transition-colors text-neutral-600">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>

      <!-- Calendar grid -->
      <div class="px-3 pb-1">
        <div class="grid grid-cols-7 mb-1">
          {#each WEEKDAYS as wd}
            <div class="text-center text-xs font-medium text-neutral-500 py-2">{wd}</div>
          {/each}
        </div>

        {#each calendarDays as week}
          <div class="grid grid-cols-7">
            {#each week as cell}
              <div class="flex items-center justify-center p-0.5">
                <button
                  type="button"
                  onclick={() => selectDay(cell.iso)}
                  class="h-9 w-9 flex items-center justify-center rounded-full text-sm transition-colors
                         {cell.iso === pendingDate ? 'bg-neutral-900 text-white font-semibold' : ''}
                         {cell.today && cell.iso !== pendingDate ? 'border border-neutral-900' : ''}
                         {!cell.current ? 'text-neutral-300' : cell.iso !== pendingDate ? 'text-neutral-800 hover:bg-neutral-100 cursor-pointer' : ''}"
                >
                  {cell.day}
                </button>
              </div>
            {/each}
          </div>
        {/each}
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-2 px-4 py-3 border-t border-neutral-100">
        <button type="button" onclick={handleCancel} class="px-4 py-2 text-sm font-semibold text-neutral-900 rounded-lg hover:bg-neutral-100 transition-colors">
          Cancel
        </button>
        <button type="button" onclick={handleConfirm} class="px-4 py-2 text-sm font-semibold text-neutral-900 rounded-lg hover:bg-neutral-100 transition-colors">
          OK
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .dateinput-enter {
    animation: dateinputFadeIn 0.15s ease-out both;
  }

  @keyframes dateinputFadeIn {
    from {
      opacity: 0;
      transform: translateY(-4px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
</style>
