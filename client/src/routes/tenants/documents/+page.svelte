<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      documents_total: number;
      pending_signature: number;
      expired_documents: number;
      payment_receipts: number;
    };
    watchlist: DocumentRecord[];
  }

  interface DocumentRecord {
    id: number;
    tenant_name: string;
    title: string;
    category_display: string;
    status_display: string;
    reference_number: string;
    issue_date: string | null;
    expiry_date: string | null;
    is_signed: boolean;
  }

  interface LookupItem {
    id: number;
    label: string;
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);
  let showDrawer = $state(false);

  let overview = $state<Overview | null>(null);
  let documents = $state<DocumentRecord[]>([]);
  let tenantLookup = $state<LookupItem[]>([]);
  let leaseLookup = $state<LookupItem[]>([]);

  let form = $state({
    tenant_profile: "",
    lease_agreement: "",
    title: "",
    category: "lease_agreement",
    status: "active",
    reference_number: "",
    file_reference: "",
    issue_date: "",
    expiry_date: "",
    is_signed: false,
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillDocument() {
    const today = new Date().toISOString().slice(0, 10);
    const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const titles = ["Signed Lease Agreement — Unit 3A", "Tenant ID Verification (NIN)", "Utility Transfer Authorization", "Insurance Certificate of Occupancy", "Move-in Checklist (Signed)", "Security Deposit Receipt"];
    const categories = ["lease_agreement", "identification", "utility", "insurance", "checklist", "receipt"];
    const idx = Math.floor(Math.random() * titles.length);
    form.title = titles[idx];
    form.category = categories[idx % categories.length];
    form.status = "active";
    form.reference_number = `DOC-${Math.floor(Math.random() * 90000) + 10000}`;
    form.issue_date = today;
    form.expiry_date = nextYear;
    form.is_signed = Math.random() > 0.3;
    form.notes = "Original copy filed. Digital scan uploaded for reference.";
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function parseApiMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      if (typeof error.body?.detail === "string" && error.body.detail.trim()) return error.body.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ").trim();
      if (fieldMessage) return fieldMessage;
    }
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
  }

  async function loadData(showSpinner = true) {
    if (showSpinner) loading = true;
    try {
      const [overviewRes, documentRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/documents/overview/"),
        api.get<DocumentRecord[]>("/tenants/documents/records/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      documents = documentRes;
      tenantLookup = lookupsRes.tenants ?? [];
      leaseLookup = (lookupsRes.leases ?? []).map((item: any) => ({ id: item.id, label: item.label }));
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load tenant documents."));
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function refreshAll() {
    refreshing = true;
    await loadData(false);
  }

  async function runWorkflows() {
    syncing = true;
    try {
      const result = await api.post<Record<string, number>>("/tenants/documents/sync/", {});
      toast.success(
        "Document sync completed",
        `Created ${result.documents_created ?? 0}, expired ${result.documents_expired ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run document workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      tenant_profile: "",
      lease_agreement: "",
      title: "",
      category: "lease_agreement",
      status: "active",
      reference_number: "",
      file_reference: "",
      issue_date: "",
      expiry_date: "",
      is_signed: false,
      notes: "",
    };
    showDrawer = true;
  }

  async function saveDocument() {
    saving = true;
    try {
      await api.post("/tenants/documents/records/", {
        ...form,
        tenant_profile: Number(form.tenant_profile),
        lease_agreement: form.lease_agreement ? Number(form.lease_agreement) : null,
        issue_date: form.issue_date || null,
        expiry_date: form.expiry_date || null,
      });
      toast.success("Document saved", "Tenant contract / document record was added.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the document."));
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Documents & Contracts</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Lease agreements, signed documents, KYC, inspection reports, and payment receipts as the tenant source of truth.
      </p>
      {#if overview?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>{/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <!-- svelte-ignore a11y_consider_explicit_label -->
      <button onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50">
        <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" /></svg>
      </button>
      <button onclick={runWorkflows} disabled={syncing || loading} class="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{syncing ? "Running..." : "Run Workflows"}</button>
    </div>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <section class="rounded-2xl border border-violet-200/70 bg-linear-to-br from-violet-50 via-white to-fuchsia-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Documents</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.documents_total ?? 0}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Pending Signature</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.pending_signature ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Expired</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.expired_documents ?? 0}</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Receipts</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.payment_receipts ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading documents...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Document Register</p>
          <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Tenant contracts, receipts, and compliance records</h2>
        </div>
        <button onclick={openDrawer} class="rounded-xl bg-violet-500 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-600">Add Document</button>
      </div>
      <div class="overflow-x-auto rounded-2xl border border-neutral-200">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
            <tr>
              <th class="px-4 py-3 text-left">Title</th>
              <th class="px-4 py-3 text-left">Tenant</th>
              <th class="px-4 py-3 text-left">Category</th>
              <th class="px-4 py-3 text-left">Issue</th>
              <th class="px-4 py-3 text-left">Expiry</th>
              <th class="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each documents.slice(0, 14) as document}
              <tr class="transition hover:bg-neutral-50/80">
                <td class="px-4 py-3 font-semibold text-neutral-900">{document.title}</td>
                <td class="px-4 py-3 text-neutral-600">{document.tenant_name}</td>
                <td class="px-4 py-3 text-neutral-600">{document.category_display}</td>
                <td class="px-4 py-3 text-neutral-600">{fmtDate(document.issue_date)}</td>
                <td class="px-4 py-3 text-neutral-600">{fmtDate(document.expiry_date)}</td>
                <td class="px-4 py-3"><span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{document.status_display}</span></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

{#if showDrawer}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (showDrawer = false)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Tenant Documents</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Add Document</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Tenant</span><select bind:value={form.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select tenant</option>{#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Lease</span><select bind:value={form.lease_agreement} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select lease</option>{#each leaseLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Title</span><input bind:value={form.title} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Category</span><select bind:value={form.category} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="lease_agreement">Lease agreement</option><option value="id_kyc">ID / KYC</option><option value="payment_receipt">Payment receipt</option><option value="inspection_report">Inspection report</option><option value="signed_document">Signed document</option><option value="other">Other</option></select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Status</span><select bind:value={form.status} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="active">Active</option><option value="pending_signature">Pending signature</option><option value="expired">Expired</option><option value="archived">Archived</option></select></label>
      </div>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillDocument} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveDocument} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save Document"}</button>
    </div>
  </aside>
{/if}
