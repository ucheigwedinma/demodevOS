<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import PropertyMap from "$lib/components/PropertyMap.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import type { Unit, Property, PropertyInventoryEvent } from "$lib/types";

  const unitId = $derived($page.params.id);

  let unit = $state<Unit | null>(null);
  let property = $state<Property | null>(null);
  let loading = $state(true);
  let activeTab = $state<"overview" | "documents" | "inventory">("overview");

  let inventoryEvents = $state<PropertyInventoryEvent[]>([]);
  let eventsLoading = $state(false);

  let holdBusy = $state(false);
  let holdBy = $state("");
  let holdNotes = $state("");

  const eventTypeLabels: Record<string, string> = {
    listed: "Listed",
    held: "Held",
    hold_released: "Hold Released",
    hold_expired: "Hold Expired",
    reserved: "Reserved",
    reservation_cancelled: "Reservation Cancelled",
    sold: "Sold",
    leased: "Leased",
    made_unavailable: "Made Unavailable",
    made_available: "Made Available",
    price_changed: "Price Changed",
    note_added: "Note Added",
  };

  const unitCategoryLabels: Record<string, string> = {
    apartment: "Apartment",
    villa: "Villa",
    townhouse: "Townhouse",
    penthouse: "Penthouse",
    studio: "Studio",
    duplex: "Duplex",
    office: "Office",
    retail: "Retail",
    warehouse: "Warehouse",
    land: "Land",
    other: "Other",
  };

  async function loadUnit() {
    loading = true;
    try {
      unit = await api.get<Unit>(`/properties/units/${unitId}/`);
      property = await api.get<Property>(`/properties/${unit.property}/`);
    } catch {
      unit = null;
      property = null;
    }
    loading = false;
  }

  async function loadEvents() {
    if (!unit?.inventory) return;
    eventsLoading = true;
    try {
      const res = await api.get<{ results: PropertyInventoryEvent[] } | PropertyInventoryEvent[]>(
        `/properties/inventory/${unit.inventory.id}/events/`
      );
      inventoryEvents = Array.isArray(res) ? res : res.results;
    } catch {
      inventoryEvents = [];
    }
    eventsLoading = false;
  }

  $effect(() => {
    void unitId;
    loadUnit();
  });

  $effect(() => {
    if (activeTab === "inventory" && unit?.inventory) {
      loadEvents();
    }
  });

  function fmtCurrency(value: string | null): string {
    if (!value) return "--";
    return currency.formatCompact(value);
  }

  function fmtDate(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async function placeHold() {
    if (!unit?.inventory) return;
    holdBusy = true;
    try {
      await api.post(`/properties/inventory/${unit.inventory.id}/hold/`, {
        held_by: holdBy,
        notes: holdNotes,
      });
      holdBy = "";
      holdNotes = "";
      await loadUnit();
      await loadEvents();
    } catch {
      // error handled by api layer
    }
    holdBusy = false;
  }

  async function releaseHold() {
    if (!unit?.inventory) return;
    holdBusy = true;
    try {
      await api.post(`/properties/inventory/${unit.inventory.id}/release/`, {});
      await loadUnit();
      await loadEvents();
    } catch {
      // error handled by api layer
    }
    holdBusy = false;
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !unit || !property}
  <div class="text-center py-24">
    <p class="text-neutral-400">Unit not found.</p>
    <a href="/properties" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to properties</a>
  </div>
{:else}
  <div class="space-y-6">
    <div>
      <Breadcrumb items={[{ label: "Properties", href: "/properties" }, { label: property.name, href: `/properties/${property.id}` }, { label: `Unit ${unit.unit_number}` }]} />
      <h1 class="text-2xl font-bold text-neutral-900 mt-3">Unit {unit.unit_number}</h1>
      <div class="flex items-center gap-3 mt-2">
        <StatusBadge status={unit.status} />
        <a href={`/properties/${property.id}`} class="text-sm text-neutral-500 hover:text-neutral-900 transition-colors">{property.name}</a>
      </div>
    </div>

    <div class="border-b border-neutral-200">
      <nav class="flex gap-6">
        {#each [
          { key: "overview", label: "Overview" },
          { key: "inventory", label: "Inventory" },
          { key: "documents", label: "Documents" },
        ] as tab}
          <button
            onclick={() => (activeTab = tab.key as typeof activeTab)}
            class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px
                   {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
          >
            {tab.label}
          </button>
        {/each}
      </nav>
    </div>

    {#if activeTab === "overview"}
      <div class="grid lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Unit Details</h3>
            <div class="grid md:grid-cols-2 gap-x-10 gap-y-3 text-sm">
              <div class="flex justify-between"><span class="text-neutral-400">Unit Number</span><span class="text-neutral-900">{unit.unit_number}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Status</span><StatusBadge status={unit.status} /></div>
              <div class="flex justify-between"><span class="text-neutral-400">Floor</span><span class="text-neutral-900">{unit.floor ?? "--"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Area</span><span class="text-neutral-900">{Number(unit.area_sqft).toLocaleString()} sqft</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Category</span><span class="text-neutral-900">{unitCategoryLabels[unit.unit_category] ?? unit.unit_category}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Bedrooms</span><span class="text-neutral-900">{unit.bedrooms ?? "--"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Bathrooms</span><span class="text-neutral-900">{unit.bathrooms ?? "--"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Asking Price</span><span class="text-neutral-900 tabular-nums">{fmtCurrency(unit.asking_price)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Property</span><a href={`/properties/${property.id}`} class="text-neutral-900 hover:underline">{property.name}</a></div>
              {#if unit.location_description}
                <div class="flex justify-between md:col-span-2"><span class="text-neutral-400">Location</span><span class="text-neutral-900">{unit.location_description}</span></div>
              {/if}
              {#if unit.gps_latitude && unit.gps_longitude}
                <div class="flex justify-between"><span class="text-neutral-400">GPS Coordinates</span><span class="text-neutral-900 tabular-nums">{unit.gps_latitude}, {unit.gps_longitude}</span></div>
              {/if}
            </div>
          </div>
        </div>

        <div class="space-y-6">
          {#if property.map_available && unit.gps_latitude && unit.gps_longitude}
            <PropertyMap
              latitude={Number(unit.gps_latitude)}
              longitude={Number(unit.gps_longitude)}
            />
          {:else if property.map_available && property.gps_latitude && property.gps_longitude}
            <div>
              <PropertyMap
                latitude={Number(property.gps_latitude)}
                longitude={Number(property.gps_longitude)}
              />
              <p class="mt-1.5 text-[11px] text-neutral-400">Showing property location — no unit GPS set.</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    {#if activeTab === "inventory"}
      {#if unit.inventory}
        {@const inv = unit.inventory}
        <div class="grid lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2 space-y-6">
            <!-- Inventory Status Card -->
            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Inventory Status</h3>
                <StatusBadge status={inv.status} size="md" />
              </div>
              <div class="grid md:grid-cols-2 gap-x-10 gap-y-3 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">List Price</span><span class="text-neutral-900 tabular-nums">{fmtCurrency(inv.list_price)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Asking Price</span><span class="text-neutral-900 tabular-nums">{fmtCurrency(unit.asking_price)}</span></div>
                {#if inv.held_by}
                  <div class="flex justify-between"><span class="text-neutral-400">Held By</span><span class="text-neutral-900">{inv.held_by}</span></div>
                {/if}
                {#if inv.held_until}
                  <div class="flex justify-between"><span class="text-neutral-400">Hold Expires</span><span class="text-neutral-900">{fmtDateTime(inv.held_until)}</span></div>
                {/if}
                {#if inv.allocated_to}
                  <div class="flex justify-between"><span class="text-neutral-400">Allocated To</span><span class="text-neutral-900">{inv.allocated_to}</span></div>
                {/if}
                {#if inv.allocated_on}
                  <div class="flex justify-between"><span class="text-neutral-400">Allocated On</span><span class="text-neutral-900">{fmtDate(inv.allocated_on)}</span></div>
                {/if}
                <div class="flex justify-between"><span class="text-neutral-400">Last Updated</span><span class="text-neutral-900">{fmtDateTime(inv.updated_at)}</span></div>
              </div>
              {#if inv.notes}
                <div class="mt-4 pt-4 border-t border-neutral-100">
                  <p class="text-xs text-neutral-400 mb-1">Notes</p>
                  <p class="text-sm text-neutral-700">{inv.notes}</p>
                </div>
              {/if}
            </div>

            <!-- Event Timeline -->
            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Activity Timeline</h3>
              {#if eventsLoading}
                <div class="flex items-center justify-center py-8">
                  <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
                </div>
              {:else if inventoryEvents.length === 0}
                <p class="text-sm text-neutral-400 py-4">No events recorded yet.</p>
              {:else}
                <div class="relative">
                  <div class="absolute left-[7px] top-2 bottom-2 w-px bg-neutral-200"></div>
                  <div class="space-y-4">
                    {#each inventoryEvents as event}
                      <div class="flex gap-3 relative">
                        <div class="w-[15px] h-[15px] rounded-full border-2 border-neutral-300 bg-white shrink-0 mt-0.5 z-10"></div>
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-sm font-medium text-neutral-900">{eventTypeLabels[event.event_type] ?? event.event_type}</span>
                            {#if event.from_status && event.to_status}
                              <span class="text-xs text-neutral-400">
                                <StatusBadge status={event.from_status} size="sm" />
                                <span class="mx-1">&rarr;</span>
                                <StatusBadge status={event.to_status} size="sm" />
                              </span>
                            {/if}
                          </div>
                          <div class="flex items-center gap-3 mt-0.5">
                            <span class="text-xs text-neutral-400">{fmtDateTime(event.created_at)}</span>
                            {#if event.actor_name}
                              <span class="text-xs text-neutral-500">by {event.actor_name}</span>
                            {/if}
                          </div>
                          {#if event.notes}
                            <p class="text-xs text-neutral-500 mt-1">{event.notes}</p>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          </div>

          <!-- Actions Sidebar -->
          <div class="space-y-6">
            {#if inv.status === "available"}
              <div class="bg-white rounded-xl border border-neutral-200 p-6">
                <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Place Hold</h3>
                <div class="space-y-3">
                  <div>
                    <label for="hold-by" class="block text-xs text-neutral-500 mb-1">Held By</label>
                    <input
                      id="hold-by"
                      type="text"
                      bind:value={holdBy}
                      placeholder="Name or identifier"
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label for="hold-notes" class="block text-xs text-neutral-500 mb-1">Notes</label>
                    <textarea
                      id="hold-notes"
                      bind:value={holdNotes}
                      placeholder="Reason for hold..."
                      rows="2"
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                    ></textarea>
                  </div>
                  <button
                    onclick={placeHold}
                    disabled={holdBusy || !holdBy.trim()}
                    class="w-full rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {holdBusy ? "Placing Hold..." : "Place Hold"}
                  </button>
                </div>
              </div>
            {/if}

            {#if inv.status === "held"}
              <div class="bg-white rounded-xl border border-neutral-200 p-6">
                <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Release Hold</h3>
                <p class="text-sm text-neutral-500 mb-3">
                  Currently held by <span class="font-medium text-neutral-900">{inv.held_by || "Unknown"}</span>
                  {#if inv.held_until}
                    until {fmtDateTime(inv.held_until)}
                  {/if}
                </p>
                <button
                  onclick={releaseHold}
                  disabled={holdBusy}
                  class="w-full rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-neutral-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {holdBusy ? "Releasing..." : "Release Hold"}
                </button>
              </div>
            {/if}
          </div>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 text-center">
          <p class="text-sm text-neutral-400">No inventory record found for this unit.</p>
        </div>
      {/if}
    {/if}

    {#if activeTab === "documents"}
      <DocumentRecordsTable
        title="Unit Documents"
        subtitle="Auto-filtered controlled repository view for this unit."
        query={{ unit: Number(unitId) }}
        pageSize={14}
        showViewAll={true}
        viewAllHref={`/documents/repository?unit=${unitId}`}
        emptyMessage="No controlled repository documents are linked to this unit yet."
      />
    {/if}
  </div>
{/if}
