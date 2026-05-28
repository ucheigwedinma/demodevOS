<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    OnboardingTemplateDocumentRequirement,
    PartnerIntakeReviewStatus,
    PartnerIntakeSourceChannel,
    PartnerOnboardingCaseDetail,
    PartnerOnboardingCaseListItem,
    PartnerOnboardingIntakeDocument,
  } from "$lib/types";

  type RequirementState = {
    requirement: OnboardingTemplateDocumentRequirement;
    approved: boolean;
    current_status: PartnerIntakeReviewStatus | "missing";
    latest_document: PartnerOnboardingIntakeDocument | null;
  };

  const sourceOptions: Array<{ value: PartnerIntakeSourceChannel; label: string }> = [
    { value: "physical_scan", label: "Physical Submission (Scanned)" },
    { value: "email", label: "Email" },
    { value: "secure_upload_link", label: "Secure Upload Link" },
    { value: "tender_portal", label: "Tender Portal" },
    { value: "data_room", label: "Data Room" },
    { value: "internal_generated", label: "Internal Generated" },
    { value: "other", label: "Other" },
  ];

  const reviewActions: Array<{ value: PartnerIntakeReviewStatus; label: string; tone: string }> = [
    { value: "under_review", label: "Mark Review", tone: "border-amber-200 text-amber-700 hover:bg-amber-50" },
    { value: "approved", label: "Approve", tone: "border-emerald-200 text-emerald-700 hover:bg-emerald-50" },
    { value: "rejected", label: "Reject", tone: "border-rose-200 text-rose-700 hover:bg-rose-50" },
    { value: "waived", label: "Waive", tone: "border-neutral-200 text-neutral-700 hover:bg-neutral-100" },
  ];

  let loading = $state(true);
  let saving = $state(false);
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let selectedCaseId = $state("");
  let selectedCaseDetail = $state<PartnerOnboardingCaseDetail | null>(null);

  let form = $state({
    requirement: "",
    document_name: "",
    document_code: "",
    source_channel: "secure_upload_link" as PartnerIntakeSourceChannel,
    external_reference_url: "",
    external_reference_number: "",
    status: "received" as PartnerIntakeReviewStatus,
    review_notes: "",
    file: null as File | null,
  });

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 30,
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (page <= maxPages) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });
      if (Array.isArray(payload)) {
        rows.push(...payload);
        break;
      }
      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  async function loadCases() {
    cases = await fetchAllPages<PartnerOnboardingCaseListItem>("/partners/cases/", {
      ordering: "-created_at",
      page_size: "200",
    });
  }

  async function loadCaseDetail(caseId: number) {
    selectedCaseDetail = await api.get<PartnerOnboardingCaseDetail>(`/partners/cases/${caseId}/`);
  }

  async function loadData() {
    loading = true;
    try {
      await loadCases();
      if (!selectedCaseId && cases.length > 0) {
        selectedCaseId = String(cases[0].id);
      }
      const caseId = Number.parseInt(selectedCaseId, 10);
      if (!Number.isNaN(caseId)) {
        await loadCaseDetail(caseId);
      } else {
        selectedCaseDetail = null;
      }
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load onboarding intake data."));
    } finally {
      loading = false;
    }
  }

  async function onCaseChange(value: string) {
    selectedCaseId = value;
    const caseId = Number.parseInt(value, 10);
    if (Number.isNaN(caseId)) {
      selectedCaseDetail = null;
      return;
    }

    try {
      await loadCaseDetail(caseId);
      resetForm();
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load case intake details."));
    }
  }

  function resetForm() {
    form = {
      requirement: "",
      document_name: "",
      document_code: "",
      source_channel: "secure_upload_link",
      external_reference_url: "",
      external_reference_number: "",
      status: "received",
      review_notes: "",
      file: null,
    };
  }

  function setFormRequirement(requirementId: string) {
    form.requirement = requirementId;
    const requirement = selectedCaseDetail?.required_documents.find((row) => row.id === Number.parseInt(requirementId, 10));
    if (!requirement) return;

    form.document_code = requirement.code;
    form.document_name = requirement.name;
  }

  async function createIntakeDocument(event: Event) {
    event.preventDefault();
    const caseId = Number.parseInt(selectedCaseId, 10);
    if (Number.isNaN(caseId)) {
      toast.error("Case required", "Select an onboarding case first.");
      return;
    }

    const formData = new FormData();
    if (form.requirement) formData.append("requirement", form.requirement);
    if (form.document_code.trim()) formData.append("document_code", form.document_code.trim());
    if (form.document_name.trim()) formData.append("document_name", form.document_name.trim());
    formData.append("source_channel", form.source_channel);
    formData.append("status", form.status);
    if (form.external_reference_url.trim()) formData.append("external_reference_url", form.external_reference_url.trim());
    if (form.external_reference_number.trim()) formData.append("external_reference_number", form.external_reference_number.trim());
    if (form.review_notes.trim()) formData.append("review_notes", form.review_notes.trim());
    if (form.file) formData.append("file", form.file);

    saving = true;
    try {
      await api.upload(`/partners/cases/${caseId}/intake-documents/`, formData);
      toast.success("Document logged", "Onboarding intake document saved.");
      resetForm();
      await Promise.all([loadCases(), loadCaseDetail(caseId)]);
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save intake document."));
    } finally {
      saving = false;
    }
  }

  async function updateDocumentStatus(documentId: number, statusValue: PartnerIntakeReviewStatus) {
    try {
      await api.patch(`/partners/intake-documents/${documentId}/`, {
        status: statusValue,
      });
      const caseId = Number.parseInt(selectedCaseId, 10);
      if (!Number.isNaN(caseId)) {
        await Promise.all([loadCases(), loadCaseDetail(caseId)]);
      }
      toast.success("Updated", `Document marked ${statusValue.replace("_", " ")}.`);
    } catch (error) {
      toast.error("Update failed", parseApiError(error, "Could not update document status."));
    }
  }

  const intakeDocuments = $derived.by(() => {
    if (!selectedCaseDetail) return [];
    return [...selectedCaseDetail.intake_documents].sort(
      (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime(),
    );
  });

  const requirementStates = $derived.by<RequirementState[]>(() => {
    const detail = selectedCaseDetail;
    if (!detail) return [];

    return detail.required_documents
      .filter((row) => row.is_required)
      .map((requirement) => {
        const linkedRows = detail.intake_documents
          .filter((doc) => doc.requirement === requirement.id)
          .sort((a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime());

        const approved = linkedRows.some((doc) => doc.status === "approved" || doc.status === "waived");
        const latest = linkedRows[0] ?? null;
        const currentStatus = approved ? "approved" : latest ? latest.status : "missing";

        return {
          requirement,
          approved,
          current_status: currentStatus,
          latest_document: latest,
        };
      });
  });

  function statusChipTone(statusValue: string): string {
    if (statusValue === "approved" || statusValue === "waived") return "bg-emerald-100 text-emerald-700 border border-emerald-200";
    if (statusValue === "under_review") return "bg-amber-100 text-amber-700 border border-amber-200";
    if (statusValue === "rejected") return "bg-rose-100 text-rose-700 border border-rose-200";
    if (statusValue === "received") return "bg-blue-100 text-blue-700 border border-blue-200";
    return "bg-neutral-100 text-neutral-600 border border-neutral-200";
  }

  $effect(() => {
    loadData();
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-semibold text-neutral-800">Onboarding Intake Documents</h2>
    <p class="mt-1 text-sm text-neutral-500">Log and review partner documents before ERP activation and partner portal access.</p>
  </div>

  {#if loading}
    <section class="rounded-xl border border-neutral-200 bg-white py-14">
      <div class="flex items-center justify-center">
        <div class="h-7 w-7 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    </section>
  {:else}
    <section class="rounded-xl border border-neutral-200 bg-white p-5">
      <div class="grid gap-4 md:grid-cols-4">
        <label class="flex flex-col gap-2 md:col-span-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Onboarding Case</span>
          <select
            bind:value={selectedCaseId}
            onchange={(event) => onCaseChange((event.currentTarget as HTMLSelectElement).value)}
            class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
          >
            <option value="">Select case</option>
            {#each cases as row (row.id)}
              <option value={String(row.id)}>{row.title} ({row.partner_type_display})</option>
            {/each}
          </select>
        </label>

        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Required Docs</p>
          <p class="mt-2 text-xl font-semibold text-neutral-800">
            {selectedCaseDetail ? `${selectedCaseDetail.approved_document_total}/${selectedCaseDetail.required_document_total}` : "0/0"}
          </p>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Gate Status</p>
          <p class="mt-2 text-sm font-semibold {selectedCaseDetail?.intake_gate_passed ? 'text-emerald-700' : 'text-amber-700'}">
            {selectedCaseDetail ? (selectedCaseDetail.intake_gate_passed ? "Ready" : "Not Ready") : "--"}
          </p>
          <p class="mt-1 text-xs text-neutral-500">
            {selectedCaseDetail ? `${selectedCaseDetail.missing_required_document_count} missing` : "No case selected"}
          </p>
        </div>
      </div>
    </section>

    {#if !selectedCaseDetail}
      <section class="rounded-xl border border-neutral-200 bg-white px-6 py-10 text-center text-sm text-neutral-500">
        Select an onboarding case to manage pre-onboarding intake documents.
      </section>
    {:else}
      <div class="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <form onsubmit={createIntakeDocument} class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold text-neutral-800">Log Intake Document</h3>
          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <label class="flex flex-col gap-2 md:col-span-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Requirement (Optional)</span>
              <select
                bind:value={form.requirement}
                onchange={(event) => setFormRequirement((event.currentTarget as HTMLSelectElement).value)}
                class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
              >
                <option value="">Ad-hoc / supplemental document</option>
                {#each selectedCaseDetail.required_documents as row (row.id)}
                  <option value={String(row.id)}>{row.name} ({row.code})</option>
                {/each}
              </select>
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Document Name</span>
              <input
                type="text"
                bind:value={form.document_name}
                placeholder="e.g. Signed SPA Copy"
                class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              />
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Document Code</span>
              <input
                type="text"
                bind:value={form.document_code}
                placeholder="e.g. spa_signed_copy"
                class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              />
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Source Channel</span>
              <select bind:value={form.source_channel} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                {#each sourceOptions as row}
                  <option value={row.value}>{row.label}</option>
                {/each}
              </select>
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Initial Status</span>
              <select bind:value={form.status} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                <option value="received">Received</option>
                <option value="under_review">Under Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="waived">Waived</option>
              </select>
            </label>

            <label class="flex flex-col gap-2 md:col-span-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Upload / Scan File</span>
              <input
                type="file"
                onchange={(event) => {
                  const target = event.currentTarget as HTMLInputElement;
                  form.file = target.files?.[0] ?? null;
                }}
                class="block w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
              />
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference URL</span>
              <input
                type="url"
                bind:value={form.external_reference_url}
                placeholder="https://..."
                class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              />
            </label>

            <label class="flex flex-col gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference Number</span>
              <input
                type="text"
                bind:value={form.external_reference_number}
                placeholder="External receipt/tracker"
                class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              />
            </label>

            <label class="flex flex-col gap-2 md:col-span-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Review Notes</span>
              <textarea
                bind:value={form.review_notes}
                rows="2"
                placeholder="Optional notes"
                class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              ></textarea>
            </label>
          </div>

          <div class="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={saving || !form.document_name.trim()}
              class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Intake Document"}
            </button>
          </div>
        </form>

        <section class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold text-neutral-800">Required Document Checklist</h3>
          {#if requirementStates.length === 0}
            <p class="mt-3 text-sm text-neutral-500">No required intake documents configured for this template.</p>
          {:else}
            <div class="mt-3 overflow-x-auto">
              <table class="min-w-[640px] w-full text-sm">
                <thead class="border-b border-neutral-100 bg-neutral-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Requirement</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Stage</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Latest</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each requirementStates as row (row.requirement.id)}
                    <tr>
                      <td class="px-3 py-2">
                        <p class="font-medium text-neutral-800">{row.requirement.name}</p>
                        <p class="text-xs font-mono text-neutral-500">{row.requirement.code}</p>
                      </td>
                      <td class="px-3 py-2 text-neutral-600">{row.requirement.stage_name || "--"}</td>
                      <td class="px-3 py-2">
                        <span class={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusChipTone(row.current_status)}`}>
                          {row.current_status.replaceAll("_", " ")}
                        </span>
                      </td>
                      <td class="px-3 py-2 text-xs text-neutral-500">
                        {#if row.latest_document}
                          {new Date(row.latest_document.received_at).toLocaleString()}
                        {:else}
                          --
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

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold text-neutral-800">Logged Intake Documents</h3>
        {#if intakeDocuments.length === 0}
          <p class="mt-3 text-sm text-neutral-500">No intake documents logged yet.</p>
        {:else}
          <div class="mt-3 overflow-x-auto">
            <table class="min-w-[1120px] w-full text-sm">
              <thead class="border-b border-neutral-100 bg-neutral-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Document</th>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Requirement</th>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Source</th>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</th>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Received</th>
                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference</th>
                  <th class="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each intakeDocuments as row (row.id)}
                  <tr>
                    <td class="px-3 py-2">
                      <p class="font-medium text-neutral-800">{row.document_name}</p>
                      <p class="text-xs font-mono text-neutral-500">{row.document_code}</p>
                    </td>
                    <td class="px-3 py-2 text-neutral-600">{row.requirement_name || "Ad-hoc"}</td>
                    <td class="px-3 py-2 text-neutral-600">{row.source_channel.replaceAll("_", " ")}</td>
                    <td class="px-3 py-2">
                      <span class={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusChipTone(row.status)}`}>
                        {row.status.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-neutral-500">{new Date(row.received_at).toLocaleString()}</td>
                    <td class="px-3 py-2 text-xs text-neutral-500">
                      {#if row.external_reference_number}
                        {row.external_reference_number}
                      {:else if row.external_reference_url}
                        <a href={row.external_reference_url} target="_blank" rel="noreferrer" class="text-neutral-700 underline">Open</a>
                      {:else if row.file}
                        <a href={row.file} target="_blank" rel="noreferrer" class="text-neutral-700 underline">Download</a>
                      {:else}
                        --
                      {/if}
                    </td>
                    <td class="px-3 py-2">
                      <div class="flex justify-end gap-2">
                        {#each reviewActions as action}
                          <button
                            onclick={() => updateDocumentStatus(row.id, action.value)}
                            class={`rounded-md border px-2.5 py-1 text-xs font-medium ${action.tone}`}
                            disabled={row.status === action.value}
                          >
                            {action.label}
                          </button>
                        {/each}
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    {/if}
  {/if}
</div>
