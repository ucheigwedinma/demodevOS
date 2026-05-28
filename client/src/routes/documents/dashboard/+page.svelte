<script lang="ts">
  import { api } from "$lib/api";
  import DocumentKpiCard from "$lib/components/documents/DocumentKpiCard.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    DocumentExpiryRecord,
    DocumentRecord,
    PaginatedResponse,
    ProjectVariationOrder,
  } from "$lib/types";

  type ClientCompletenessRow = {
    clientId: number;
    clientName: string;
    missing: string[];
    linkedDocuments: number;
  };

  let loading = $state(true);

  let expiring30Count = $state(0);
  let expiring60Count = $state(0);
  let expiring90Count = $state(0);
  let permitsAtRiskCount = $state(0);
  let drawingsAwaitingApprovalCount = $state(0);
  let contractsWithoutInsuranceCount = $state(0);
  let clientDocumentsIncompleteCount = $state(0);
  let highValueVariationPendingCount = $state(0);

  let upcomingExpiries = $state<DocumentExpiryRecord[]>([]);
  let permitsAtRisk = $state<DocumentExpiryRecord[]>([]);
  let drawingsAwaitingApproval = $state<DocumentRecord[]>([]);
  let contractsWithoutInsurance = $state<DocumentRecord[]>([]);
  let highValueVariationPending = $state<ProjectVariationOrder[]>([]);
  let clientDocumentsIncomplete = $state<ClientCompletenessRow[]>([]);

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 50,
  ): Promise<T[]> {
    const results: T[] = [];
    let page = 1;
    let total = 0;

    while (page <= maxPages) {
      const response = await api.get<PaginatedResponse<T>>(endpoint, {
        ...params,
        page: String(page),
      });

      total = response.count;
      results.push(...response.results);

      if (!response.next || response.results.length === 0 || results.length >= total) {
        break;
      }
      page += 1;
    }

    return results;
  }

  function daysToExpiry(value: string): number {
    const now = new Date();
    const expiryDate = new Date(value);
    return Math.ceil((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function triggerLabel(value: string): string {
    return {
      building_permit: "Building Permit",
      insurance: "Insurance",
      performance_bond: "Performance Bond",
      eia_renewal: "EIA Renewal",
      warranty_end: "Warranty End",
    }[value] ?? value;
  }

  function normalize(value: string | null | undefined): string {
    return (value ?? "").toLowerCase();
  }

  function documentText(doc: DocumentRecord): string {
    return `${normalize(doc.document_type_name)} ${normalize(doc.title)}`;
  }

  function isVariationOrderText(text: string): boolean {
    return text.includes("variation order") || (text.includes("variation") && text.includes("order"));
  }

  function isDrawingDocument(doc: DocumentRecord): boolean {
    if (doc.category !== "DES") return false;
    const text = documentText(doc);
    return text.includes("drawing");
  }

  function isContractDocument(doc: DocumentRecord): boolean {
    const text = documentText(doc);
    return text.includes("contract") && !isVariationOrderText(text);
  }

  function isInsuranceDocument(doc: DocumentRecord): boolean {
    const text = documentText(doc);
    return text.includes("insurance");
  }

  function isPendingApprovalStatus(status: DocumentRecord["status"]): boolean {
    return status === "submitted" || status === "under_review";
  }

  function isActiveDocumentStatus(status: DocumentRecord["status"]): boolean {
    return status !== "archived" && status !== "superseded";
  }

  function contractValue(record: { contract_value: string | null }): number {
    const value = Number.parseFloat(record.contract_value ?? "0");
    return Number.isFinite(value) ? value : 0;
  }

  function uniqueById(records: DocumentRecord[]): DocumentRecord[] {
    const map = new Map<number, DocumentRecord>();
    for (const record of records) {
      map.set(record.id, record);
    }
    return Array.from(map.values());
  }

  function hasInsuranceCoverage(contractDoc: DocumentRecord, insuranceDocs: DocumentRecord[]): boolean {
    if (!contractDoc.vendor && !contractDoc.project) {
      return false;
    }

    return insuranceDocs.some((insuranceDoc) => {
      if (contractDoc.vendor && contractDoc.project) {
        return insuranceDoc.vendor === contractDoc.vendor && insuranceDoc.project === contractDoc.project;
      }
      if (contractDoc.vendor) {
        return insuranceDoc.vendor === contractDoc.vendor;
      }
      if (contractDoc.project) {
        return insuranceDoc.project === contractDoc.project;
      }
      return false;
    });
  }

  function buildClientCompletenessRows(salesDocs: DocumentRecord[]): ClientCompletenessRow[] {
    const byClient = new Map<
      number,
      {
        clientName: string;
        hasOfferLetter: boolean;
        hasSalesAgreement: boolean;
        hasHandoverPack: boolean;
        linkedDocuments: number;
      }
    >();

    for (const doc of salesDocs) {
      if (!doc.client) continue;

      const existing = byClient.get(doc.client) ?? {
        clientName: doc.client_name ?? `Client #${doc.client}`,
        hasOfferLetter: false,
        hasSalesAgreement: false,
        hasHandoverPack: false,
        linkedDocuments: 0,
      };

      const text = documentText(doc);
      if (text.includes("offer")) existing.hasOfferLetter = true;
      if (text.includes("sales agreement") || text.includes("sale") || text.includes("spa")) {
        existing.hasSalesAgreement = true;
      }
      if (text.includes("handover")) existing.hasHandoverPack = true;

      existing.linkedDocuments += 1;
      byClient.set(doc.client, existing);
    }

    const rows: ClientCompletenessRow[] = [];
    for (const [clientId, state] of byClient.entries()) {
      const missing: string[] = [];
      if (!state.hasOfferLetter) missing.push("Offer Letter");
      if (!state.hasSalesAgreement) missing.push("Sales Agreement");
      if (!state.hasHandoverPack) missing.push("Handover Pack");

      if (missing.length > 0) {
        rows.push({
          clientId,
          clientName: state.clientName,
          missing,
          linkedDocuments: state.linkedDocuments,
        });
      }
    }

    rows.sort((a, b) => {
      if (b.missing.length !== a.missing.length) return b.missing.length - a.missing.length;
      return a.clientName.localeCompare(b.clientName);
    });

    return rows;
  }

  async function loadDashboard() {
    loading = true;
    try {
      const [
        allExpiries,
        allConstructionDocs,
        allDesignDocs,
        allSalesDocs,
        allVariationOrders,
      ] = await Promise.all([
        fetchAllPages<DocumentExpiryRecord>("/documents/control/expiries/", {
          ordering: "expiry_date",
        }),
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "CON",
          ordering: "-created_at",
        }),
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "DES",
          ordering: "-created_at",
        }),
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "SAL",
          ordering: "-created_at",
        }),
        fetchAllPages<ProjectVariationOrder>("/projects/variations/", {
          ordering: "-contract_value",
        }),
      ]);

      expiring30Count = 0;
      expiring60Count = 0;
      expiring90Count = 0;

      upcomingExpiries = allExpiries
        .map((item) => ({ item, days: daysToExpiry(item.expiry_date) }))
        .filter(({ days }) => days >= 0 && days <= 90)
        .sort((a, b) => a.days - b.days)
        .slice(0, 10)
        .map(({ item }) => item);

      for (const expiry of allExpiries) {
        const days = daysToExpiry(expiry.expiry_date);
        if (days < 0 || days > 90) continue;
        if (days <= 30) {
          expiring30Count += 1;
        } else if (days <= 60) {
          expiring60Count += 1;
        } else {
          expiring90Count += 1;
        }
      }

      permitsAtRisk = allExpiries
        .map((item) => ({ item, days: daysToExpiry(item.expiry_date) }))
        .filter(
          ({ item, days }) =>
            (item.trigger_category === "building_permit" || item.trigger_category === "eia_renewal")
            && days <= 30,
        )
        .sort((a, b) => a.days - b.days)
        .slice(0, 10)
        .map(({ item }) => item);
      permitsAtRiskCount = allExpiries.filter((item) => {
        const days = daysToExpiry(item.expiry_date);
        const isPermitType = item.trigger_category === "building_permit" || item.trigger_category === "eia_renewal";
        return isPermitType && days <= 30;
      }).length;

      const pendingDrawings = allDesignDocs.filter(
        (doc) => isPendingApprovalStatus(doc.status) && isDrawingDocument(doc),
      );
      drawingsAwaitingApprovalCount = pendingDrawings.length;
      drawingsAwaitingApproval = pendingDrawings.slice(0, 10);

      const insuranceExpiryDocumentIds = new Set(
        allExpiries
          .filter((expiry) => expiry.trigger_category === "insurance")
          .map((expiry) => expiry.document),
      );

      const activeConstructionDocs = allConstructionDocs.filter((doc) => isActiveDocumentStatus(doc.status));

      const insuranceArtifacts = uniqueById([
        ...activeConstructionDocs.filter((doc) => isInsuranceDocument(doc)),
        ...activeConstructionDocs.filter((doc) => insuranceExpiryDocumentIds.has(doc.id)),
      ]);

      const contractCandidates = activeConstructionDocs.filter((doc) => isContractDocument(doc));
      const missingInsurance = contractCandidates
        .filter((doc) => !hasInsuranceCoverage(doc, insuranceArtifacts))
        .sort((a, b) => contractValue(b) - contractValue(a));

      contractsWithoutInsuranceCount = missingInsurance.length;
      contractsWithoutInsurance = missingInsurance.slice(0, 10);

      const pendingHighValueVariationOrders = allVariationOrders
        .filter(
          (variation) => isPendingApprovalStatus(variation.status)
            && contractValue(variation) >= 100000,
        )
        .sort((a, b) => contractValue(b) - contractValue(a));

      highValueVariationPendingCount = pendingHighValueVariationOrders.length;
      highValueVariationPending = pendingHighValueVariationOrders.slice(0, 10);

      const incompleteClientRows = buildClientCompletenessRows(
        allSalesDocs.filter((doc) => isActiveDocumentStatus(doc.status)),
      );
      clientDocumentsIncompleteCount = incompleteClientRows.length;
      clientDocumentsIncomplete = incompleteClientRows.slice(0, 12);
    } catch {
      expiring30Count = 0;
      expiring60Count = 0;
      expiring90Count = 0;
      permitsAtRiskCount = 0;
      drawingsAwaitingApprovalCount = 0;
      contractsWithoutInsuranceCount = 0;
      clientDocumentsIncompleteCount = 0;
      highValueVariationPendingCount = 0;

      upcomingExpiries = [];
      permitsAtRisk = [];
      drawingsAwaitingApproval = [];
      contractsWithoutInsurance = [];
      clientDocumentsIncomplete = [];
      highValueVariationPending = [];
    }

    loading = false;
  }

  $effect(() => {
    void loadDashboard();
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Document Governance Dashboard</h1>
      <p class="mt-1 text-sm text-neutral-500">Risk and control indicators for the centralized repository.</p>
    </div>
    <a
      href="/documents/repository"
      class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
    >
      Open Repository
    </a>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else}
    <div class="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
      <DocumentKpiCard title="Expiring ≤30 Days" value={String(expiring30Count)} accent="red" />
      <DocumentKpiCard title="Expiring 31-60 Days" value={String(expiring60Count)} accent="amber" />
      <DocumentKpiCard title="Expiring 61-90 Days" value={String(expiring90Count)} accent="blue" />
      <DocumentKpiCard title="Permits At Risk" value={String(permitsAtRiskCount)} subtitle="Building Permit + EIA <=30 days" accent="red" />
      <DocumentKpiCard title="Drawings Awaiting Approval" value={String(drawingsAwaitingApprovalCount)} accent="blue" />
      <DocumentKpiCard title="Contracts Without Insurance" value={String(contractsWithoutInsuranceCount)} accent="amber" />
      <DocumentKpiCard title="Client Docs Incomplete" value={String(clientDocumentsIncompleteCount)} accent="amber" />
      <DocumentKpiCard title="High-Value VO Pending" value={String(highValueVariationPendingCount)} subtitle="Variation orders >= 100k" accent="red" />
    </div>

    <div class="grid xl:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Documents Expiring in 30/60/90 Days</h3>
            <p class="mt-1 text-xs text-neutral-500">All tracked expiries due within the next 90 days.</p>
          </div>
          <a href="/documents/repository" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View all</a>
        </div>
        {#if upcomingExpiries.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">No documents expiring within 90 days.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Document</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Trigger</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Expiry</th>
                <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Days</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each upcomingExpiries as expiry}
                <tr>
                  <td class="px-5 py-3.5">
                    <a href={`/documents/${expiry.document}`} class="font-medium text-neutral-900 hover:underline">{expiry.document_number}</a>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600">{triggerLabel(expiry.trigger_category)}</td>
                  <td class="px-5 py-3.5 text-neutral-500">{fmtDate(expiry.expiry_date)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums text-neutral-900">{daysToExpiry(expiry.expiry_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Permits At Risk</h3>
            <p class="mt-1 text-xs text-neutral-500">Building permit and EIA records due or overdue in 30 days.</p>
          </div>
          <a href="/documents/repository?category=REG" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View all</a>
        </div>
        {#if permitsAtRisk.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">No permits currently at risk.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Document</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Type</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Expiry</th>
                <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Days</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each permitsAtRisk as permit}
                <tr>
                  <td class="px-5 py-3.5">
                    <a href={`/documents/${permit.document}`} class="font-medium text-neutral-900 hover:underline">{permit.document_number}</a>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600">{triggerLabel(permit.trigger_category)}</td>
                  <td class="px-5 py-3.5 text-neutral-500">{fmtDate(permit.expiry_date)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums text-neutral-900">{daysToExpiry(permit.expiry_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>

    <div class="grid xl:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Drawings Awaiting Approval</h3>
            <p class="mt-1 text-xs text-neutral-500">Design drawings in submitted or under-review status.</p>
          </div>
          <a href="/documents/repository?category=DES&status=under_review" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View list</a>
        </div>
        {#if drawingsAwaitingApproval.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">No drawings are awaiting approval.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Document</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Project</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each drawingsAwaitingApproval as doc}
                <tr>
                  <td class="px-5 py-3.5">
                    <a href={`/documents/${doc.id}`} class="font-medium text-neutral-900 hover:underline">{doc.document_number}</a>
                    <p class="mt-0.5 text-xs text-neutral-500 truncate max-w-[260px]">{doc.title}</p>
                  </td>
                  <td class="px-5 py-3.5"><StatusBadge status={doc.status} size="sm" /></td>
                  <td class="px-5 py-3.5 text-neutral-500">{doc.project_name ?? "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">High-Value Variation Orders Pending</h3>
            <p class="mt-1 text-xs text-neutral-500">Variation orders >= 100,000 pending approval workflow.</p>
          </div>
          <a href="/projects/variations" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View list</a>
        </div>
        {#if highValueVariationPending.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">No high-value variation orders pending approval.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Variation Order</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Value</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each highValueVariationPending as variation}
                <tr>
                  <td class="px-5 py-3.5">
                    <p class="font-medium text-neutral-900">{variation.variation_number}</p>
                    <p class="mt-0.5 text-xs text-neutral-500 truncate max-w-[260px]">{variation.title}</p>
                  </td>
                  <td class="px-5 py-3.5"><StatusBadge status={variation.status} size="sm" /></td>
                  <td class="px-5 py-3.5 text-right tabular-nums font-medium text-neutral-900">
                    {contractValue(variation).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>

    <div class="grid xl:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Contracts Without Insurance Attachments</h3>
            <p class="mt-1 text-xs text-neutral-500">Active contracts with no matching insurance document by project/vendor scope.</p>
          </div>
          <a href="/documents/repository?category=CON" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View list</a>
        </div>
        {#if contractsWithoutInsurance.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">All tracked contracts have insurance coverage attachments.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Document</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Vendor</th>
                <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Value</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each contractsWithoutInsurance as doc}
                <tr>
                  <td class="px-5 py-3.5">
                    <a href={`/documents/${doc.id}`} class="font-medium text-neutral-900 hover:underline">{doc.document_number}</a>
                    <p class="mt-0.5 text-xs text-neutral-500 truncate max-w-[260px]">{doc.title}</p>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-500">{doc.vendor_name ?? "--"}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums font-medium text-neutral-900">
                    {contractValue(doc).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Client Documents Incomplete</h3>
            <p class="mt-1 text-xs text-neutral-500">Missing Offer Letter, Sales Agreement, or Handover Pack.</p>
          </div>
          <a href="/documents/repository?category=SAL" class="text-xs font-medium text-neutral-500 hover:text-neutral-900">View list</a>
        </div>
        {#if clientDocumentsIncomplete.length === 0}
          <div class="py-14 text-center">
            <p class="text-sm text-neutral-400">No incomplete client document sets detected.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Client</th>
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Missing</th>
                <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Docs</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each clientDocumentsIncomplete as row}
                <tr>
                  <td class="px-5 py-3.5">
                    <a href={`/documents/repository?category=SAL&client=${row.clientId}`} class="font-medium text-neutral-900 hover:underline">{row.clientName}</a>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-500">{row.missing.join(", ")}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums text-neutral-900">{row.linkedDocuments}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  {/if}
</div>
