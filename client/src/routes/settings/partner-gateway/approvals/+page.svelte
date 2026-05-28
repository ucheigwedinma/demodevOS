<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, PartnerOnboardingCaseListItem } from "$lib/types";

  let loading = $state(true);
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let savingCaseId = $state<number | null>(null);
  let commentsByCase = $state<Record<number, string>>({});

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  async function fetchAllPages<T>(endpoint: string, params: Record<string, string> = {}): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;
    while (page <= 30) {
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

  async function loadQueue() {
    loading = true;
    try {
      cases = await fetchAllPages<PartnerOnboardingCaseListItem>("/partners/cases/", {
        ordering: "-updated_at",
        page_size: "200",
      });
      cases = cases.filter((row) => row.status === "under_review");
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load onboarding approvals queue."));
    } finally {
      loading = false;
    }
  }

  async function decide(caseId: number, decision: "approved" | "rejected") {
    savingCaseId = caseId;
    try {
      await api.post(`/partners/cases/${caseId}/record-approval/`, {
        decision,
        approver_role_label: "Governance",
        comments: commentsByCase[caseId] || "",
      });
      toast.success("Decision saved", `Case ${decision}.`);
      await loadQueue();
    } catch (error) {
      toast.error("Decision failed", parseApiError(error, "Could not record approval decision."));
    } finally {
      savingCaseId = null;
    }
  }

  $effect(() => {
    loadQueue();
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-semibold text-neutral-800">Approvals Queue</h2>
    <p class="mt-1 text-sm text-neutral-500">Review onboarding cases that have completed required stages and are awaiting governance sign-off.</p>
  </div>

  <section class="rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else if cases.length === 0}
      <div class="px-6 py-10 text-center text-sm text-neutral-500">No onboarding cases are currently awaiting approval.</div>
    {:else}
      <div class="divide-y divide-neutral-100">
        {#each cases as row (row.id)}
          <div class="p-4 sm:p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-neutral-800">{row.title}</p>
                <p class="mt-1 text-xs text-neutral-500 capitalize">{row.partner_type} • {row.required_stage_completed}/{row.required_stage_total} required stages complete</p>
              </div>
              <span class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">Under Review</span>
            </div>
            <div class="mt-3 grid gap-3 md:grid-cols-4">
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                <p class="font-semibold uppercase tracking-wider text-neutral-500">Current Stage</p>
                <p class="mt-1 text-sm text-neutral-800">{row.current_stage_name || "--"}</p>
              </div>
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                <p class="font-semibold uppercase tracking-wider text-neutral-500">ERP Profile</p>
                <p class="mt-1 text-sm text-neutral-800">{row.has_erp_profile ? "Available" : "Missing"}</p>
              </div>
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                <p class="font-semibold uppercase tracking-wider text-neutral-500">Portal Access</p>
                <p class="mt-1 text-sm text-neutral-800">{row.portal_access_granted ? "Granted" : "Pending"}</p>
              </div>
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                <p class="font-semibold uppercase tracking-wider text-neutral-500">Updated</p>
                <p class="mt-1 text-sm text-neutral-800">{new Date(row.updated_at).toLocaleString()}</p>
              </div>
            </div>
            <textarea
              bind:value={commentsByCase[row.id]}
              rows="2"
              placeholder="Approval comments"
              class="mt-3 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            ></textarea>
            <div class="mt-3 flex justify-end gap-2">
              <button
                onclick={() => decide(row.id, "rejected")}
                disabled={savingCaseId === row.id}
                class="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              >
                Reject
              </button>
              <button
                onclick={() => decide(row.id, "approved")}
                disabled={savingCaseId === row.id}
                class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Approve
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </section>
</div>
