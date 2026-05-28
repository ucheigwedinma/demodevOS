<script lang="ts">
  import { onMount } from "svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import { api, ApiError } from "$lib/api";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    AccountListItem,
    PayrollGLBulkSyncResult,
    PayrollGLLineKind,
    PayrollGLMapping,
    PayrollGLPosting,
    PayrollGLPostingStatus,
    PayrollRunListItem,
  } from "$lib/types";

  const MAX_PAGES = 10;

  const RUN_STATUS_CLASSES: Record<string, string> = {
    draft: "bg-neutral-100 border-neutral-200 text-neutral-600",
    processing: "bg-sky-50 border-sky-200 text-sky-700",
    completed: "bg-emerald-50 border-emerald-200 text-emerald-700",
    cancelled: "bg-rose-50 border-rose-200 text-rose-700",
  };

  const POSTING_STATUS_CLASSES: Record<PayrollGLPostingStatus | "unposted", string> = {
    draft: "bg-neutral-100 border-neutral-200 text-neutral-600",
    posted: "bg-emerald-50 border-emerald-200 text-emerald-700",
    reversed: "bg-amber-50 border-amber-200 text-amber-700",
    failed: "bg-rose-50 border-rose-200 text-rose-700",
    unposted: "bg-neutral-100 border-neutral-200 text-neutral-600",
  };

  const CHIP_BASE =
    "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider";

  type LineKindConfig = {
    kind: PayrollGLLineKind;
    label: string;
    description: string;
    allowedTypes: ReadonlyArray<string>;
  };

  const LINE_KIND_CONFIG: LineKindConfig[] = [
    {
      kind: "gross_salary",
      label: "Gross salary expense",
      description: "Debited for the total gross of every posted payroll run.",
      allowedTypes: ["expense"],
    },
    {
      kind: "employee_deductions",
      label: "Employee deductions payable",
      description: "Credited with statutory + voluntary deductions held on behalf of staff.",
      allowedTypes: ["liability"],
    },
    {
      kind: "net_payable",
      label: "Net salary payable",
      description: "Credited with the cash payable to employees on payday.",
      allowedTypes: ["liability"],
    },
  ];

  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state<string | null>(null);

  let accounts = $state<AccountListItem[]>([]);
  let mappings = $state<PayrollGLMapping[]>([]);
  let payrollRuns = $state<PayrollRunListItem[]>([]);
  let postings = $state<PayrollGLPosting[]>([]);

  let pendingSelections = $state<Partial<Record<PayrollGLLineKind, number | "">>>({});
  let savingMapping = $state<Record<PayrollGLLineKind, boolean>>({
    gross_salary: false,
    employee_deductions: false,
    net_payable: false,
  });
  let runActionPending = $state<Record<number, boolean>>({});
  let bulkSyncing = $state(false);

  function getSettledValue<T>(result: PromiseSettledResult<T[]>, fallback: T[]): T[] {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatCurrency(value: number, digits = 0): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currency.config.code || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(Number.isFinite(value) ? value : 0);
  }

  function shortDate(value: string | null | undefined): string {
    const date = parseDate(value);
    if (!date) return "—";
    return new Intl.DateTimeFormat("en-NG", { day: "numeric", month: "short", year: "numeric" }).format(date);
  }

  function formatStatusLabel(value: string): string {
    return value
      .split("_")
      .map((part) => (part.length === 0 ? part : part[0].toUpperCase() + part.slice(1)))
      .join(" ");
  }

  function relativeTime(date: Date | null): string {
    if (!date) return "Never";
    const diffSeconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSeconds < 60) return "Just now";
    const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    if (diffSeconds < 3600) return formatter.format(-Math.floor(diffSeconds / 60), "minute");
    if (diffSeconds < 86400) return formatter.format(-Math.floor(diffSeconds / 3600), "hour");
    if (diffSeconds < 2592000) return formatter.format(-Math.floor(diffSeconds / 86400), "day");
    if (diffSeconds < 31536000) return formatter.format(-Math.floor(diffSeconds / 2592000), "month");
    return formatter.format(-Math.floor(diffSeconds / 31536000), "year");
  }

  function describeError(err: unknown, fallback: string): string {
    if (err instanceof ApiError) {
      const data = err.data as { detail?: string } | null;
      if (data?.detail) return data.detail;
      if (err.message) return err.message;
    }
    if (err instanceof Error && err.message) return err.message;
    return fallback;
  }

  async function loadData(background = false) {
    if (background) refreshing = true;
    else loading = true;
    error = null;

    try {
      const results = await Promise.allSettled([
        fetchAllPages<AccountListItem>("/finance/accounts/", { page_size: "200", is_active: "true" }, MAX_PAGES),
        fetchAllPages<PayrollGLMapping>("/finance/payroll-gl-mappings/", { page_size: "50" }, MAX_PAGES),
        fetchAllPages<PayrollRunListItem>("/hr/payroll-runs/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<PayrollGLPosting>("/finance/payroll-gl-postings/", { page_size: "200" }, MAX_PAGES),
      ]);

      accounts = getSettledValue(results[0], []);
      mappings = getSettledValue(results[1], []);
      payrollRuns = getSettledValue(results[2], []);
      postings = getSettledValue(results[3], []);

      // seed pending selects from current mappings so the controls reflect server state
      const next: Partial<Record<PayrollGLLineKind, number | "">> = {};
      for (const mapping of mappings) {
        next[mapping.line_kind] = mapping.account;
      }
      pendingSelections = next;

      const criticalFailed = results[0].status === "rejected" || results[2].status === "rejected";
      if (criticalFailed) error = "We couldn't reach the accounting service right now.";
    } catch {
      error = "We couldn't reach the accounting service right now.";
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadData();
  });

  // ---------- Derived state ----------

  let mappingsByKind = $derived.by(() => {
    const map = new Map<PayrollGLLineKind, PayrollGLMapping>();
    for (const m of mappings) map.set(m.line_kind, m);
    return map;
  });

  let postingByRun = $derived.by(() => {
    const map = new Map<number, PayrollGLPosting>();
    for (const p of postings) map.set(p.payroll_run, p);
    return map;
  });

  let accountsByType = $derived.by(() => {
    const map = new Map<string, AccountListItem[]>();
    for (const acc of accounts) {
      if (!acc.is_active) continue;
      const list = map.get(acc.account_type) ?? [];
      list.push(acc);
      map.set(acc.account_type, list);
    }
    return map;
  });

  function accountsForKind(kind: PayrollGLLineKind): AccountListItem[] {
    const cfg = LINE_KIND_CONFIG.find((c) => c.kind === kind);
    if (!cfg) return [];
    const out: AccountListItem[] = [];
    for (const type of cfg.allowedTypes) {
      out.push(...(accountsByType.get(type) ?? []));
    }
    return out.sort((a, b) => a.code.localeCompare(b.code));
  }

  let postedRunsCount = $derived(
    postings.filter((p) => p.status === "posted").length,
  );

  let pendingGlPostingCount = $derived(
    payrollRuns.filter((run) => {
      if (run.status !== "completed") return false;
      const posting = postingByRun.get(run.id);
      return !posting || posting.status !== "posted";
    }).length,
  );

  let postedNetTotalYtd = $derived.by(() => {
    const currentYear = new Date().getFullYear();
    let total = 0;
    for (const posting of postings) {
      if (posting.status !== "posted") continue;
      const run = payrollRuns.find((r) => r.id === posting.payroll_run);
      if (!run) continue;
      const date = parseDate(run.period_end ?? run.run_date ?? run.period_start);
      if (!date || date.getFullYear() !== currentYear) continue;
      total += toAmount(run.total_net);
    }
    return total;
  });

  let lastSyncedDate = $derived.by(() => {
    const stamps = postings
      .filter((p) => p.status === "posted" && p.posted_at)
      .map((p) => parseDate(p.posted_at)?.getTime() ?? 0)
      .filter((t) => t > 0);
    if (stamps.length === 0) return null;
    return new Date(Math.max(...stamps));
  });

  let recentRuns = $derived.by(() =>
    [...payrollRuns]
      .sort((a, b) => {
        const left = parseDate(a.updated_at)?.getTime() ?? 0;
        const right = parseDate(b.updated_at)?.getTime() ?? 0;
        return right - left;
      })
      .slice(0, 20),
  );

  let allMappingsConfigured = $derived(LINE_KIND_CONFIG.every((cfg) => mappingsByKind.has(cfg.kind)));

  // ---------- Mutations ----------

  async function saveMapping(kind: PayrollGLLineKind) {
    const choice = pendingSelections[kind];
    if (choice === undefined || choice === "" || choice === null) {
      toast.warning("Pick an account", "Choose an account for this payroll line before saving.");
      return;
    }
    savingMapping[kind] = true;
    try {
      await api.post<PayrollGLMapping>("/finance/payroll-gl-mappings/", {
        line_kind: kind,
        account: choice,
      });
      toast.success("Mapping saved", "The payroll → GL mapping has been updated.");
      await loadData(true);
    } catch (err) {
      toast.error("Mapping save failed", describeError(err, "Could not update mapping. Try again."));
    } finally {
      savingMapping[kind] = false;
    }
  }

  async function postRunToGl(run: PayrollRunListItem) {
    runActionPending[run.id] = true;
    try {
      await api.post<PayrollGLPosting>(`/hr/payroll-runs/${run.id}/post-to-gl/`, {});
      toast.success("Posted to GL", `${run.name} has been posted to the general ledger.`);
      await loadData(true);
    } catch (err) {
      toast.error("Posting failed", describeError(err, "Could not post the payroll run to the GL."));
    } finally {
      runActionPending[run.id] = false;
    }
  }

  async function reconcileRun(run: PayrollRunListItem) {
    runActionPending[run.id] = true;
    try {
      await api.post<PayrollGLPosting>(`/hr/payroll-runs/${run.id}/reconcile-gl/`, {});
      toast.success("Reconciled", `${run.name} was reversed and reposted to the GL.`);
      await loadData(true);
    } catch (err) {
      toast.error("Reconciliation failed", describeError(err, "Could not reconcile the run."));
    } finally {
      runActionPending[run.id] = false;
    }
  }

  async function runBulkSync() {
    bulkSyncing = true;
    try {
      const result = await api.post<PayrollGLBulkSyncResult>("/hr/payroll-runs/bulk-sync-gl/", {});
      const parts: string[] = [];
      parts.push(`${result.posted.length} posted`);
      parts.push(`${result.skipped.length} skipped`);
      if (result.errors.length > 0) parts.push(`${result.errors.length} errors`);
      const summary = parts.join(" · ");
      if (result.errors.length > 0) {
        toast.warning("Sync finished with errors", summary);
      } else {
        toast.success("Sync complete", summary);
      }
      await loadData(true);
    } catch (err) {
      toast.error("Bulk sync failed", describeError(err, "Could not sync payroll runs to the GL."));
    } finally {
      bulkSyncing = false;
    }
  }

  function describeRunAction(run: PayrollRunListItem): {
    label: string;
    intent: "post" | "reconcile" | "disabled";
    disabledReason?: string;
  } {
    const posting = postingByRun.get(run.id);
    if (run.status !== "completed") {
      return { label: "Not ready", intent: "disabled", disabledReason: "Complete the run first." };
    }
    if (posting && posting.status === "posted") {
      return { label: "Reconcile", intent: "reconcile" };
    }
    if (!allMappingsConfigured) {
      return {
        label: "Post to GL",
        intent: "disabled",
        disabledReason: "Configure all three account mappings first.",
      };
    }
    return { label: "Post to GL", intent: "post" };
  }

  function postingChipFor(run: PayrollRunListItem): {
    label: string;
    cls: string;
  } {
    const posting = postingByRun.get(run.id);
    if (!posting) {
      return {
        label: "Unposted",
        cls: POSTING_STATUS_CLASSES.unposted,
      };
    }
    return {
      label: posting.status_display || formatStatusLabel(posting.status),
      cls: POSTING_STATUS_CLASSES[posting.status] ?? POSTING_STATUS_CLASSES.unposted,
    };
  }
</script>

<svelte:head>
  <title>Accounting Integration | developerOS</title>
</svelte:head>

{#if loading}
  <div class="flex min-h-[60vh] items-center justify-center">
    <div class="flex items-center gap-3 text-sm text-neutral-500">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Loading accounting integration…
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
          <a href="/payroll" class="hover:text-indigo-700">Payroll</a>
          <span class="text-neutral-300"> › </span>
          <span class="text-indigo-600">Accounting Integration</span>
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Accounting Integration</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Map payroll line kinds to your chart of accounts and post completed payroll runs as balanced journal entries in the general ledger.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950 disabled:opacity-50"
          onclick={() => void loadData(true)}
          disabled={refreshing}
        >
          <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
          </svg>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-50"
          onclick={runBulkSync}
          disabled={bulkSyncing || !allMappingsConfigured}
          title={!allMappingsConfigured ? "Configure all account mappings first" : undefined}
        >
          {bulkSyncing ? "Syncing…" : "Bulk Sync"}
        </button>
      </div>
    </div>

    {#if error}
      <DataStateBanner message={error} onretry={() => loadData(true)} retrying={refreshing} />
    {/if}

    {#if !allMappingsConfigured}
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Configure every payroll line below before posting runs — the GL bridge requires all three mappings to keep journals balanced.
      </div>
    {/if}

    <div class="grid gap-4 xl:grid-cols-4">
      <div class="min-w-0 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">Posted Runs</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-emerald-900">{postedRunsCount}</p>
        <p class="mt-2 text-xs text-emerald-800/90">Payroll runs that have a posted journal entry in the GL.</p>
      </div>

      <div class={`min-w-0 rounded-2xl border p-5 sm:p-6 ${pendingGlPostingCount > 0 ? "border-orange-200 bg-orange-50" : "border-neutral-200 bg-white"}`}>
        <p class={`text-[10px] font-semibold uppercase tracking-wider ${pendingGlPostingCount > 0 ? "text-orange-600" : "text-neutral-500"}`}>
          Pending GL Posting
        </p>
        <p class={`mt-3 text-2xl font-bold tracking-tight tabular-nums ${pendingGlPostingCount > 0 ? "text-orange-900" : "text-neutral-900"}`}>
          {pendingGlPostingCount}
        </p>
        <p class={`mt-2 text-xs ${pendingGlPostingCount > 0 ? "text-orange-800/90" : "text-neutral-500"}`}>
          Completed runs that have not yet been posted to the GL.
        </p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Posted Net (YTD)</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(postedNetTotalYtd)}</p>
        <p class="mt-2 text-xs text-neutral-500">Sum of net amounts on posted runs in the current calendar year.</p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Last Sync</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{relativeTime(lastSyncedDate)}</p>
        <p class="mt-2 text-xs text-neutral-500">
          {lastSyncedDate ? `Most recent posting on ${shortDate(lastSyncedDate.toISOString())}.` : "No postings recorded yet."}
        </p>
      </div>
    </div>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Chart of Accounts Mapping</p>
          <h2 class="mt-2 text-lg font-semibold text-neutral-950">Payroll lines → general ledger</h2>
          <p class="mt-1 text-sm text-neutral-500">
            Each mapping picks the GL account used to record one side of the payroll journal entry.
          </p>
        </div>
      </div>

      <div class="mt-5 overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
              <th class="px-4 py-3">Payroll line</th>
              <th class="px-4 py-3">Account</th>
              <th class="px-4 py-3">Current mapping</th>
              <th class="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each LINE_KIND_CONFIG as cfg (cfg.kind)}
              {@const choices = accountsForKind(cfg.kind)}
              {@const current = mappingsByKind.get(cfg.kind)}
              <tr class="border-t border-neutral-200 align-top hover:bg-neutral-50">
                <td class="px-4 py-3">
                  <p class="font-medium text-neutral-900">{cfg.label}</p>
                  <p class="mt-1 max-w-md text-xs text-neutral-500">{cfg.description}</p>
                </td>
                <td class="px-4 py-3">
                  <select
                    class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-500 focus:outline-none"
                    bind:value={pendingSelections[cfg.kind]}
                  >
                    <option value="">Select an account…</option>
                    {#each choices as account (account.id)}
                      <option value={account.id}>{account.code} — {account.name}</option>
                    {/each}
                  </select>
                  {#if choices.length === 0}
                    <p class="mt-1 text-[11px] text-amber-700">No {cfg.allowedTypes.join("/")} accounts found in the chart of accounts.</p>
                  {/if}
                </td>
                <td class="px-4 py-3 text-neutral-700">
                  {#if current}
                    <p class="font-medium tabular-nums text-neutral-900">{current.account_code ?? "—"}</p>
                    <p class="text-xs text-neutral-500">{current.account_name ?? ""}</p>
                  {:else}
                    <span class="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-700">
                      Not configured
                    </span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded-2xl border border-neutral-900 bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-50"
                    onclick={() => saveMapping(cfg.kind)}
                    disabled={savingMapping[cfg.kind]}
                  >
                    {savingMapping[cfg.kind] ? "Saving…" : "Save"}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Recent Postings</p>
          <h2 class="mt-2 text-lg font-semibold text-neutral-950">Last 20 payroll runs</h2>
          <p class="mt-1 text-sm text-neutral-500">
            Post completed runs to the GL or reconcile previously posted runs (creates a reversal + repost).
          </p>
        </div>
        <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
          {recentRuns.length} entries
        </span>
      </div>

      <div class="mt-5 overflow-x-auto">
        {#if recentRuns.length === 0}
          <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-10 text-center text-sm text-neutral-500">
            No payroll runs have been recorded yet.
          </div>
        {:else}
          <table class="min-w-full text-sm">
            <thead>
              <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                <th class="px-4 py-3">Run</th>
                <th class="px-4 py-3">Period</th>
                <th class="px-4 py-3 text-right">Total Net</th>
                <th class="px-4 py-3">Run status</th>
                <th class="px-4 py-3">GL status</th>
                <th class="px-4 py-3">Journal</th>
                <th class="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {#each recentRuns as run (run.id)}
                {@const action = describeRunAction(run)}
                {@const chip = postingChipFor(run)}
                {@const posting = postingByRun.get(run.id)}
                <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-900">{run.name}</p>
                    <p class="text-xs text-neutral-500">Updated {relativeTime(parseDate(run.updated_at))}</p>
                  </td>
                  <td class="px-4 py-3 text-neutral-700">
                    {shortDate(run.period_start)} → {shortDate(run.period_end)}
                  </td>
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                    {formatCurrency(toAmount(run.total_net))}
                  </td>
                  <td class="px-4 py-3">
                    <span class={`${CHIP_BASE} ${RUN_STATUS_CLASSES[run.status] ?? "bg-neutral-100 border-neutral-200 text-neutral-600"}`}>
                      {formatStatusLabel(run.status)}
                    </span>
                  </td>
                  <td class="px-4 py-3">
                    <span class={`${CHIP_BASE} ${chip.cls}`}>{chip.label}</span>
                  </td>
                  <td class="px-4 py-3 text-neutral-700">
                    {#if posting && posting.journal_number}
                      <span class="tabular-nums text-neutral-900">{posting.journal_number}</span>
                      {#if posting.posted_at}
                        <p class="text-xs text-neutral-500">Posted {shortDate(posting.posted_at)}</p>
                      {/if}
                    {:else}
                      <span class="text-neutral-400">—</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-right">
                    {#if action.intent === "post"}
                      <button
                        type="button"
                        class="inline-flex items-center gap-1 rounded-2xl border border-neutral-900 bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-50"
                        onclick={() => postRunToGl(run)}
                        disabled={runActionPending[run.id]}
                      >
                        {runActionPending[run.id] ? "Posting…" : "Post to GL"}
                      </button>
                    {:else if action.intent === "reconcile"}
                      <button
                        type="button"
                        class="inline-flex items-center gap-1 rounded-2xl border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950 disabled:opacity-50"
                        onclick={() => reconcileRun(run)}
                        disabled={runActionPending[run.id]}
                      >
                        {runActionPending[run.id] ? "Reconciling…" : "Reconcile"}
                      </button>
                    {:else}
                      <span
                        class="inline-flex items-center gap-1 rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-semibold text-neutral-400"
                        title={action.disabledReason}
                      >
                        {action.label}
                      </span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </section>
  </div>
{/if}
