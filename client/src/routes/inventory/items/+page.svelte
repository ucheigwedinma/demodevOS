<script lang="ts">
  import { api } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    CostCenter,
    InventoryItemListItem,
    InventoryItemCategory,
    PaginatedResponse,
    VendorListItem,
  } from "$lib/types";

  type AccountOption = { id: number; code: string; name: string };

  const CATEGORY_OPTIONS: { value: InventoryItemCategory; label: string }[] = [
    { value: "structural", label: "Structural" },
    { value: "finishing", label: "Finishing" },
    { value: "mep", label: "MEP" },
    { value: "electrical", label: "Electrical" },
    { value: "plumbing", label: "Plumbing" },
    { value: "safety", label: "Safety" },
    { value: "consumable", label: "Consumable" },
    { value: "spare", label: "Spare" },
    { value: "equipment", label: "Equipment" },
    { value: "other", label: "Other" },
  ];

  let items = $state<InventoryItemListItem[]>([]);
  let vendors = $state<VendorListItem[]>([]);
  let accounts = $state<AccountOption[]>([]);
  let costCenters = $state<CostCenter[]>([]);

  let loading = $state(true);
  let creating = $state(false);
  let showCreate = $state(false);

  let currentPage = $state(1);
  let pageSize = $state(25);
  let totalCount = $state(0);

  let search = $state("");
  let category = $state("");
  let active = $state("");

  let form = $state({
    sku: "",
    name: "",
    description: "",
    category: "other",
    unit_of_measure: "ea",
    reorder_level: "0",
    target_stock_level: "0",
    default_unit_cost: "0",
    preferred_vendor: "",
    expense_account: "",
    cost_center: "",
    is_active: true,
  });

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      ordering: "name",
    };
    if (search.trim()) params.search = search.trim();
    if (category) params.category = category;
    if (active) params.is_active = active;
    return params;
  }

  async function fetchItems() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<InventoryItemListItem>>("/inventory/items/", buildParams());
      items = res.results;
      totalCount = res.count;
    } catch {
      items = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load inventory items.");
    } finally {
      loading = false;
    }
  }

  async function fetchOptions() {
    try {
      const [vendorRes, accountRes, costCenterRes] = await Promise.all([
        api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", {
          page_size: "200",
          ordering: "name",
        }),
        api.get<PaginatedResponse<AccountOption>>("/finance/accounts/", {
          page_size: "200",
          ordering: "code",
        }),
        api.get<PaginatedResponse<CostCenter>>("/settings/cost-centers/", {
          page_size: "200",
          ordering: "name",
        }),
      ]);
      vendors = vendorRes.results;
      accounts = accountRes.results;
      costCenters = costCenterRes.results;
    } catch {
      vendors = [];
      accounts = [];
      costCenters = [];
    }
  }

  async function createItem() {
    if (!form.sku.trim() || !form.name.trim()) {
      toast.error("Validation", "SKU and Name are required.");
      return;
    }

    creating = true;
    try {
      await api.post("/inventory/items/", {
        sku: form.sku.trim(),
        name: form.name.trim(),
        description: form.description,
        category: form.category,
        unit_of_measure: form.unit_of_measure.trim() || "ea",
        reorder_level: form.reorder_level || "0",
        target_stock_level: form.target_stock_level || "0",
        default_unit_cost: form.default_unit_cost || "0",
        preferred_vendor: form.preferred_vendor ? Number(form.preferred_vendor) : null,
        expense_account: form.expense_account ? Number(form.expense_account) : null,
        cost_center: form.cost_center ? Number(form.cost_center) : null,
        is_active: form.is_active,
      });

      toast.success("Created", "Inventory item added.");
      showCreate = false;
      form = {
        sku: "",
        name: "",
        description: "",
        category: "other",
        unit_of_measure: "ea",
        reorder_level: "0",
        target_stock_level: "0",
        default_unit_cost: "0",
        preferred_vendor: "",
        expense_account: "",
        cost_center: "",
        is_active: true,
      };
      currentPage = 1;
      await fetchItems();
    } catch {
      toast.error("Create failed", "Could not create inventory item.");
    } finally {
      creating = false;
    }
  }

  function fmtCurrency(value: string): string {
    const n = Number(value || 0);
    return currency.format(n);
  }

  $effect(() => {
    fetchOptions();
  });

  $effect(() => {
    fetchItems();
  });

  useAutoRefresh("InventoryItem", fetchItems);
</script>

<div class="space-y-6">
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Inventory</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Items</h1>
      <p class="text-sm text-neutral-400 mt-1">Material master linked to procurement, projects, and budgets.</p>
    </div>
    <button
      class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800"
      onclick={() => (showCreate = !showCreate)}
    >
      {showCreate ? "Close" : "Add Item"}
    </button>
  </div>

  {#if showCreate}
    <section class="bg-white rounded-xl border border-neutral-200 p-5 space-y-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-500">New Inventory Item</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label class="text-xs text-neutral-500">SKU
          <input class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.sku} />
        </label>
        <label class="text-xs text-neutral-500">Name
          <input class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.name} />
        </label>
        <label class="text-xs text-neutral-500">Category
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.category}>
            {#each CATEGORY_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Unit of Measure
          <input class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.unit_of_measure} />
        </label>
        <label class="text-xs text-neutral-500">Reorder Level
          <input type="number" min="0" step="0.001" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.reorder_level} />
        </label>
        <label class="text-xs text-neutral-500">Target Stock
          <input type="number" min="0" step="0.001" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.target_stock_level} />
        </label>
        <label class="text-xs text-neutral-500">Default Unit Cost
          <input type="number" min="0" step="0.01" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.default_unit_cost} />
        </label>
        <label class="text-xs text-neutral-500">Preferred Vendor
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.preferred_vendor}>
            <option value="">Unassigned</option>
            {#each vendors as vendor}
              <option value={vendor.id}>{vendor.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Expense Account
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.expense_account}>
            <option value="">Unassigned</option>
            {#each accounts as account}
              <option value={account.id}>{account.code} - {account.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Cost Center
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.cost_center}>
            <option value="">Unassigned</option>
            {#each costCenters as center}
              <option value={center.id}>{center.name}</option>
            {/each}
          </select>
        </label>
      </div>
      <label class="text-xs text-neutral-500 block">Description
        <textarea rows="3" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.description}></textarea>
      </label>
      <label class="inline-flex items-center gap-2 text-sm text-neutral-600">
        <input type="checkbox" bind:checked={form.is_active} /> Active
      </label>
      <div>
        <button
          class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-60"
          onclick={createItem}
          disabled={creating}
        >
          {creating ? "Saving..." : "Create Item"}
        </button>
      </div>
    </section>
  {/if}

  <section class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <input
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        placeholder="Search by SKU or name"
        bind:value={search}
        oninput={() => {
          currentPage = 1;
          fetchItems();
        }}
      />
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        bind:value={category}
        onchange={() => {
          currentPage = 1;
          fetchItems();
        }}
      >
        <option value="">All categories</option>
        {#each CATEGORY_OPTIONS as option}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        bind:value={active}
        onchange={() => {
          currentPage = 1;
          fetchItems();
        }}
      >
        <option value="">All statuses</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        bind:value={pageSize}
        onchange={() => {
          currentPage = 1;
          fetchItems();
        }}
      >
        <option value={10}>10 rows</option>
        <option value={25}>25 rows</option>
        <option value={50}>50 rows</option>
      </select>
    </div>

    <div class="mt-4 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 text-left text-[11px] uppercase tracking-wider text-neutral-400">
            <th class="px-3 py-2">Item</th>
            <th class="px-3 py-2">Category</th>
            <th class="px-3 py-2">UoM</th>
            <th class="px-3 py-2 text-right">Reorder</th>
            <th class="px-3 py-2 text-right">Unit Cost</th>
            <th class="px-3 py-2">Finance Tag</th>
            <th class="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#if loading}
            <tr>
              <td colspan="7" class="px-3 py-10 text-center text-sm text-neutral-400">Loading items...</td>
            </tr>
          {:else if items.length === 0}
            <tr>
              <td colspan="7" class="px-3 py-10 text-center text-sm text-neutral-400">No items found</td>
            </tr>
          {:else}
            {#each items as item}
              <tr class="hover:bg-neutral-50">
                <td class="px-3 py-3">
                  <p class="text-sm font-medium text-neutral-900">{item.name}</p>
                  <p class="text-xs text-neutral-400">{item.sku}</p>
                </td>
                <td class="px-3 py-3 text-sm text-neutral-600 capitalize">{item.category.replaceAll("_", " ")}</td>
                <td class="px-3 py-3 text-sm text-neutral-600">{item.unit_of_measure}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-600 tabular-nums">{Number(item.reorder_level).toLocaleString()}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-700 tabular-nums">{fmtCurrency(item.default_unit_cost)}</td>
                <td class="px-3 py-3 text-xs text-neutral-500">
                  {#if item.expense_account_code}
                    {item.expense_account_code}
                  {:else}
                    <span class="text-neutral-300">Unmapped</span>
                  {/if}
                  {#if item.cost_center_name}
                    <span class="text-neutral-300"> / </span>{item.cost_center_name}
                  {/if}
                </td>
                <td class="px-3 py-3">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${item.is_active ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"}`}>
                    {item.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <div class="mt-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <p class="text-xs text-neutral-400">Showing {startItem}-{endItem} of {totalCount}</p>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40"
          onclick={() => {
            if (currentPage > 1) {
              currentPage -= 1;
              fetchItems();
            }
          }}
          disabled={currentPage <= 1}
        >
          Prev
        </button>
        <span class="text-sm text-neutral-500">Page {currentPage} of {totalPages}</span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40"
          onclick={() => {
            if (currentPage < totalPages) {
              currentPage += 1;
              fetchItems();
            }
          }}
          disabled={currentPage >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  </section>
</div>
