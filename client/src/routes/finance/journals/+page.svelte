<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    AccountListItem,
    JournalEntryListItem,
    JournalSourceType,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type DraftLine = {
    account: string;
    debit_amount: string | number;
    credit_amount: string | number;
    memo: string;
  };

  let loading = $state(true);
  let saving = $state(false);
  let postingId = $state<number | null>(null);
  let showNew = $state(false);

  let entries = $state<JournalEntryListItem[]>([]);
  let accounts = $state<AccountListItem[]>([]);

  let search = $state("");
  let statusFilter = $state("");

  let form = $state({
    entry_date: new Date().toISOString().slice(0, 10),
    description: "",
    reference: "",
    source_type: "manual" as JournalSourceType,
    source_id: "" as string | number,
    lines: [
      { account: "", debit_amount: "", credit_amount: "", memo: "" },
      { account: "", debit_amount: "", credit_amount: "", memo: "" },
    ] as DraftLine[],
  });

  const sourceOptions: { value: JournalSourceType; label: string }[] = [
    { value: "manual", label: "Manual" },
    { value: "bill", label: "Bill" },
    { value: "invoice", label: "Invoice" },
    { value: "payment", label: "Payment" },
    { value: "adjustment", label: "Adjustment" },
    { value: "closing", label: "Closing Entry" },
    { value: "opening", label: "Opening Balance" },
  ];

  const statusClass: Record<string, string> = {
    draft: "bg-amber-50 text-amber-700",
    posted: "bg-emerald-50 text-emerald-700",
    reversed: "bg-neutral-100 text-neutral-600",
  };

  const statusLabel: Record<string, string> = {
    draft: "Draft",
    posted: "Posted",
    reversed: "Reversed",
  };

  async function fetchAccounts() {
    try {
      const res = await api.get<PaginatedResponse<AccountListItem>>("/finance/accounts/", {
        page_size: "500",
        is_active: "true",
      });
      accounts = res.results;
    } catch {
      accounts = [];
    }
  }

  async function fetchEntries() {
    loading = true;
    try {
      const params: Record<string, string> = { ordering: "-entry_date" };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<JournalEntryListItem>>("/finance/journals/", params);
      entries = res.results;
    } catch {
      entries = [];
      toast.error("Load failed", "Could not load journal entries.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchAccounts();
    fetchEntries();
  });

  function resetForm() {
    form = {
      entry_date: new Date().toISOString().slice(0, 10),
      description: "",
      reference: "",
      source_type: "manual",
      source_id: "",
      lines: [
        { account: "", debit_amount: "", credit_amount: "", memo: "" },
        { account: "", debit_amount: "", credit_amount: "", memo: "" },
      ],
    };
  }

  function addLine() {
    form.lines = [...form.lines, { account: "", debit_amount: "", credit_amount: "", memo: "" }];
  }

  function removeLine(index: number) {
    if (form.lines.length <= 2) return;
    form.lines = form.lines.filter((_, i) => i !== index);
  }

  function decimalOrZero(raw: unknown): string {
    if (raw === null || raw === undefined || raw === "") return "0.00";
    const num = typeof raw === "number" ? raw : Number(String(raw).trim());
    if (!Number.isFinite(num) || num < 0) return "0.00";
    return num.toFixed(2);
  }

  function computeTotals(lines: DraftLine[]): { debit: number; credit: number } {
    let debit = 0;
    let credit = 0;
    for (const line of lines) {
      debit += Number(decimalOrZero(line.debit_amount));
      credit += Number(decimalOrZero(line.credit_amount));
    }
    return { debit, credit };
  }

  function formatDate(value: string): string {
    const d = new Date(`${value}T00:00:00`);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  async function saveJournal() {
    if (!form.description.trim()) {
      toast.error("Validation", "Description is required.");
      return;
    }

    const payloadLines = form.lines.map((line) => ({
      account: line.account ? Number(line.account) : null,
      debit_amount: decimalOrZero(line.debit_amount),
      credit_amount: decimalOrZero(line.credit_amount),
      memo: line.memo.trim(),
    }));

    if (payloadLines.some((line) => !line.account)) {
      toast.error("Validation", "Every journal line must have an account.");
      return;
    }

    const { debit, credit } = computeTotals(form.lines);
    if (payloadLines.length < 2) {
      toast.error("Validation", "Journal entry needs at least two lines.");
      return;
    }
    if (debit <= 0 || credit <= 0) {
      toast.error("Validation", "Journal must include debit and credit values.");
      return;
    }
    if (Math.abs(debit - credit) > 0.00001) {
      toast.error("Validation", "Journal is not balanced. Debit must equal credit.");
      return;
    }

    saving = true;
    try {
      const sourceIdRaw = form.source_id;
      const sourceId = sourceIdRaw === null || sourceIdRaw === undefined
        ? ""
        : String(sourceIdRaw).trim();

      await api.post("/finance/journals/", {
        entry_date: form.entry_date,
        description: form.description.trim(),
        reference: form.reference.trim(),
        source_type: form.source_type,
        source_id: sourceId ? Number(sourceId) : null,
        lines: payloadLines,
      });
      toast.success("Journal created", "Draft journal entry has been saved.");
      resetForm();
      closeDrawer();
      fetchEntries();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          (typeof err.data.detail === "string" && err.data.detail) ||
          (Array.isArray(err.data.lines) && typeof err.data.lines[0] === "string" && err.data.lines[0]) ||
          "Could not save journal entry.";
        toast.error("Save failed", detail);
      } else {
        toast.error("Save failed", "Could not save journal entry.");
      }
    } finally {
      saving = false;
    }
  }

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const JOURNAL_SAMPLES = [
    {
      description: "Monthly office rent accrual — March 2025",
      reference: "RENT-2025-03",
      source_type: "manual" as JournalSourceType,
      lines: [
        { debit_amount: 8500, credit_amount: "", memo: "Office rent expense" },
        { debit_amount: "", credit_amount: 8500, memo: "Rent payable to landlord" },
      ],
    },
    {
      description: "Construction material purchase — Site B concrete supply",
      reference: "PO-MAT-0042",
      source_type: "bill" as JournalSourceType,
      lines: [
        { debit_amount: 24750, credit_amount: "", memo: "Concrete & rebar delivery" },
        { debit_amount: 3712.5, credit_amount: "", memo: "VAT on materials (15%)" },
        { debit_amount: "", credit_amount: 28462.5, memo: "Payment to Al-Rashid Supplies" },
      ],
    },
    {
      description: "Contractor progress payment — Phase 2 structural works",
      reference: "CERT-SW-007",
      source_type: "payment" as JournalSourceType,
      lines: [
        { debit_amount: 145000, credit_amount: "", memo: "Structural works — 35% completion" },
        { debit_amount: "", credit_amount: 14500, memo: "10% retention withheld" },
        { debit_amount: "", credit_amount: 130500, memo: "Net payment to contractor" },
      ],
    },
  ];

  let journalDevIdx = $state(0);

  function devFillJournal() {
    const sample = JOURNAL_SAMPLES[journalDevIdx % JOURNAL_SAMPLES.length];
    journalDevIdx++;

    form.entry_date = new Date().toISOString().slice(0, 10);
    form.description = sample.description;
    form.reference = sample.reference;
    form.source_type = sample.source_type;
    form.source_id = "";

    form.lines = sample.lines.map((line, i) => ({
      account: accounts.length > 0 ? String(accounts[i % accounts.length].id) : "",
      debit_amount: line.debit_amount,
      credit_amount: line.credit_amount,
      memo: line.memo,
    }));
  }

  function openDrawer() {
    resetForm();
    showNew = true;
  }

  function closeDrawer() {
    showNew = false;
  }

  async function postEntry(entryId: number) {
    postingId = entryId;
    try {
      await api.post(`/finance/journals/${entryId}/post/`, {});
      toast.success("Journal posted", "Entry posted to general ledger.");
      fetchEntries();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          (typeof err.data.detail === "string" && err.data.detail) ||
          "Could not post journal entry.";
        toast.error("Post failed", detail);
      } else {
        toast.error("Post failed", "Could not post journal entry.");
      }
    } finally {
      postingId = null;
    }
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounting</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Journal Entries</h1>
      <p class="text-sm text-neutral-500 mt-1">Create, review, and post balanced journals with full auditability into the general ledger.</p>
    </div>
    <button
      onclick={openDrawer}
      class="inline-flex items-center gap-2 rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
    >
      + New Journal
    </button>
  </div>

  <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    <div class="px-5 py-4 border-b border-neutral-100 flex flex-wrap items-center gap-3">
      <input
        type="text"
        bind:value={search}
        placeholder="Search by number, description, reference"
        class="flex-1 min-w-[220px] rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
      />

      <select
        bind:value={statusFilter}
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
      >
        <option value="">All statuses</option>
        <option value="draft">Draft</option>
        <option value="posted">Posted</option>
        <option value="reversed">Reversed</option>
      </select>

      <button
        onclick={fetchEntries}
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Apply
      </button>
    </div>

    {#if loading}
      <div class="py-16 text-center text-sm text-neutral-500">Loading journals...</div>
    {:else if entries.length === 0}
      <div class="py-16 text-center text-sm text-neutral-500">No journal entries found.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full min-w-[980px] text-sm">
          <thead>
            <tr class="border-b border-neutral-100 text-left">
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Journal</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Date</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Description</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500 text-right">Debit</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500 text-right">Credit</th>
              <th class="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-neutral-500 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each entries as entry (entry.id)}
              <tr class="border-b border-neutral-50 hover:bg-neutral-50/60 transition-colors">
                <td class="px-5 py-3.5 font-medium text-neutral-800">{entry.journal_number}</td>
                <td class="px-5 py-3.5 text-neutral-600">{formatDate(entry.entry_date)}</td>
                <td class="px-5 py-3.5">
                  <p class="font-medium text-neutral-800">{entry.description}</p>
                  {#if entry.reference}
                    <p class="text-xs text-neutral-500 mt-0.5">Ref: {entry.reference}</p>
                  {/if}
                </td>
                <td class="px-5 py-3.5">
                  <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass[entry.status] ?? "bg-neutral-100 text-neutral-600"}`}>
                    {statusLabel[entry.status] ?? entry.status}
                  </span>
                </td>
                <td class="px-5 py-3.5 text-right tabular-nums text-neutral-700">{currency.format(entry.total_debit)}</td>
                <td class="px-5 py-3.5 text-right tabular-nums text-neutral-700">{currency.format(entry.total_credit)}</td>
                <td class="px-5 py-3.5 text-right">
                  {#if entry.status === "draft"}
                    <button
                      onclick={() => postEntry(entry.id)}
                      disabled={postingId === entry.id}
                      class="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
                    >
                      {postingId === entry.id ? "Posting..." : "Post"}
                    </button>
                  {:else}
                    <span class="text-xs text-neutral-400">{entry.posted_at ? "Posted" : "-"}</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

<!-- New Journal Entry Drawer -->
{#if showNew}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
      <h2 class="text-lg font-bold text-neutral-800">New Journal Entry</h2>
      <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <div class="grid grid-cols-2 gap-3">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1">Entry Date</span>
          <DateInput bind:value={form.entry_date} />
        </label>
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1">Reference</span>
          <input type="text" bind:value={form.reference} placeholder="Optional reference" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        </label>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1">Source Type</span>
          <select bind:value={form.source_type} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
            {#each sourceOptions as source}
              <option value={source.value}>{source.label}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1">Source ID</span>
          <input type="number" min="1" bind:value={form.source_id} placeholder="Optional" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        </label>
      </div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1">Description</span>
        <textarea bind:value={form.description} rows={2} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" placeholder="Journal description"></textarea>
      </label>

      <!-- Journal Lines -->
      <div>
        <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">Journal Lines</h3>
        <div class="border border-neutral-200 rounded-lg overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-neutral-50 border-b border-neutral-200">
                <th class="px-2 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide text-left w-8">#</th>
                <th class="px-2 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide text-left">Account</th>
                <th class="px-2 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide text-right w-24">Debit</th>
                <th class="px-2 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide text-right w-24">Credit</th>
                <th class="px-2 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide text-left">Memo</th>
                <th class="px-2 py-2 w-14"></th>
              </tr>
            </thead>
            <tbody>
              {#each form.lines as line, index}
                <tr class="border-b border-neutral-100">
                  <td class="px-2 py-2 text-neutral-400 text-xs">{index + 1}</td>
                  <td class="px-2 py-2">
                    <select bind:value={line.account} class="w-full rounded border border-neutral-200 px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
                      <option value="">Select</option>
                      {#each accounts as account}
                        <option value={String(account.id)}>{account.code} - {account.name}</option>
                      {/each}
                    </select>
                  </td>
                  <td class="px-2 py-2">
                    <input type="number" min="0" step="0.01" bind:value={line.debit_amount} class="w-full rounded border border-neutral-200 px-2 py-1.5 text-xs text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                  </td>
                  <td class="px-2 py-2">
                    <input type="number" min="0" step="0.01" bind:value={line.credit_amount} class="w-full rounded border border-neutral-200 px-2 py-1.5 text-xs text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                  </td>
                  <td class="px-2 py-2">
                    <input type="text" bind:value={line.memo} placeholder="Optional" class="w-full rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                  </td>
                  <td class="px-2 py-2 text-right">
                    <button type="button" onclick={() => removeLine(index)} class="text-[10px] font-medium text-red-500 hover:text-red-700 disabled:text-neutral-300" disabled={form.lines.length <= 2}>Del</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between mt-2">
          <button type="button" onclick={addLine} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">+ Add Line</button>
          <div class="text-xs text-neutral-500">
            Debit: <span class="font-semibold text-neutral-800">{currency.format(computeTotals(form.lines).debit)}</span>
            <span class="mx-1.5">|</span>
            Credit: <span class="font-semibold text-neutral-800">{currency.format(computeTotals(form.lines).credit)}</span>
            {#if Math.abs(computeTotals(form.lines).debit - computeTotals(form.lines).credit) < 0.01 && computeTotals(form.lines).debit > 0}
              <span class="ml-2 text-emerald-600 font-semibold">Balanced</span>
            {:else if computeTotals(form.lines).debit > 0 || computeTotals(form.lines).credit > 0}
              <span class="ml-2 text-red-500 font-semibold">Unbalanced</span>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
      {#if isDev}
        <button type="button" onclick={devFillJournal} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeDrawer} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="button" onclick={saveJournal} disabled={saving} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : "Save Draft"}</button>
    </div>
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>
