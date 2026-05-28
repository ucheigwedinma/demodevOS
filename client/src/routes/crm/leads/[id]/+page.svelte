<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    LeadDetail,
    LeadActivity,
    LeadProjectInterest,
    LeadUnitPreference,
    PipelineStage,
  } from "$lib/types";

  const leadId = $derived($page.params.id);

  let lead = $state<LeadDetail | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let editing = $state(false);
  let activeTab = $state<"overview" | "activities" | "preferences" | "timeline">("overview");

  // Edit form state
  let editForm = $state({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    secondary_phone: "",
    company: "",
    nationality: "",
    lead_type: "" as "buyer" | "tenant" | "investor",
    priority: "" as "low" | "medium" | "high" | "urgent",
    score: 0,
    tags: "",
    budget_min: "",
    budget_max: "",
    preferred_locations: "",
    payment_capability: "" as "cash" | "mortgage" | "installment" | "mixed" | "undetermined",
    notes: "",
  });

  // Stage change
  let showStageDropdown = $state(false);
  let stageChangeNotes = $state("");
  let changingStage = $state(false);

  // Convert modal
  let showConvertModal = $state(false);
  let convertNotes = $state("");
  let converting = $state(false);

  // Mark lost modal
  let showLostModal = $state(false);
  let lostReason = $state("");
  let markingLost = $state(false);

  // Activity modal
  let showActivityModal = $state(false);
  let activityForm = $state({
    activity_type: "call",
    subject: "",
    description: "",
    scheduled_at: "",
  });
  let savingActivity = $state(false);

  // Interest modal
  let showInterestModal = $state(false);
  let interestForm = $state({
    project: "",
    interest_level: "medium" as "low" | "medium" | "high",
    notes: "",
  });
  let projects = $state<{ id: number; name: string }[]>([]);
  let savingInterest = $state(false);

  // Preference modal
  let showPreferenceModal = $state(false);
  let preferenceForm = $state({
    unit_type: "",
    min_bedrooms: "",
    max_bedrooms: "",
    min_area_sqft: "",
    max_area_sqft: "",
    floor_preference: "",
    view_preference: "",
    notes: "",
  });
  let savingPreference = $state(false);

  // Pipeline stages definition
  const pipelineStages: { key: PipelineStage; label: string }[] = [
    { key: "inquiry", label: "Inquiry" },
    { key: "qualified", label: "Qualified" },
    { key: "site_visit", label: "Site Visit" },
    { key: "offer_made", label: "Offer Made" },
    { key: "reservation", label: "Reservation" },
    { key: "spa_issued", label: "SPA Issued" },
    { key: "closed", label: "Closed" },
  ];

  const priorityLabels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  const leadTypeLabels: Record<string, string> = {
    buyer: "Buyer",
    tenant: "Tenant",
    investor: "Investor",
  };

  const paymentCapabilityLabels: Record<string, string> = {
    cash: "Cash",
    mortgage: "Mortgage",
    installment: "Installment",
    mixed: "Mixed",
    undetermined: "Undetermined",
  };

  const activityTypeOptions = [
    { value: "call", label: "Call" },
    { value: "email", label: "Email" },
    { value: "meeting", label: "Meeting" },
    { value: "site_visit", label: "Site Visit" },
    { value: "follow_up", label: "Follow Up" },
    { value: "note", label: "Note" },
    { value: "other", label: "Other" },
  ];

  const activityIcons: Record<string, string> = {
    call: "M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z",
    email: "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
    meeting: "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    site_visit: "M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z",
    follow_up: "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182",
    note: "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    other: "M11.25 11.25l.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z",
  };

  // Stage date keys mapping
  const stageDateKeys: Record<string, keyof LeadDetail> = {
    inquiry: "inquiry_date",
    qualified: "qualified_date",
    site_visit: "site_visit_date",
    offer_made: "offer_date",
    reservation: "reservation_date",
    spa_issued: "spa_issued_date",
    closed: "closed_date",
  };

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function fmtAmount(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return currency.format(parseFloat(value));
  }

  function parseTags(raw: string): string[] {
    return raw
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function parseList(raw: string): string[] {
    return raw
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function stageIndex(stage: PipelineStage): number {
    return pipelineStages.findIndex((s) => s.key === stage);
  }

  function nextStage(currentStage: PipelineStage): PipelineStage | null {
    const idx = stageIndex(currentStage);
    if (idx < 0 || idx >= pipelineStages.length - 1) return null;
    return pipelineStages[idx + 1].key;
  }

  function nextStageLabel(currentStage: PipelineStage): string | null {
    const next = nextStage(currentStage);
    if (!next) return null;
    return pipelineStages.find((s) => s.key === next)?.label ?? null;
  }

  function populateEditForm(l: LeadDetail) {
    editForm = {
      first_name: l.first_name,
      last_name: l.last_name,
      email: l.email,
      phone: l.phone,
      secondary_phone: l.secondary_phone,
      company: l.company,
      nationality: l.nationality,
      lead_type: l.lead_type,
      priority: l.priority,
      score: l.score,
      tags: l.tags.join(", "),
      budget_min: l.budget_min ?? "",
      budget_max: l.budget_max ?? "",
      preferred_locations: l.preferred_locations.join(", "),
      payment_capability: l.payment_capability,
      notes: l.notes,
    };
  }

  $effect(() => {
    void leadId;
    loadLead();
  });

  async function loadLead() {
    loading = true;
    try {
      const res = await api.get<LeadDetail>(`/crm/leads/${leadId}/`);
      lead = res;
      populateEditForm(res);
    } catch {
      lead = null;
    }
    loading = false;
  }

  async function saveLead() {
    if (!lead) return;
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        email: editForm.email,
        phone: editForm.phone,
        secondary_phone: editForm.secondary_phone,
        company: editForm.company,
        nationality: editForm.nationality,
        lead_type: editForm.lead_type,
        priority: editForm.priority,
        score: editForm.score,
        tags: parseTags(editForm.tags),
        budget_min: editForm.budget_min || null,
        budget_max: editForm.budget_max || null,
        preferred_locations: parseList(editForm.preferred_locations),
        payment_capability: editForm.payment_capability,
        notes: editForm.notes,
      };
      const res = await api.patch<LeadDetail>(`/crm/leads/${leadId}/`, payload);
      lead = res;
      populateEditForm(res);
      editing = false;
      toast.success("Lead updated", "Changes have been saved");
    } catch {
      toast.error("Failed to save", "Please try again later");
    }
    saving = false;
  }

  async function advanceStage() {
    if (!lead) return;
    const next = nextStage(lead.pipeline_stage);
    if (!next) return;
    changingStage = true;
    try {
      await api.post(`/crm/leads/${leadId}/change_stage/`, {
        stage: next,
        notes: stageChangeNotes,
      });
      stageChangeNotes = "";
      showStageDropdown = false;
      toast.success("Stage advanced", `Lead moved to ${nextStageLabel(lead.pipeline_stage)}`);
      await loadLead();
    } catch {
      toast.error("Failed to change stage", "Please try again later");
    }
    changingStage = false;
  }

  async function convertToCustomer() {
    converting = true;
    try {
      await api.post(`/crm/leads/${leadId}/convert/`, { notes: convertNotes });
      convertNotes = "";
      showConvertModal = false;
      toast.success("Lead converted", "Lead has been converted to a customer");
      await loadLead();
    } catch {
      toast.error("Conversion failed", "Please try again later");
    }
    converting = false;
  }

  async function markLost() {
    markingLost = true;
    try {
      await api.post(`/crm/leads/${leadId}/mark_lost/`, { reason: lostReason });
      lostReason = "";
      showLostModal = false;
      toast.success("Lead marked as lost", "The lead has been marked as lost");
      await loadLead();
    } catch {
      toast.error("Failed to mark lost", "Please try again later");
    }
    markingLost = false;
  }

  // Activities
  async function addActivity() {
    savingActivity = true;
    try {
      await api.post(`/crm/leads/${leadId}/activities/`, {
        activity_type: activityForm.activity_type,
        subject: activityForm.subject,
        description: activityForm.description,
        scheduled_at: activityForm.scheduled_at || null,
      });
      activityForm = { activity_type: "call", subject: "", description: "", scheduled_at: "" };
      showActivityModal = false;
      toast.success("Activity added", "The activity has been logged");
      await loadLead();
    } catch {
      toast.error("Failed to add activity", "Please try again later");
    }
    savingActivity = false;
  }

  async function toggleActivityComplete(activity: LeadActivity) {
    try {
      await api.patch(`/crm/leads/${leadId}/activities/${activity.id}/`, {
        is_completed: !activity.is_completed,
        completed_at: !activity.is_completed ? new Date().toISOString() : null,
      });
      await loadLead();
    } catch {
      toast.error("Failed to update activity", "Please try again later");
    }
  }

  async function deleteActivity(activityId: number) {
    if (!confirm("Delete this activity?")) return;
    try {
      await api.delete(`/crm/leads/${leadId}/activities/${activityId}/`);
      toast.success("Activity deleted", "The activity has been removed");
      await loadLead();
    } catch {
      toast.error("Failed to delete activity", "Please try again later");
    }
  }

  // Interests
  async function loadProjects() {
    try {
      const res = await api.get<{ results: { id: number; name: string }[] }>("/projects/projects/", { page_size: "200" });
      projects = res.results;
    } catch {
      projects = [];
    }
  }

  async function addInterest() {
    savingInterest = true;
    try {
      await api.post(`/crm/leads/${leadId}/interests/`, {
        project: Number(interestForm.project),
        interest_level: interestForm.interest_level,
        notes: interestForm.notes,
      });
      interestForm = { project: "", interest_level: "medium", notes: "" };
      showInterestModal = false;
      toast.success("Interest added", "Project interest has been recorded");
      await loadLead();
    } catch {
      toast.error("Failed to add interest", "Please try again later");
    }
    savingInterest = false;
  }

  async function removeInterest(interestId: number) {
    if (!confirm("Remove this project interest?")) return;
    try {
      await api.delete(`/crm/leads/${leadId}/interests/${interestId}/`);
      toast.success("Interest removed", "Project interest has been removed");
      await loadLead();
    } catch {
      toast.error("Failed to remove interest", "Please try again later");
    }
  }

  // Preferences
  async function addPreference() {
    savingPreference = true;
    try {
      await api.post(`/crm/leads/${leadId}/preferences/`, {
        unit_type: preferenceForm.unit_type,
        min_bedrooms: preferenceForm.min_bedrooms ? Number(preferenceForm.min_bedrooms) : null,
        max_bedrooms: preferenceForm.max_bedrooms ? Number(preferenceForm.max_bedrooms) : null,
        min_area_sqft: preferenceForm.min_area_sqft || null,
        max_area_sqft: preferenceForm.max_area_sqft || null,
        floor_preference: preferenceForm.floor_preference,
        view_preference: preferenceForm.view_preference,
        notes: preferenceForm.notes,
      });
      preferenceForm = { unit_type: "", min_bedrooms: "", max_bedrooms: "", min_area_sqft: "", max_area_sqft: "", floor_preference: "", view_preference: "", notes: "" };
      showPreferenceModal = false;
      toast.success("Preference added", "Unit preference has been recorded");
      await loadLead();
    } catch {
      toast.error("Failed to add preference", "Please try again later");
    }
    savingPreference = false;
  }

  async function removePreference(prefId: number) {
    if (!confirm("Remove this unit preference?")) return;
    try {
      await api.delete(`/crm/leads/${leadId}/preferences/${prefId}/`);
      toast.success("Preference removed", "Unit preference has been removed");
      await loadLead();
    } catch {
      toast.error("Failed to remove preference", "Please try again later");
    }
  }

  function openInterestModal() {
    loadProjects();
    showInterestModal = true;
  }

  const tabs = [
    { key: "overview" as const, label: "Overview" },
    { key: "activities" as const, label: "Activities" },
    { key: "preferences" as const, label: "Preferences" },
    { key: "timeline" as const, label: "Timeline" },
  ];
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !lead}
  <div class="py-24 text-center">
    <p class="text-neutral-400 text-sm">Lead not found</p>
    <a href="/crm/leads" class="inline-block mt-3 text-sm font-medium text-neutral-900 hover:underline">Back to leads</a>
  </div>
{:else}
  <div class="space-y-6">

    <!-- Header -->
    <div>
      <Breadcrumb items={[
        { label: "CRM", href: "/crm" },
        { label: "Leads", href: "/crm/leads" },
        { label: lead.full_name },
      ]} />

      <div class="flex items-start justify-between mt-4">
        <div class="min-w-0">
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">{lead.full_name}</h1>
            <StatusBadge status={lead.status} label={lead.status_display} />
            <StatusBadge status={lead.pipeline_stage} label={lead.pipeline_stage_display} />
          </div>
          <div class="flex items-center gap-4 mt-1.5 text-sm text-neutral-500 flex-wrap">
            {#if lead.company}
              <span>{lead.company}</span>
            {/if}
            {#if lead.email}
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
                </svg>
                {lead.email}
              </span>
            {/if}
            {#if lead.phone}
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z" />
                </svg>
                {lead.phone}
              </span>
            {/if}
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <!-- Advance Stage -->
          {#if lead.status === "active" && nextStage(lead.pipeline_stage)}
            <div class="relative">
              <button
                onclick={() => (showStageDropdown = !showStageDropdown)}
                class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
              >
                Advance Stage
              </button>
              {#if showStageDropdown}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl border border-neutral-200 shadow-lg z-20 p-4"
                  onkeydown={(e) => { if (e.key === "Escape") showStageDropdown = false; }}
                >
                  <p class="text-sm font-medium text-neutral-900 mb-3">
                    Move to <span class="font-semibold">{nextStageLabel(lead.pipeline_stage)}</span>
                  </p>
                  <textarea
                    bind:value={stageChangeNotes}
                    placeholder="Notes (optional)"
                    rows={3}
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none mb-3"
                  ></textarea>
                  <div class="flex gap-2 justify-end">
                    <button
                      onclick={() => (showStageDropdown = false)}
                      class="px-3 py-1.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onclick={advanceStage}
                      disabled={changingStage}
                      class="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                    >
                      {changingStage ? "Moving..." : "Confirm"}
                    </button>
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Convert to Customer -->
          {#if lead.status === "active" && (lead.pipeline_stage === "closed" || lead.pipeline_stage === "spa_issued")}
            <button
              onclick={() => (showConvertModal = true)}
              class="px-4 py-2 border border-neutral-900 text-neutral-900 rounded-lg text-sm font-medium hover:bg-neutral-900 hover:text-white transition-colors"
            >
              Convert to Customer
            </button>
          {/if}

          <!-- Mark Lost -->
          {#if lead.status === "active"}
            <button
              onclick={() => (showLostModal = true)}
              class="px-4 py-2 border border-neutral-200 text-neutral-600 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors"
            >
              Mark Lost
            </button>
          {/if}

          <!-- Edit Toggle -->
          <button
            onclick={() => {
              if (editing && lead) {
                populateEditForm(lead);
              }
              editing = !editing;
            }}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium transition-colors
                   {editing ? 'bg-neutral-900 text-white hover:bg-neutral-800 border-neutral-900' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            {editing ? "Cancel Edit" : "Edit"}
          </button>

          <!-- Save (visible in edit mode) -->
          {#if editing}
            <button
              onclick={saveLead}
              disabled={saving}
              class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {#if saving}
                <div class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1.5"></div>
              {/if}
              Save
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Pipeline Progress Bar -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <div class="flex items-center">
        {#each pipelineStages as stage, i}
          {@const currentIdx = stageIndex(lead.pipeline_stage)}
          {@const isCompleted = i <= currentIdx}
          {@const isCurrent = i === currentIdx}
          {@const dateKey = stageDateKeys[stage.key]}
          {@const dateValue = lead[dateKey] as string | null}

          {#if i > 0}
            <div class="flex-1 h-0.5 {i <= currentIdx ? 'bg-neutral-900' : 'bg-neutral-200'} transition-colors"></div>
          {/if}

          <div class="flex flex-col items-center relative">
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors
                     {isCompleted ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-400'}
                     {isCurrent ? 'ring-2 ring-neutral-900 ring-offset-2' : ''}"
            >
              {#if isCompleted && !isCurrent}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              {:else}
                {i + 1}
              {/if}
            </div>
            <span class="text-[10px] font-medium mt-1.5 whitespace-nowrap {isCompleted ? 'text-neutral-900' : 'text-neutral-400'}">
              {stage.label}
            </span>
            {#if dateValue}
              <span class="text-[9px] text-neutral-400 mt-0.5 whitespace-nowrap">
                {fmtDate(dateValue)}
              </span>
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-neutral-200">
      <nav class="flex gap-6">
        {#each tabs as tab}
          <button
            onclick={() => (activeTab = tab.key)}
            class="pb-3 text-sm font-medium border-b-2 transition-colors
                   {activeTab === tab.key
                     ? 'border-neutral-900 text-neutral-900'
                     : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
          >
            {tab.label}
            {#if tab.key === "activities" && lead.activities.length > 0}
              <span class="ml-1.5 text-xs text-neutral-400">{lead.activities.length}</span>
            {/if}
          </button>
        {/each}
      </nav>
    </div>

    <!-- TAB: Overview -->
    {#if activeTab === "overview"}
      <div class="grid md:grid-cols-2 gap-6">

        <!-- Contact Information -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Contact Information</h3>
          <div class="space-y-3 text-sm">
            {#if editing}
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">First Name</span>
                  <input bind:value={editForm.first_name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Last Name</span>
                  <input bind:value={editForm.last_name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Email</span>
                <input bind:value={editForm.email} type="email" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Phone</span>
                  <input bind:value={editForm.phone} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Secondary Phone</span>
                  <input bind:value={editForm.secondary_phone} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Company</span>
                <input bind:value={editForm.company} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Nationality</span>
                <input bind:value={editForm.nationality} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            {:else}
              <div class="flex justify-between"><span class="text-neutral-400">Email</span><span class="text-neutral-900">{lead.email || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Phone</span><span class="text-neutral-900">{lead.phone || "\u2014"}</span></div>
              {#if lead.secondary_phone}
                <div class="flex justify-between"><span class="text-neutral-400">Secondary Phone</span><span class="text-neutral-900">{lead.secondary_phone}</span></div>
              {/if}
              <div class="flex justify-between"><span class="text-neutral-400">Company</span><span class="text-neutral-900">{lead.company || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Nationality</span><span class="text-neutral-900">{lead.nationality || "\u2014"}</span></div>
            {/if}
          </div>
        </div>

        <!-- Lead Details -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Lead Details</h3>
          <div class="space-y-3 text-sm">
            {#if editing}
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Lead Type</span>
                <select bind:value={editForm.lead_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="buyer">Buyer</option>
                  <option value="tenant">Tenant</option>
                  <option value="investor">Investor</option>
                </select>
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Priority</span>
                  <select bind:value={editForm.priority} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Score</span>
                  <input bind:value={editForm.score} type="number" min="0" max="100" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Tags</span>
                <input
                  bind:value={editForm.tags}
                  placeholder="high net worth, mortgage needed"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
                <p class="mt-1 text-[11px] text-neutral-400">Comma-separated labels.</p>
              </label>
            {:else}
              <div class="flex justify-between"><span class="text-neutral-400">Lead Type</span><span class="text-neutral-900">{leadTypeLabels[lead.lead_type]}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Priority</span><span class="text-neutral-900">{priorityLabels[lead.priority]}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Score</span><span class="text-neutral-900 tabular-nums">{lead.score}</span></div>
              <div class="space-y-1">
                <span class="text-neutral-400">Tags</span>
                {#if lead.tags.length > 0}
                  <div class="flex flex-wrap gap-1.5">
                    {#each lead.tags as tag}
                      <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-700">
                        {tag}
                      </span>
                    {/each}
                  </div>
                {:else}
                  <p class="text-neutral-900">\u2014</p>
                {/if}
              </div>
            {/if}
            <div class="flex justify-between"><span class="text-neutral-400">Source</span><span class="text-neutral-900">{lead.source_name || "\u2014"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Broker</span><span class="text-neutral-900">{lead.broker_name || "\u2014"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Referral</span><span class="text-neutral-900">{lead.referral_name || "\u2014"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Assigned To</span><span class="text-neutral-900">{lead.assigned_to_name || "\u2014"}</span></div>
          </div>
        </div>

        <!-- Budget & Payment -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Budget & Payment</h3>
          <div class="space-y-3 text-sm">
            {#if editing}
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Budget Min</span>
                  <input bind:value={editForm.budget_min} placeholder="0.00" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Budget Max</span>
                  <input bind:value={editForm.budget_max} placeholder="0.00" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Payment Capability</span>
                <select bind:value={editForm.payment_capability} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="cash">Cash</option>
                  <option value="mortgage">Mortgage</option>
                  <option value="installment">Installment</option>
                  <option value="mixed">Mixed</option>
                  <option value="undetermined">Undetermined</option>
                </select>
              </label>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Preferred Locations</span>
                <input
                  bind:value={editForm.preferred_locations}
                  placeholder="Lekki, Victoria Island"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
                <p class="mt-1 text-[11px] text-neutral-400">Comma-separated preferred areas for matching.</p>
              </label>
            {:else}
              <div class="flex justify-between"><span class="text-neutral-400">Budget Min</span><span class="text-neutral-900 tabular-nums">{fmtAmount(lead.budget_min)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Budget Max</span><span class="text-neutral-900 tabular-nums">{fmtAmount(lead.budget_max)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Payment Capability</span><span class="text-neutral-900">{paymentCapabilityLabels[lead.payment_capability]}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Preferred Locations</span><span class="text-neutral-900 text-right">{lead.preferred_locations.join(", ") || "\u2014"}</span></div>
            {/if}
          </div>
        </div>

        <!-- Key Dates -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Key Dates</h3>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between"><span class="text-neutral-400">Inquiry Date</span><span class="text-neutral-900">{fmtDate(lead.inquiry_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Qualified Date</span><span class="text-neutral-900">{fmtDate(lead.qualified_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Site Visit Date</span><span class="text-neutral-900">{fmtDate(lead.site_visit_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Offer Date</span><span class="text-neutral-900">{fmtDate(lead.offer_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Reservation Date</span><span class="text-neutral-900">{fmtDate(lead.reservation_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">SPA Issued Date</span><span class="text-neutral-900">{fmtDate(lead.spa_issued_date)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Closed Date</span><span class="text-neutral-900">{fmtDate(lead.closed_date)}</span></div>
            <div class="flex justify-between border-t border-neutral-100 pt-3"><span class="text-neutral-400 font-medium">Days in Pipeline</span><span class="text-neutral-900 font-semibold tabular-nums">{lead.days_in_pipeline}</span></div>
          </div>
        </div>

        <!-- Notes -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Notes</h3>
          {#if editing}
            <textarea
              bind:value={editForm.notes}
              rows={4}
              placeholder="Add notes about this lead..."
              class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
            ></textarea>
          {:else}
            <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{lead.notes || "No notes recorded."}</p>
          {/if}
        </div>

        <!-- Lost Reason (if lost) -->
        {#if lead.status === "lost" && lead.lost_reason}
          <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2 space-y-3">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Lost Reason</h3>
            <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{lead.lost_reason}</p>
          </div>
        {/if}

        <!-- Converted Customer (if converted) -->
        {#if lead.converted_customer}
          <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2 space-y-3">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Converted Customer</h3>
            <a
              href="/finance/customers/{lead.converted_customer}"
              class="inline-flex items-center gap-2 text-sm font-medium text-neutral-900 hover:underline"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              {lead.converted_customer_name ?? `Customer #${lead.converted_customer}`}
            </a>
          </div>
        {/if}
      </div>
    {/if}

    <!-- TAB: Activities -->
    {#if activeTab === "activities"}
      <div class="space-y-4">
        <div class="flex justify-end">
          <button
            onclick={() => (showActivityModal = true)}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
          >
            + Add Activity
          </button>
        </div>

        {#if lead.activities.length === 0}
          <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <p class="text-neutral-400 text-sm">No activities recorded yet. Add your first activity to start tracking interactions.</p>
          </div>
        {:else}
          <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
            {#each [...lead.activities].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) as activity}
              <div class="p-5 flex gap-4">
                <!-- Activity icon -->
                <div class="shrink-0 w-9 h-9 rounded-full bg-neutral-100 flex items-center justify-center">
                  <svg class="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d={activityIcons[activity.activity_type] || activityIcons.other} />
                  </svg>
                </div>

                <!-- Activity content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-neutral-900">{activity.subject}</span>
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-600">
                          {activity.activity_type_display}
                        </span>
                        {#if activity.is_completed}
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-900 text-white">
                            Completed
                          </span>
                        {/if}
                      </div>
                      {#if activity.description}
                        <p class="text-sm text-neutral-500 mt-1 whitespace-pre-line">{activity.description}</p>
                      {/if}
                      <div class="flex items-center gap-3 mt-2 text-xs text-neutral-400">
                        {#if activity.scheduled_at}
                          <span>Scheduled: {fmtDateTime(activity.scheduled_at)}</span>
                        {/if}
                        {#if activity.performed_by_name}
                          <span>By: {activity.performed_by_name}</span>
                        {/if}
                        <span>{fmtDateTime(activity.created_at)}</span>
                      </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <button
                        onclick={() => toggleActivityComplete(activity)}
                        class="text-xs font-medium transition-colors
                               {activity.is_completed ? 'text-neutral-400 hover:text-neutral-600' : 'text-neutral-900 hover:text-neutral-700'}"
                        title={activity.is_completed ? "Mark incomplete" : "Mark complete"}
                      >
                        {#if activity.is_completed}
                          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                          </svg>
                        {:else}
                          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                          </svg>
                        {/if}
                      </button>
                      <button
                        onclick={() => deleteActivity(activity.id)}
                        class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- TAB: Preferences -->
    {#if activeTab === "preferences"}
      <div class="space-y-8">

        <!-- Project Interests -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Project Interests</h3>
            <button
              onclick={openInterestModal}
              class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
            >
              + Add Interest
            </button>
          </div>

          {#if lead.project_interests.length === 0}
            <div class="bg-white rounded-xl border border-neutral-200 p-8 text-center">
              <p class="text-neutral-400 text-sm">No project interests recorded.</p>
            </div>
          {:else}
            <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
              {#each lead.project_interests as interest}
                <div class="p-5 flex items-center justify-between">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-neutral-900">{interest.project_name}</span>
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium
                             {interest.interest_level === 'high' ? 'bg-neutral-900 text-white' :
                              interest.interest_level === 'medium' ? 'bg-neutral-200 text-neutral-700' :
                              'bg-neutral-100 text-neutral-500'}">
                        {interest.interest_level}
                      </span>
                    </div>
                    {#if interest.notes}
                      <p class="text-xs text-neutral-400 mt-1">{interest.notes}</p>
                    {/if}
                    <p class="text-xs text-neutral-400 mt-1">Added {fmtDate(interest.created_at?.slice(0, 10))}</p>
                  </div>
                  <button
                    onclick={() => removeInterest(interest.id)}
                    class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors shrink-0 ml-4"
                  >
                    Remove
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Unit Preferences -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Unit Preferences</h3>
            <button
              onclick={() => (showPreferenceModal = true)}
              class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
            >
              + Add Preference
            </button>
          </div>

          {#if lead.unit_preferences.length === 0}
            <div class="bg-white rounded-xl border border-neutral-200 p-8 text-center">
              <p class="text-neutral-400 text-sm">No unit preferences recorded.</p>
            </div>
          {:else}
            <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
              {#each lead.unit_preferences as pref}
                <div class="p-5 flex items-start justify-between gap-4">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2 mb-2">
                      <span class="text-sm font-medium text-neutral-900">{pref.unit_type_display || pref.unit_type}</span>
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1 text-xs">
                      {#if pref.min_bedrooms != null || pref.max_bedrooms != null}
                        <div>
                          <span class="text-neutral-400">Bedrooms:</span>
                          <span class="text-neutral-700 ml-1">
                            {pref.min_bedrooms ?? "?"} - {pref.max_bedrooms ?? "?"}
                          </span>
                        </div>
                      {/if}
                      {#if pref.min_area_sqft || pref.max_area_sqft}
                        <div>
                          <span class="text-neutral-400">Area (sqft):</span>
                          <span class="text-neutral-700 ml-1">
                            {pref.min_area_sqft ?? "?"} - {pref.max_area_sqft ?? "?"}
                          </span>
                        </div>
                      {/if}
                      {#if pref.floor_preference}
                        <div>
                          <span class="text-neutral-400">Floor:</span>
                          <span class="text-neutral-700 ml-1">{pref.floor_preference}</span>
                        </div>
                      {/if}
                      {#if pref.view_preference}
                        <div>
                          <span class="text-neutral-400">View:</span>
                          <span class="text-neutral-700 ml-1">{pref.view_preference}</span>
                        </div>
                      {/if}
                    </div>
                    {#if pref.notes}
                      <p class="text-xs text-neutral-400 mt-2">{pref.notes}</p>
                    {/if}
                  </div>
                  <button
                    onclick={() => removePreference(pref.id)}
                    class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors shrink-0"
                  >
                    Remove
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- TAB: Timeline -->
    {#if activeTab === "timeline"}
      <div>
        {#if lead.stage_transitions.length === 0}
          <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <p class="text-neutral-400 text-sm">No stage transitions recorded yet.</p>
          </div>
        {:else}
          <div class="relative">
            <!-- Vertical connecting line -->
            <div class="absolute left-[17px] top-3 bottom-3 w-px bg-neutral-200"></div>

            <div class="space-y-0">
              {#each [...lead.stage_transitions].sort((a, b) => new Date(b.transitioned_at).getTime() - new Date(a.transitioned_at).getTime()) as transition, i}
                <div class="relative flex gap-4 pb-6">
                  <!-- Timeline dot -->
                  <div class="relative z-10 shrink-0">
                    <div class="w-[35px] h-[35px] rounded-full bg-white border-2 border-neutral-300 flex items-center justify-center
                                {i === 0 ? 'border-neutral-900' : ''}">
                      <svg class="w-4 h-4 {i === 0 ? 'text-neutral-900' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                      </svg>
                    </div>
                  </div>

                  <!-- Content -->
                  <div class="bg-white rounded-xl border border-neutral-200 p-4 flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <StatusBadge status={transition.from_stage} label={pipelineStages.find(s => s.key === transition.from_stage)?.label ?? transition.from_stage} />
                      <svg class="w-3.5 h-3.5 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                      </svg>
                      <StatusBadge status={transition.to_stage} label={pipelineStages.find(s => s.key === transition.to_stage)?.label ?? transition.to_stage} />
                    </div>
                    <div class="flex items-center gap-3 mt-2 text-xs text-neutral-400">
                      {#if transition.transitioned_by_name}
                        <span>By {transition.transitioned_by_name}</span>
                      {/if}
                      <span>{fmtDateTime(transition.transitioned_at)}</span>
                    </div>
                    {#if transition.notes}
                      <p class="text-xs text-neutral-500 mt-2 whitespace-pre-line">{transition.notes}</p>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- MODAL: Convert to Customer -->
  {#if showConvertModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onkeydown={(e) => { if (e.key === "Escape") showConvertModal = false; }}>
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showConvertModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-1">Convert to Customer</h2>
        <p class="text-sm text-neutral-500 mb-4">This will convert {lead.full_name} into a customer record.</p>
        <textarea
          bind:value={convertNotes}
          placeholder="Notes (optional)"
          rows={3}
          class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none mb-4"
        ></textarea>
        <div class="flex gap-3 justify-end">
          <button
            onclick={() => (showConvertModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={convertToCustomer}
            disabled={converting}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {converting ? "Converting..." : "Convert"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- MODAL: Mark Lost -->
  {#if showLostModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onkeydown={(e) => { if (e.key === "Escape") showLostModal = false; }}>
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showLostModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-1">Mark Lead as Lost</h2>
        <p class="text-sm text-neutral-500 mb-4">Please provide a reason for losing this lead.</p>
        <textarea
          bind:value={lostReason}
          placeholder="Reason for losing this lead..."
          rows={3}
          class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none mb-4"
        ></textarea>
        <div class="flex gap-3 justify-end">
          <button
            onclick={() => (showLostModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={markLost}
            disabled={markingLost || !lostReason.trim()}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {markingLost ? "Saving..." : "Mark as Lost"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- MODAL: Add Activity -->
  {#if showActivityModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onkeydown={(e) => { if (e.key === "Escape") showActivityModal = false; }}>
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showActivityModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-lg p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-4">Add Activity</h2>
        <div class="space-y-4">
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Activity Type</span>
            <select bind:value={activityForm.activity_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each activityTypeOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </label>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Subject</span>
            <input bind:value={activityForm.subject} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Follow-up call about pricing" />
          </label>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Description</span>
            <textarea bind:value={activityForm.description} rows={3} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Details..."></textarea>
          </label>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Scheduled At</span>
            <input bind:value={activityForm.scheduled_at} type="datetime-local" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <div class="flex gap-3 justify-end mt-6">
          <button
            onclick={() => (showActivityModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={addActivity}
            disabled={savingActivity || !activityForm.subject.trim()}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {savingActivity ? "Adding..." : "Add Activity"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- MODAL: Add Interest -->
  {#if showInterestModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onkeydown={(e) => { if (e.key === "Escape") showInterestModal = false; }}>
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showInterestModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-lg p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-4">Add Project Interest</h2>
        <div class="space-y-4">
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Project</span>
            <select bind:value={interestForm.project} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">Select a project</option>
              {#each projects as proj}
                <option value={String(proj.id)}>{proj.name}</option>
              {/each}
            </select>
          </label>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Interest Level</span>
            <select bind:value={interestForm.interest_level} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
            <textarea bind:value={interestForm.notes} rows={3} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Optional notes..."></textarea>
          </label>
        </div>
        <div class="flex gap-3 justify-end mt-6">
          <button
            onclick={() => (showInterestModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={addInterest}
            disabled={savingInterest || !interestForm.project}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {savingInterest ? "Adding..." : "Add Interest"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- MODAL: Add Preference -->
  {#if showPreferenceModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onkeydown={(e) => { if (e.key === "Escape") showPreferenceModal = false; }}>
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showPreferenceModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-lg p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-4">Add Unit Preference</h2>
        <div class="space-y-4">
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Unit Type</span>
            <input bind:value={preferenceForm.unit_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. apartment, villa, studio" />
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Min Bedrooms</span>
              <input bind:value={preferenceForm.min_bedrooms} type="number" min="0" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Max Bedrooms</span>
              <input bind:value={preferenceForm.max_bedrooms} type="number" min="0" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Min Area (sqft)</span>
              <input bind:value={preferenceForm.min_area_sqft} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Max Area (sqft)</span>
              <input bind:value={preferenceForm.max_area_sqft} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Floor Preference</span>
              <input bind:value={preferenceForm.floor_preference} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. High floor" />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">View Preference</span>
              <input bind:value={preferenceForm.view_preference} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Sea view" />
            </label>
          </div>
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
            <textarea bind:value={preferenceForm.notes} rows={2} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Optional notes..."></textarea>
          </label>
        </div>
        <div class="flex gap-3 justify-end mt-6">
          <button
            onclick={() => (showPreferenceModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={addPreference}
            disabled={savingPreference || !preferenceForm.unit_type.trim()}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {savingPreference ? "Adding..." : "Add Preference"}
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}
