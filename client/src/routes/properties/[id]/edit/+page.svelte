<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Property } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const propertyId = $derived($page.params.id);

  let form = $state({
    name: "",
    property_type: "building" as "land" | "building" | "mixed" | "estate" | "warehouse" | "industrial",
    classification: "owned" as "owned" | "lease" | "concession" | "under_development",
    address: "",
    description: "",
    gps_latitude: "",
    gps_longitude: "",
    plot_number: "",
    acquisition_date: "",
    acquisition_price: "",
    current_value: "",
    total_area_sqft: "",
    is_active: true,
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);
  let loading = $state(true);

  $effect(() => {
    void propertyId;
    loadProperty();
  });

  async function loadProperty() {
    loading = true;
    try {
      const p = await api.get<Property>(`/properties/${propertyId}/`);
      form = {
        name: p.name,
        property_type: p.property_type,
        classification: p.classification,
        address: p.address,
        description: p.description,
        gps_latitude: p.gps_latitude ?? "",
        gps_longitude: p.gps_longitude ?? "",
        plot_number: p.plot_number,
        acquisition_date: p.acquisition_date ?? "",
        acquisition_price: p.acquisition_price ?? "",
        current_value: p.current_value ?? "",
        total_area_sqft: p.total_area_sqft ?? "",
        is_active: p.is_active,
      };
    } catch {
      // Property not found
    }
    loading = false;
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const payload = {
        ...form,
        gps_latitude: form.gps_latitude || null,
        gps_longitude: form.gps_longitude || null,
        acquisition_date: form.acquisition_date || null,
        acquisition_price: form.acquisition_price || null,
        current_value: form.current_value || null,
        total_area_sqft: form.total_area_sqft || null,
      };
      await api.patch(`/properties/${propertyId}/`, payload);
      toast.success("Property updated", `"${form.name}" has been saved`);
      goto(`/properties/${propertyId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the property");
      }
    }
    saving = false;
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="max-w-2xl">
    <Breadcrumb items={[{ label: "Properties", href: "/properties" }, { label: form.name || "Property", href: `/properties/${propertyId}` }, { label: "Edit" }]} />
    <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">Edit Property</h1>

    <form onsubmit={handleSubmit} class="space-y-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <div>
          <label for="name" class="block text-xs font-medium text-neutral-500 mb-1.5">Name</label>
          <input
            id="name"
            bind:value={form.name}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
        </div>

        <div>
          <label for="property_type" class="block text-xs font-medium text-neutral-500 mb-1.5">Type</label>
          <select
            id="property_type"
            bind:value={form.property_type}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="land">Land Parcel</option>
            <option value="building">Building</option>
            <option value="mixed">Mixed-Use</option>
            <option value="estate">Estate</option>
            <option value="warehouse">Warehouse</option>
            <option value="industrial">Industrial</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="classification" class="block text-xs font-medium text-neutral-500 mb-1.5">Classification</label>
            <select
              id="classification"
              bind:value={form.classification}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="owned">Owned</option>
              <option value="lease">Lease</option>
              <option value="concession">Concession</option>
              <option value="under_development">Under Development</option>
            </select>
          </div>
          <div>
            <label for="plot_number" class="block text-xs font-medium text-neutral-500 mb-1.5">Plot Number</label>
            <input
              id="plot_number"
              bind:value={form.plot_number}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label for="address" class="block text-xs font-medium text-neutral-500 mb-1.5">Address</label>
          <textarea
            id="address"
            bind:value={form.address}
            rows={2}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          ></textarea>
          {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">{fieldError("address")}</p>{/if}
        </div>

        <div>
          <label for="description" class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label>
          <textarea
            id="description"
            bind:value={form.description}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          ></textarea>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">GPS Coordinates</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="gps_latitude" class="block text-xs font-medium text-neutral-500 mb-1.5">Latitude</label>
            <input
              id="gps_latitude"
              bind:value={form.gps_latitude}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="-1.2920659"
            />
            {#if fieldError("gps_latitude")}<p class="mt-1 text-xs text-red-500">{fieldError("gps_latitude")}</p>{/if}
          </div>
          <div>
            <label for="gps_longitude" class="block text-xs font-medium text-neutral-500 mb-1.5">Longitude</label>
            <input
              id="gps_longitude"
              bind:value={form.gps_longitude}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="36.8219462"
            />
            {#if fieldError("gps_longitude")}<p class="mt-1 text-xs text-red-500">{fieldError("gps_longitude")}</p>{/if}
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Financials</h3>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="acquisition_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Acquisition Date</label>
            <DateInput id="acquisition_date" bind:value={form.acquisition_date} />
          </div>
          <div>
            <label for="acquisition_price" class="block text-xs font-medium text-neutral-500 mb-1.5">Acquisition Price ({currency.config.symbol})</label>
            <input
              id="acquisition_price"
              bind:value={form.acquisition_price}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("acquisition_price")}<p class="mt-1 text-xs text-red-500">{fieldError("acquisition_price")}</p>{/if}
          </div>
          <div>
            <label for="current_value" class="block text-xs font-medium text-neutral-500 mb-1.5">Current Value ({currency.config.symbol})</label>
            <input
              id="current_value"
              bind:value={form.current_value}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("current_value")}<p class="mt-1 text-xs text-red-500">{fieldError("current_value")}</p>{/if}
          </div>
          <div>
            <label for="total_area_sqft" class="block text-xs font-medium text-neutral-500 mb-1.5">Total Area (sqft)</label>
            <input
              id="total_area_sqft"
              bind:value={form.total_area_sqft}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" bind:checked={form.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
          <span class="text-sm text-neutral-700">Active property</span>
        </label>
      </div>

      <div class="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                 hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
        <a href="/properties/{propertyId}" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
          Cancel
        </a>
      </div>
    </form>
  </div>
{/if}
