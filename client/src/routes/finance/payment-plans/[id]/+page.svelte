<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { PaymentPlan, PaymentInstallment, InstallmentStatus } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const id = $derived($page.params.id ?? "");

  let plan = $state<PaymentPlan | null>(null);
  let loading = $state(true);
  let editing = $state(false);
  let saving = $state(false);

  // Edit form for plan details
  let editForm = $state({
    title: "",
    description: "",
    notes: "",
  });

  // Installment modal
  let showInstallmentModal = $state(false);
  let editingInstallment = $state<PaymentInstallment | null>(null);
  let savingInstallment = $state(false);
  let installmentForm = $state({
    installment_number: "",
    label: "",
    amount: "",
    scheduled_date: "",
    due_date: "",
    percentage_of_total: "",
    notes: "",
  });

  // Record payment modal
  let showPaymentModal = $state(false);
  let paymentTargetInstallment = $state<PaymentInstallment | null>(null);
  let recordingPayment = $state(false);
  let paymentForm = $state({
    amount: "",
    payment_method: "bank_transfer",
    reference_number: "",
  });

  // Action loading states
  let approvingPlan = $state(false);
  let pausingPlan = $state(false);
  let activatingPlan = $state(false);

  // --- Status configuration ---

  const planStatusLabels: Record<string, string> = {
    draft: "Draft",
    active: "Active",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
  };

  const planStatusColors: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    active: "bg-neutral-900 text-white",
    paused: "bg-neutral-300 text-neutral-700",
    completed: "bg-neutral-800 text-white",
    cancelled: "bg-neutral-100 text-neutral-400",
  };

  const installmentStatusLabels: Record<InstallmentStatus, string> = {
    scheduled: "Scheduled",
    due: "Due",
    paid: "Paid",
    partially_paid: "Partially Paid",
    overdue: "Overdue",
    waived: "Waived",
    cancelled: "Cancelled",
  };

  const installmentStatusColors: Record<InstallmentStatus, string> = {
    scheduled: "bg-neutral-100 text-neutral-600",
    due: "bg-neutral-800 text-white",
    paid: "bg-neutral-900 text-white",
    partially_paid: "bg-neutral-300 text-neutral-700",
    overdue: "bg-neutral-700 text-neutral-100",
    waived: "bg-neutral-100 text-neutral-400",
    cancelled: "bg-neutral-50 text-neutral-400",
  };

  const planTypeLabels: Record<string, string> = {
    fixed_installment: "Fixed Installment",
    milestone_based: "Milestone Based",
    percentage_based: "Percentage Based",
    custom: "Custom",
  };

  const directionLabels: Record<string, string> = {
    receivable: "Receivable",
    payable: "Payable",
  };

  const frequencyLabels: Record<string, string> = {
    weekly: "Weekly",
    biweekly: "Biweekly",
    monthly: "Monthly",
    quarterly: "Quarterly",
    semi_annual: "Semi-Annual",
    annual: "Annual",
    one_time: "One Time",
  };

  const paymentMethodLabels: Record<string, string> = {
    bank_transfer: "Bank Transfer",
    check: "Check",
    cash: "Cash",
    credit_card: "Credit Card",
    other: "Other",
  };

  // --- Helpers ---

  function fmtDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtCurrency(amount: string | null): string {
    if (!amount) return "\u2014";
    return currency.format(parseFloat(amount));
  }

  function progressPercent(paid: string, total: string): number {
    const p = parseFloat(paid || "0");
    const t = parseFloat(total || "0");
    if (t === 0) return 0;
    return Math.min(Math.round((p / t) * 100), 100);
  }

  function counterpartyName(p: PaymentPlan): string {
    return p.customer_name || p.vendor_name || p.investor_name || "\u2014";
  }

  function counterpartyLabel(p: PaymentPlan): string {
    if (p.customer_name) return "Customer";
    if (p.vendor_name) return "Vendor";
    if (p.investor_name) return "Investor";
    return "Counterparty";
  }

  // --- Data fetching ---

  async function loadPlan() {
    loading = true;
    try {
      plan = await api.get<PaymentPlan>(`/finance/payment-plans/${id}/`);
      editForm = {
        title: plan.title,
        description: plan.description,
        notes: plan.notes,
      };
    } catch {
      plan = null;
    }
    loading = false;
  }

  $effect(() => {
    void id;
    loadPlan();
  });

  // --- Plan actions ---

  async function handleSavePlan() {
    if (!plan) return;
    saving = true;
    try {
      plan = await api.patch<PaymentPlan>(`/finance/payment-plans/${id}/`, {
        title: editForm.title,
        description: editForm.description,
        notes: editForm.notes,
      });
      editing = false;
      toast.success("Plan updated", "Changes have been saved");
    } catch {
      toast.error("Something went wrong", "Could not update the payment plan");
    }
    saving = false;
  }

  async function handleApprove() {
    approvingPlan = true;
    try {
      plan = await api.post<PaymentPlan>(`/finance/payment-plans/${id}/approve/`, {});
      toast.success("Plan approved", "Payment plan is now active");
    } catch {
      toast.error("Something went wrong", "Could not approve the payment plan");
    }
    approvingPlan = false;
  }

  async function handlePause() {
    pausingPlan = true;
    try {
      plan = await api.post<PaymentPlan>(`/finance/payment-plans/${id}/pause/`, {});
      toast.success("Plan paused", "Payment plan has been paused");
    } catch {
      toast.error("Something went wrong", "Could not pause the payment plan");
    }
    pausingPlan = false;
  }

  async function handleActivate() {
    activatingPlan = true;
    try {
      plan = await api.post<PaymentPlan>(`/finance/payment-plans/${id}/activate/`, {});
      toast.success("Plan activated", "Payment plan is now active");
    } catch {
      toast.error("Something went wrong", "Could not activate the payment plan");
    }
    activatingPlan = false;
  }

  // --- Installment CRUD ---

  function openAddInstallment() {
    editingInstallment = null;
    installmentForm = {
      installment_number: plan ? String(plan.installments.length + 1) : "1",
      label: "",
      amount: "",
      scheduled_date: "",
      due_date: "",
      percentage_of_total: "",
      notes: "",
    };
    showInstallmentModal = true;
  }

  function openEditInstallment(inst: PaymentInstallment) {
    editingInstallment = inst;
    installmentForm = {
      installment_number: String(inst.installment_number),
      label: inst.label,
      amount: inst.amount,
      scheduled_date: inst.scheduled_date,
      due_date: inst.due_date,
      percentage_of_total: inst.percentage_of_total ?? "",
      notes: inst.notes,
    };
    showInstallmentModal = true;
  }

  function closeInstallmentModal() {
    showInstallmentModal = false;
    editingInstallment = null;
  }

  async function handleSaveInstallment() {
    savingInstallment = true;
    const payload: Record<string, unknown> = {
      installment_number: Number(installmentForm.installment_number),
      label: installmentForm.label,
      amount: installmentForm.amount,
      scheduled_date: installmentForm.scheduled_date || null,
      due_date: installmentForm.due_date || null,
      percentage_of_total: installmentForm.percentage_of_total || null,
      notes: installmentForm.notes,
    };

    try {
      if (editingInstallment) {
        await api.patch(
          `/finance/payment-plans/${id}/installments/${editingInstallment.id}/`,
          payload,
        );
        toast.success("Installment updated", "Changes have been saved");
      } else {
        await api.post(`/finance/payment-plans/${id}/installments/`, payload);
        toast.success("Installment created", "New installment has been added");
      }
      closeInstallmentModal();
      await loadPlan();
    } catch {
      toast.error("Something went wrong", "Could not save the installment");
    }
    savingInstallment = false;
  }

  async function handleDeleteInstallment(instId: number) {
    if (!confirm("Are you sure you want to delete this installment?")) return;
    try {
      await api.delete(`/finance/payment-plans/${id}/installments/${instId}/`);
      toast.success("Installment deleted", "The installment has been removed");
      await loadPlan();
    } catch {
      toast.error("Something went wrong", "Could not delete the installment");
    }
  }

  // --- Record Payment ---

  function openRecordPayment(inst: PaymentInstallment) {
    paymentTargetInstallment = inst;
    paymentForm = {
      amount: inst.balance_due,
      payment_method: "bank_transfer",
      reference_number: "",
    };
    showPaymentModal = true;
  }

  function closePaymentModal() {
    showPaymentModal = false;
    paymentTargetInstallment = null;
  }

  async function handleRecordPayment() {
    if (!paymentTargetInstallment) return;
    recordingPayment = true;
    try {
      await api.post(
        `/finance/payment-plans/${id}/installments/${paymentTargetInstallment.id}/record_payment/`,
        {
          amount: paymentForm.amount,
          payment_method: paymentForm.payment_method || undefined,
          reference_number: paymentForm.reference_number || undefined,
        },
      );
      toast.success("Payment recorded", "The payment has been applied to this installment");
      closePaymentModal();
      await loadPlan();
    } catch {
      toast.error("Something went wrong", "Could not record the payment");
    }
    recordingPayment = false;
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !plan}
  <div class="text-center py-24">
    <p class="text-neutral-400">Payment plan not found.</p>
    <a href="/finance/payment-plans" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to payment plans</a>
  </div>
{:else}
  <div class="space-y-8">

    <!-- Breadcrumb -->
    <Breadcrumb items={[
      { label: "Finance", href: "/finance" },
      { label: "Payment Plans", href: "/finance/payment-plans" },
      { label: plan.plan_number },
    ]} />

    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
      <div class="min-w-0">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-neutral-900 truncate">{plan.plan_number}</h1>
          <span class="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium shrink-0 {planStatusColors[plan.status] ?? 'bg-neutral-100 text-neutral-600'}">
            {planStatusLabels[plan.status] ?? plan.status}
          </span>
        </div>
        {#if plan.title}
          <p class="mt-1 text-sm text-neutral-500">{plan.title}</p>
        {/if}
      </div>
      <div class="flex items-center gap-2 shrink-0">
        {#if plan.status === "draft"}
          <button
            type="button"
            onclick={handleApprove}
            disabled={approvingPlan}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {approvingPlan ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            onclick={handleActivate}
            disabled={activatingPlan}
            class="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 disabled:opacity-50 transition-colors"
          >
            {activatingPlan ? "Activating..." : "Activate"}
          </button>
        {/if}
        {#if plan.status === "active"}
          <button
            type="button"
            onclick={handlePause}
            disabled={pausingPlan}
            class="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 disabled:opacity-50 transition-colors"
          >
            {pausingPlan ? "Pausing..." : "Pause"}
          </button>
        {/if}
        {#if plan.status === "paused"}
          <button
            type="button"
            onclick={handleActivate}
            disabled={activatingPlan}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {activatingPlan ? "Activating..." : "Activate"}
          </button>
        {/if}
        <button
          type="button"
          onclick={() => {
            if (editing) {
              editForm = { title: plan!.title, description: plan!.description, notes: plan!.notes };
            }
            editing = !editing;
          }}
          class="px-4 py-2 border border-neutral-200 text-neutral-600 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors"
        >
          {editing ? "Cancel" : "Edit"}
        </button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Total Amount</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(plan.total_amount)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Paid Amount</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(plan.paid_amount)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Balance Due</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(plan.balance_due)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Progress</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{progressPercent(plan.paid_amount, plan.total_amount)}%</p>
        <div class="mt-2 w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-neutral-900 rounded-full transition-all duration-500"
            style="width: {progressPercent(plan.paid_amount, plan.total_amount)}%"
          ></div>
        </div>
      </div>
    </div>

    <!-- Plan Details -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Plan Details</h2>
        {#if editing}
          <button
            type="button"
            onclick={handleSavePlan}
            disabled={saving}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        {/if}
      </div>

      {#if editing}
        <!-- Editable fields -->
        <div class="space-y-5 mb-6">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
            <input
              type="text"
              bind:value={editForm.title}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
            <textarea
              bind:value={editForm.description}
              rows={3}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Plan description..."
            ></textarea>
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
            <textarea
              bind:value={editForm.notes}
              rows={3}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Internal notes..."
            ></textarea>
          </label>
        </div>
        <div class="border-t border-neutral-100 pt-6"></div>
      {/if}

      <div class="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-5">
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Direction</p>
          <p class="mt-1 text-sm text-neutral-900">{directionLabels[plan.direction] ?? plan.direction}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Plan Type</p>
          <p class="mt-1 text-sm text-neutral-900">{planTypeLabels[plan.plan_type] ?? plan.plan_type}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Frequency</p>
          <p class="mt-1 text-sm text-neutral-900">{frequencyLabels[plan.frequency] ?? plan.frequency}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Currency</p>
          <p class="mt-1 text-sm text-neutral-900">{currency.config.code}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Start Date</p>
          <p class="mt-1 text-sm text-neutral-900">{fmtDate(plan.start_date)}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">End Date</p>
          <p class="mt-1 text-sm text-neutral-900">{fmtDate(plan.end_date)}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Number of Installments</p>
          <p class="mt-1 text-sm text-neutral-900">{plan.number_of_installments}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">{counterpartyLabel(plan)}</p>
          <p class="mt-1 text-sm text-neutral-900">{counterpartyName(plan)}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Project</p>
          <p class="mt-1 text-sm text-neutral-900">{plan.project_name ?? "\u2014"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">SPV Entity</p>
          <p class="mt-1 text-sm text-neutral-900">{plan.spv_name ?? "\u2014"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Created By</p>
          <p class="mt-1 text-sm text-neutral-900">{plan.created_by_name ?? "\u2014"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Approved By</p>
          <p class="mt-1 text-sm text-neutral-900">
            {plan.approved_by_name ?? "\u2014"}
            {#if plan.approved_at}
              <span class="text-neutral-400 text-xs ml-1">on {fmtDate(plan.approved_at.split("T")[0])}</span>
            {/if}
          </p>
        </div>
        {#if !editing && (plan.description || plan.notes)}
          {#if plan.description}
            <div class="md:col-span-2">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Description</p>
              <p class="mt-1 text-sm text-neutral-700 whitespace-pre-line">{plan.description}</p>
            </div>
          {/if}
          {#if plan.notes}
            <div class="md:col-span-2">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Notes</p>
              <p class="mt-1 text-sm text-neutral-700 whitespace-pre-line">{plan.notes}</p>
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <!-- Installments Table -->
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-6 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Installments</h2>
        <button
          type="button"
          onclick={openAddInstallment}
          class="px-3.5 py-2 bg-neutral-900 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 transition-colors"
        >
          + Add Installment
        </button>
      </div>

      {#if plan.installments.length > 0}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-3 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">#</th>
                <th class="px-5 py-3 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Label</th>
                <th class="px-5 py-3 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Amount</th>
                <th class="px-5 py-3 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Paid</th>
                <th class="px-5 py-3 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Balance</th>
                <th class="px-5 py-3 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Scheduled</th>
                <th class="px-5 py-3 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Due</th>
                <th class="px-5 py-3 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each plan.installments as inst}
                <tr class="hover:bg-neutral-50/60 transition-colors">
                  <td class="px-5 py-3.5 text-xs text-neutral-500 tabular-nums">{inst.installment_number}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-900 font-medium">
                    <button
                      type="button"
                      onclick={() => openEditInstallment(inst)}
                      class="hover:underline text-left"
                    >
                      {inst.label || `Installment ${inst.installment_number}`}
                    </button>
                  </td>
                  <td class="px-5 py-3.5 text-xs text-neutral-900 tabular-nums text-right">{fmtCurrency(inst.amount)}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-500 tabular-nums text-right">{fmtCurrency(inst.paid_amount)}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-900 tabular-nums text-right font-medium">{fmtCurrency(inst.balance_due)}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-500">{fmtDate(inst.scheduled_date)}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-500">{fmtDate(inst.due_date)}</td>
                  <td class="px-5 py-3.5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium {installmentStatusColors[inst.status] ?? 'bg-neutral-100 text-neutral-600'}">
                      {installmentStatusLabels[inst.status] ?? inst.status}
                    </span>
                  </td>
                  <td class="px-5 py-3.5 text-right">
                    <div class="flex items-center justify-end gap-2">
                      {#if inst.status !== "paid" && inst.status !== "waived" && inst.status !== "cancelled"}
                        <button
                          type="button"
                          onclick={() => openRecordPayment(inst)}
                          class="text-[11px] font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 px-2.5 py-1 rounded-md transition-colors"
                        >
                          Record Payment
                        </button>
                      {/if}
                      <button
                        type="button"
                        onclick={() => handleDeleteInstallment(inst.id)}
                        class="text-[11px] text-neutral-400 hover:text-neutral-700 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="px-6 py-12 text-center">
          <p class="text-sm text-neutral-400">No installments yet.</p>
          <p class="text-xs text-neutral-300 mt-1">Add an installment to get started.</p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Add/Edit Installment Modal -->
  {#if showInstallmentModal}
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <button
        type="button"
        class="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onclick={closeInstallmentModal}
        aria-label="Close modal"
      ></button>
      <!-- Modal content -->
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-2xl w-full max-w-lg mx-4 p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-neutral-900">
            {editingInstallment ? "Edit Installment" : "Add Installment"}
          </h3>
          <button
            type="button"
            onclick={closeInstallmentModal}
            class="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Close"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Installment #</span>
              <input
                type="number"
                min="1"
                bind:value={installmentForm.installment_number}
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
              />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Label</span>
              <input
                type="text"
                bind:value={installmentForm.label}
                placeholder="e.g. Down Payment"
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
            </label>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Amount</span>
              <input
                type="text"
                bind:value={installmentForm.amount}
                placeholder="0.00"
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
              />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">% of Total <span class="text-neutral-400 font-normal">(optional)</span></span>
              <input
                type="text"
                bind:value={installmentForm.percentage_of_total}
                placeholder="e.g. 25.00"
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
              />
            </label>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Scheduled Date</span>
              <DateInput bind:value={installmentForm.scheduled_date} />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Due Date</span>
              <DateInput bind:value={installmentForm.due_date} />
            </label>
          </div>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
            <textarea
              bind:value={installmentForm.notes}
              rows={2}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Any additional notes..."
            ></textarea>
          </label>
        </div>

        <div class="flex items-center justify-end gap-3 mt-6 pt-5 border-t border-neutral-100">
          <button
            type="button"
            onclick={closeInstallmentModal}
            class="px-4 py-2.5 border border-neutral-200 text-neutral-600 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onclick={handleSaveInstallment}
            disabled={savingInstallment}
            class="px-5 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {#if savingInstallment}
              <div class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2 align-middle"></div>
            {/if}
            {editingInstallment ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Record Payment Modal -->
  {#if showPaymentModal && paymentTargetInstallment}
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <button
        type="button"
        class="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onclick={closePaymentModal}
        aria-label="Close modal"
      ></button>
      <!-- Modal content -->
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-2xl w-full max-w-md mx-4 p-6">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h3 class="text-lg font-semibold text-neutral-900">Record Payment</h3>
            <p class="text-xs text-neutral-400 mt-0.5">
              {paymentTargetInstallment.label || `Installment ${paymentTargetInstallment.installment_number}`}
              &mdash; Balance: {fmtCurrency(paymentTargetInstallment.balance_due)}
            </p>
          </div>
          <button
            type="button"
            onclick={closePaymentModal}
            class="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Close"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="space-y-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Amount <span class="text-neutral-900">*</span></span>
            <input
              type="text"
              bind:value={paymentForm.amount}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Method</span>
            <select
              bind:value={paymentForm.payment_method}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="bank_transfer">Bank Transfer</option>
              <option value="check">Check</option>
              <option value="cash">Cash</option>
              <option value="credit_card">Credit Card</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Reference Number <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              type="text"
              bind:value={paymentForm.reference_number}
              placeholder="e.g. TXN-123456"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </label>
        </div>

        <div class="flex items-center justify-end gap-3 mt-6 pt-5 border-t border-neutral-100">
          <button
            type="button"
            onclick={closePaymentModal}
            class="px-4 py-2.5 border border-neutral-200 text-neutral-600 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onclick={handleRecordPayment}
            disabled={recordingPayment || !paymentForm.amount}
            class="px-5 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {#if recordingPayment}
              <div class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2 align-middle"></div>
            {/if}
            Record Payment
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}
