<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaymentPlanListItem,
    PaymentPlanDirection,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  type CreateForm = typeof createForm;
  const PAYMENT_PLAN_SAMPLES: CreateForm[] = [
    {
      title: "Unit buyer instalment schedule — Block A (Unit 12B)",
      description: "12-month fixed instalment plan for off-plan residential unit purchase. 10% deposit paid, balance spread across equal monthly payments aligned with construction milestones.",
      plan_type: "fixed_installment",
      direction: "receivable",
      frequency: "monthly",
      total_amount: "1850000",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10),
      number_of_installments: "12",
      customer: "",
      vendor: "",
      investor: "",
      project: "",
      notes: "First instalment due on signing. Buyer: Khalid Al-Rashid. SPA ref: SPA-2026-0047. Penalty clause: 2% per month on overdue instalments beyond 14-day grace period.",
    },
    {
      title: "Main contractor progress payments — Structural works",
      description: "Quarterly progress-based payment plan for structural subcontract package covering piling, substructure, and superstructure up to Level 12. Valuations by QS on 25th of each quarter-end month.",
      plan_type: "milestone_based",
      direction: "payable",
      frequency: "quarterly",
      total_amount: "4200000",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: new Date(Date.now() + 540 * 86400000).toISOString().slice(0, 10),
      number_of_installments: "6",
      customer: "",
      vendor: "",
      investor: "",
      project: "",
      notes: "Retention: 5% held until practical completion + 12-month DLP. Performance bond: 10% of contract value. IPC to be submitted with supporting measurement sheets and site photographs.",
    },
    {
      title: "Investor equity drawdown — Phase 2 development",
      description: "Scheduled capital calls against committed equity for Phase 2 mixed-use development. Drawdowns triggered by construction progress thresholds verified by independent monitoring surveyor.",
      plan_type: "percentage_based",
      direction: "receivable",
      frequency: "quarterly",
      total_amount: "12500000",
      start_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      end_date: new Date(Date.now() + 730 * 86400000).toISOString().slice(0, 10),
      number_of_installments: "8",
      customer: "",
      vendor: "",
      investor: "",
      project: "",
      notes: "Drawdown tranches: 15% at foundation completion, 25% at structural topping-out, 25% at MEP first fix, 20% at practical completion, 15% at final account. 30-day call notice period.",
    },
  ];

  let paymentPlanDevIdx = 0;

  function devFillPaymentPlan() {
    const sample = PAYMENT_PLAN_SAMPLES[paymentPlanDevIdx % PAYMENT_PLAN_SAMPLES.length];
    paymentPlanDevIdx++;
    createForm = {
      ...sample,
      project: createForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
    };
  }

  // ---------------------------------------------------------------------------
  // List state
  // ---------------------------------------------------------------------------
  let search = $state("");
  let statusFilter = $state("");
  let directionFilter = $state("");
  let currentPage = $state(1);
  const pageSize = 25;

  let plans = $state<PaymentPlanListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let expandedPlanRowId = $state<number | null>(null);

  // ---------------------------------------------------------------------------
  // Create modal state
  // ---------------------------------------------------------------------------
  let showCreateModal = $state(false);
  let savingPlan = $state(false);
  let createErrors = $state<Record<string, string[]>>({});

  let createForm = $state({
    title: "",
    description: "",
    plan_type: "fixed_installment",
    direction: "receivable",
    frequency: "monthly",
    total_amount: "",
    start_date: "",
    end_date: "",
    number_of_installments: "",
    customer: "",
    vendor: "",
    investor: "",
    project: "",
    notes: "",
  });

  // Lookup data for the create modal
  let customers = $state<{ id: number; name: string }[]>([]);
  let vendors = $state<{ id: number; name: string }[]>([]);
  let investors = $state<{ id: number; name: string }[]>([]);
  let projects = $state<{ id: number; name: string }[]>([]);
  let lookupsLoaded = $state(false);

  // ---------------------------------------------------------------------------
  // Derived helpers
  // ---------------------------------------------------------------------------
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  // ---------------------------------------------------------------------------
  // Labels & badges
  // ---------------------------------------------------------------------------
  const planTypeLabels: Record<string, string> = {
    fixed_installment: "Fixed Installment",
    milestone_based: "Milestone Based",
    percentage_based: "Percentage Based",
    custom: "Custom",
  };

  const frequencyLabels: Record<string, string> = {
    weekly: "Weekly",
    biweekly: "Bi-weekly",
    monthly: "Monthly",
    quarterly: "Quarterly",
    semi_annual: "Semi-annual",
    annual: "Annual",
    one_time: "One-time",
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function fmtAmount(value: string): string {
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    return currency.format(num);
  }

  function fmtDate(dateStr: string): string {
    if (!dateStr) return "";
    return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function counterparty(plan: PaymentPlanListItem): string {
    if (plan.customer_name) return plan.customer_name;
    if (plan.vendor_name) return plan.vendor_name;
    if (plan.investor_name) return plan.investor_name;
    return "\u2014";
  }

  function progressPct(plan: PaymentPlanListItem): number {
    const total = parseFloat(plan.total_amount);
    const paid = parseFloat(plan.paid_amount);
    if (!total || total <= 0) return 0;
    return Math.min(100, Math.max(0, (paid / total) * 100));
  }

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function togglePlanRow(planId: number) {
    expandedPlanRowId = expandedPlanRowId === planId ? null : planId;
  }

  function resetCreateForm() {
    createForm = {
      title: "",
      description: "",
      plan_type: "fixed_installment",
      direction: "receivable",
      frequency: "monthly",
      total_amount: "",
      start_date: "",
      end_date: "",
      number_of_installments: "",
      customer: "",
      vendor: "",
      investor: "",
      project: "",
      notes: "",
    };
    createErrors = {};
  }

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  let debounceTimer: ReturnType<typeof setTimeout>;

  async function fetchPlans() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (directionFilter) params.direction = directionFilter;

      const res = await api.get<PaginatedResponse<PaymentPlanListItem>>(
        "/finance/payment-plans/",
        params,
      );
      plans = res.results;
      totalCount = res.count;
    } catch {
      plans = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchLookups() {
    if (lookupsLoaded) return;
    try {
      const [custRes, vendRes, invRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<{ id: number; name: string }>>("/finance/customers/", { page_size: "200" }),
        api.get<PaginatedResponse<{ id: number; name: string }>>("/procurement/vendors/", { page_size: "200" }),
        api.get<PaginatedResponse<{ id: number; name: string }>>("/finance/investors/", { page_size: "200" }),
        api.get<PaginatedResponse<{ id: number; name: string }>>("/projects/projects/", { page_size: "200" }),
      ]);
      customers = custRes.results;
      vendors = vendRes.results;
      investors = invRes.results;
      projects = projRes.results;
      lookupsLoaded = true;
    } catch {
      // Silently fail; selects will remain empty
    }
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------
  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchPlans();
    }, 300);
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchPlans();
  }

  function handleDirectionChange(value: string) {
    directionFilter = value;
    currentPage = 1;
    fetchPlans();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchPlans();
  }

  function openCreateModal() {
    showCreateModal = true;
    fetchLookups();
  }

  async function handleCreate(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingPlan = true;

    try {
      const payload: Record<string, unknown> = {
        title: createForm.title,
        description: createForm.description,
        plan_type: createForm.plan_type,
        direction: createForm.direction,
        frequency: createForm.frequency,
        total_amount: createForm.total_amount,
        currency: currency.config.code,
        start_date: createForm.start_date || null,
        end_date: createForm.end_date || null,
        number_of_installments: createForm.number_of_installments
          ? Number(createForm.number_of_installments)
          : null,
        notes: createForm.notes,
      };
      if (createForm.customer) payload.customer = Number(createForm.customer);
      if (createForm.vendor) payload.vendor = Number(createForm.vendor);
      if (createForm.investor) payload.investor = Number(createForm.investor);
      if (createForm.project) payload.project = Number(createForm.project);

      const result = await api.post<PaymentPlanListItem>("/finance/payment-plans/", payload);
      toast.success("Payment plan created", `"${result.title}" has been added`);
      showCreateModal = false;
      resetCreateForm();
      fetchPlans();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the payment plan");
      }
    } finally {
      savingPlan = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  $effect(() => {
    fetchPlans();
  });

  $effect(() => {
    if (expandedPlanRowId !== null && !plans.some((plan) => plan.id === expandedPlanRowId)) {
      expandedPlanRowId = null;
    }
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800">Payment Plans</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Manage installment schedules for receivables and payables
      </p>
    </div>
    <button
      onclick={openCreateModal}
      class="inline-flex items-center px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      + New Payment Plan
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Plan number or title..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Direction</span>
        <select
          value={directionFilter}
          onchange={(e) => handleDirectionChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">All Directions</option>
          <option value="receivable">Receivable</option>
          <option value="payable">Payable</option>
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if plans.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No payment plans found</p>
        <button
          onclick={openCreateModal}
          class="mt-3 text-sm font-medium text-neutral-800 hover:underline"
        >
          Create your first payment plan
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-3 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"> </th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Plan #</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Direction</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Paid</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Balance</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Counterparty</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Start Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each plans as plan (plan.id)}
              <tr
                class="hover:bg-neutral-50 transition-colors group"
              >
                <!-- Expand toggle -->
                <td class="px-3 py-4 align-top">
                  <button
                    type="button"
                    onclick={() => togglePlanRow(plan.id)}
                    class="inline-flex h-6 w-6 items-center justify-center rounded border border-neutral-200 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
                    aria-expanded={expandedPlanRowId === plan.id}
                    aria-label={expandedPlanRowId === plan.id ? "Collapse row details" : "Expand row details"}
                    title={expandedPlanRowId === plan.id ? "Collapse details" : "Expand details"}
                  >
                    <span class={`transition-transform ${expandedPlanRowId === plan.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>

                <!-- Plan # -->
                <td class="px-5 py-4 text-sm font-medium text-neutral-800">
                  <button
                    type="button"
                    onclick={() => goto(`/finance/payment-plans/${plan.id}`)}
                    class="hover:underline underline-offset-2"
                    title="Open payment plan"
                  >
                    {plan.plan_number}
                  </button>
                </td>

                <!-- Title + progress bar -->
                <td class="px-5 py-4">
                  <div class="text-sm text-neutral-800">{plan.title}</div>
                  <div class="mt-1.5 w-full h-1 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-neutral-800 rounded-full transition-all"
                      style="width: {progressPct(plan)}%"
                    ></div>
                  </div>
                </td>

                <!-- Direction -->
                <td class="px-5 py-4">
                  {#if plan.direction === "receivable"}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
                      </svg>
                      Receivable
                    </span>
                  {:else}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-200 text-neutral-600">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3" />
                      </svg>
                      Payable
                    </span>
                  {/if}
                </td>

                <!-- Status -->
                <td class="px-5 py-4">
                  <StatusBadge status={plan.status} />
                </td>

                <!-- Total -->
                <td class="px-5 py-4 text-sm text-neutral-800 text-right tabular-nums">
                  {fmtAmount(plan.total_amount)}
                </td>

                <!-- Paid -->
                <td class="px-5 py-4 text-sm text-neutral-500 text-right tabular-nums">
                  {fmtAmount(plan.paid_amount)}
                </td>

                <!-- Balance -->
                <td class="px-5 py-4 text-sm text-neutral-800 font-medium text-right tabular-nums">
                  {fmtAmount(plan.balance_due)}
                </td>

                <!-- Counterparty -->
                <td class="px-5 py-4 text-sm text-neutral-700">
                  {counterparty(plan)}
                </td>

                <!-- Start Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {fmtDate(plan.start_date)}
                </td>
              </tr>

              {#if expandedPlanRowId === plan.id}
                <tr>
                  <td colspan="10" class="px-5 pb-4 pt-0">
                    <div class="rounded-lg border border-neutral-200 bg-neutral-50/70 px-4 py-3">
                      <div class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Plan Type</p>
                          <p class="mt-1 text-neutral-800">{planTypeLabels[plan.plan_type] ?? plan.plan_type}</p>
                        </div>
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Frequency</p>
                          <p class="mt-1 text-neutral-800">{frequencyLabels[plan.frequency] ?? plan.frequency}</p>
                        </div>
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Installments</p>
                          <p class="mt-1 text-neutral-800">{plan.installment_count || plan.number_of_installments || 0}</p>
                        </div>
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Project</p>
                          <p class="mt-1 text-neutral-800">{plan.project_name || "\u2014"}</p>
                        </div>
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">SPV Entity</p>
                          <p class="mt-1 text-neutral-800">{plan.spv_name || "\u2014"}</p>
                        </div>
                        <div>
                          <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">End Date</p>
                          <p class="mt-1 text-neutral-800">{plan.end_date ? fmtDate(plan.end_date) : "\u2014"}</p>
                        </div>
                      </div>

                      <div class="mt-3 flex items-center justify-between border-t border-neutral-200 pt-3">
                        <p class="text-xs text-neutral-500">
                          Progress: {progressPct(plan).toFixed(1)}% paid
                        </p>
                        <button
                          type="button"
                          onclick={() => goto(`/finance/payment-plans/${plan.id}`)}
                          class="text-xs font-medium text-neutral-700 hover:text-neutral-800 hover:underline underline-offset-2"
                        >
                          Open full payment plan
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}&#8211;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-800 text-white border-neutral-800'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<!-- Create Payment Plan Modal -->
<Modal
  open={showCreateModal}
  onclose={() => { showCreateModal = false; resetCreateForm(); }}
  title="New Payment Plan"
  maxWidth="max-w-2xl"
>
  <form onsubmit={handleCreate} class="space-y-5">
    <!-- Title -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
      <input
        type="text"
        bind:value={createForm.title}
        placeholder="e.g. Q1 Office Lease Payments"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      />
      {#if createFieldError("title")}<p class="mt-1 text-xs text-red-500">{createFieldError("title")}</p>{/if}
    </label>

    <!-- Description -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea
        bind:value={createForm.description}
        rows="2"
        placeholder="Brief description of this payment plan..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      ></textarea>
      {#if createFieldError("description")}<p class="mt-1 text-xs text-red-500">{createFieldError("description")}</p>{/if}
    </label>

    <!-- Plan Type / Direction / Frequency -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Plan Type</span>
        <select
          bind:value={createForm.plan_type}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="fixed_installment">Fixed Installment</option>
          <option value="milestone_based">Milestone Based</option>
          <option value="percentage_based">Percentage Based</option>
          <option value="custom">Custom</option>
        </select>
        {#if createFieldError("plan_type")}<p class="mt-1 text-xs text-red-500">{createFieldError("plan_type")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Direction</span>
        <select
          bind:value={createForm.direction}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="receivable">Receivable</option>
          <option value="payable">Payable</option>
        </select>
        {#if createFieldError("direction")}<p class="mt-1 text-xs text-red-500">{createFieldError("direction")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Frequency</span>
        <select
          bind:value={createForm.frequency}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="weekly">Weekly</option>
          <option value="biweekly">Bi-weekly</option>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="semi_annual">Semi-annual</option>
          <option value="annual">Annual</option>
          <option value="one_time">One-time</option>
        </select>
        {#if createFieldError("frequency")}<p class="mt-1 text-xs text-red-500">{createFieldError("frequency")}</p>{/if}
      </label>
    </div>

    <!-- Total Amount / Currency / Installments -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Total Amount</span>
        <input
          type="text"
          bind:value={createForm.total_amount}
          placeholder="0.00"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
        {#if createFieldError("total_amount")}<p class="mt-1 text-xs text-red-500">{createFieldError("total_amount")}</p>{/if}
      </label>

      <div>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Currency</span>
        <p class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-neutral-50 text-neutral-700">
          {currency.config.code}
        </p>
      </div>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Installments</span>
        <input
          type="number"
          min="1"
          bind:value={createForm.number_of_installments}
          placeholder="e.g. 12"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
        {#if createFieldError("number_of_installments")}<p class="mt-1 text-xs text-red-500">{createFieldError("number_of_installments")}</p>{/if}
      </label>
    </div>

    <!-- Dates -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Start Date</span>
        <DateInput bind:value={createForm.start_date} />
        {#if createFieldError("start_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("start_date")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">End Date <span class="text-neutral-400 font-normal">(optional)</span></span>
        <DateInput bind:value={createForm.end_date} />
        {#if createFieldError("end_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("end_date")}</p>{/if}
      </label>
    </div>

    <!-- Counterparty selects -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Customer <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.customer}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">None</option>
          {#each customers as c}
            <option value={String(c.id)}>{c.name}</option>
          {/each}
        </select>
        {#if createFieldError("customer")}<p class="mt-1 text-xs text-red-500">{createFieldError("customer")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.vendor}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">None</option>
          {#each vendors as v}
            <option value={String(v.id)}>{v.name}</option>
          {/each}
        </select>
        {#if createFieldError("vendor")}<p class="mt-1 text-xs text-red-500">{createFieldError("vendor")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Investor <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.investor}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">None</option>
          {#each investors as inv}
            <option value={String(inv.id)}>{inv.name}</option>
          {/each}
        </select>
        {#if createFieldError("investor")}<p class="mt-1 text-xs text-red-500">{createFieldError("investor")}</p>{/if}
      </label>
    </div>

    <!-- Project -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400 font-normal">(optional)</span></span>
      <select
        bind:value={createForm.project}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">None</option>
        {#each projects as p}
          <option value={String(p.id)}>{p.name}</option>
        {/each}
      </select>
      {#if createFieldError("project")}<p class="mt-1 text-xs text-red-500">{createFieldError("project")}</p>{/if}
    </label>

    <!-- Notes -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea
        bind:value={createForm.notes}
        rows="2"
        placeholder="Additional notes..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      ></textarea>
      {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
    </label>

    <!-- Actions -->
    <div class="flex justify-end gap-3 pt-2">
      <button
        type="button"
        onclick={() => { showCreateModal = false; resetCreateForm(); }}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      {#if isDev}
        <button
          type="button"
          onclick={devFillPaymentPlan}
          class="px-4 py-2.5 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <button
        type="submit"
        disabled={savingPlan}
        class="inline-flex items-center px-5 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {#if savingPlan}
          <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
        {/if}
        {savingPlan ? "Creating..." : "Create Payment Plan"}
      </button>
    </div>
  </form>
</Modal>
