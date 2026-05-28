<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    CampaignDetail,
    LeadListItem,
    PaginatedResponse,
  } from "$lib/types";

  let {
    campaignId: campaignIdProp = null,
    embedded = false,
  }: {
    campaignId?: number | string | null;
    embedded?: boolean;
  } = $props();

  const id = $derived(String(campaignIdProp ?? $page.params.id ?? ""));

  let campaign = $state<CampaignDetail | null>(null);
  let loading = $state(true);
  let activeTab = $state<"overview" | "recipients" | "content">("overview");

  // Edit slide-over
  let showEditSlideOver = $state(false);
  let editSaving = $state(false);
  let sourceOptions = $state<any[]>([]);
  let templateOptions = $state<any[]>([]);
  let editForm = $state({
    name: "",
    description: "",
    campaign_type: "",
    channel: "",
    notification_template: "",
    scheduled_at: "",
    target_pipeline_stages: [] as string[],
    target_lead_sources: [] as number[],
    target_lead_types: [] as string[],
    auto_create_leads_on_launch: false,
    auto_create_leads_count: "0",
    auto_create_lead_type: "buyer",
    spend_amount: "",
    revenue_attributed: "",
  });

  // Delete confirmation
  let showDeleteModal = $state(false);
  let deleting = $state(false);

  // Add recipients modal
  let showAddRecipientsModal = $state(false);
  let availableLeads = $state<LeadListItem[]>([]);
  let selectedLeadIds = $state<number[]>([]);
  let loadingLeads = $state(false);
  let addingRecipients = $state(false);

  // Content editing
  let contentForm = $state({ subject: "", body: "" });
  let savingContent = $state(false);

  // Action loading states
  let actionLoading = $state(false);

  const campaignTypeLabels: Record<string, string> = {
    email_blast: "Email Blast",
    whatsapp_campaign: "WhatsApp Campaign",
    sms_blast: "SMS Blast",
    digital_ads: "Digital Ads",
    drip: "Drip Campaign",
    follow_up: "Follow-Up",
  };

  const channelLabels: Record<string, string> = {
    email: "Email",
    whatsapp: "WhatsApp",
    sms: "SMS",
    in_app: "In-App",
    phone: "Phone",
    video_call: "Video Call",
    in_person: "In Person",
    other: "Other",
  };

  const tabs = [
    { key: "overview" as const, label: "Overview" },
    { key: "recipients" as const, label: "Recipients" },
    { key: "content" as const, label: "Content" },
  ];
  const leadTypeOptions = [
    { value: "buyer", label: "Home Buyers" },
    { value: "investor", label: "Investors" },
    { value: "tenant", label: "Tenants" },
  ] as const;
  const stageOptions = [
    { value: "inquiry", label: "Inquiry" },
    { value: "qualified", label: "Qualified" },
    { value: "site_visit", label: "Site Visit" },
    { value: "offer_made", label: "Offer Made" },
    { value: "reservation", label: "Reservation" },
    { value: "spa_issued", label: "SPA Issued" },
    { value: "closed", label: "Closed" },
  ] as const;

  function fmtDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function fmtDateTime(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function fmtLabel(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return value.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  function apiErrorDetail(err: unknown): string {
    if (err instanceof ApiError && err.fieldErrors) {
      const msgs = Object.entries(err.fieldErrors)
        .map(([field, errors]) => `${field}: ${errors[0]}`)
        .slice(0, 2);
      if (msgs.length) return msgs.join(". ");
    }
    if (err instanceof ApiError) {
      const detail = (err.data as Record<string, unknown>)?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      if (err.status === 403) return "You do not have permission for this action";
      if (err.status === 404) return "Resource not found";
    }
    return "Please try again later";
  }

  // --- Data loading ---

  $effect(() => {
    void id;
    loadCampaign();
  });

  async function loadCampaign() {
    loading = true;
    if (sourceOptions.length === 0) {
      try {
        const sourceRes = await api.get<PaginatedResponse<any>>("/crm/sources/", {
          is_active: "true",
          page_size: "200",
        });
        sourceOptions = sourceRes.results ?? [];
      } catch {
        sourceOptions = [];
      }
    }
    if (templateOptions.length === 0) {
      try {
        const templateRes = await api.get<PaginatedResponse<any>>(
          "/settings/notifications/templates/",
          {
            is_active: "true",
            page_size: "200",
          },
        );
        templateOptions = templateRes.results ?? [];
      } catch {
        templateOptions = [];
      }
    }
    try {
      const data = await api.get<CampaignDetail>(`/crm/campaigns/${id}/`);
      campaign = data;
      syncEditForm(data);
      syncContentForm(data);
    } catch {
      campaign = null;
    }
    loading = false;
  }

  function syncEditForm(c: CampaignDetail) {
    editForm = {
      name: c.name,
      description: c.description,
      campaign_type: c.campaign_type,
      channel: c.channel,
      notification_template: c.notification_template ? String(c.notification_template) : "",
      scheduled_at: c.scheduled_at ?? "",
      target_pipeline_stages: [...(c.target_pipeline_stages ?? [])],
      target_lead_sources: [...(c.target_lead_sources ?? [])],
      target_lead_types: [...(c.target_lead_types ?? [])],
      auto_create_leads_on_launch: Boolean(c.auto_create_leads_on_launch),
      auto_create_leads_count: String(c.auto_create_leads_count ?? 0),
      auto_create_lead_type: c.auto_create_lead_type ?? "buyer",
      spend_amount: c.spend_amount ?? "",
      revenue_attributed: c.revenue_attributed ?? "",
    };
  }

  function syncContentForm(c: CampaignDetail) {
    contentForm = {
      subject: c.subject ?? "",
      body: c.body ?? "",
    };
  }

  // --- Computed metrics ---

  const totalRecipients = $derived(campaign?.total_recipients ?? 0);
  const sentCount = $derived(campaign?.sent_count ?? 0);
  const deliveredCount = $derived(campaign?.delivered_count ?? 0);
  const openedCount = $derived(campaign?.opened_count ?? 0);
  const clickedCount = $derived(campaign?.clicked_count ?? 0);
  const failedCount = $derived(campaign?.failed_count ?? 0);
  const deliveryRate = $derived(campaign?.delivery_rate ?? 0);
  const openRate = $derived(campaign?.open_rate ?? 0);
  const clickRate = $derived(campaign?.click_rate ?? 0);
  const roiPercent = $derived(campaign?.roi_percent ?? 0);

  function toggleEditLeadType(leadType: string) {
    if (editForm.target_lead_types.includes(leadType)) {
      editForm.target_lead_types = editForm.target_lead_types.filter((item) => item !== leadType);
      return;
    }
    editForm.target_lead_types = [...editForm.target_lead_types, leadType];
  }

  function toggleEditStage(stage: string) {
    if (editForm.target_pipeline_stages.includes(stage)) {
      editForm.target_pipeline_stages = editForm.target_pipeline_stages.filter((item) => item !== stage);
      return;
    }
    editForm.target_pipeline_stages = [...editForm.target_pipeline_stages, stage];
  }

  function toggleEditLeadSource(sourceId: number) {
    if (editForm.target_lead_sources.includes(sourceId)) {
      editForm.target_lead_sources = editForm.target_lead_sources.filter((item) => item !== sourceId);
      return;
    }
    editForm.target_lead_sources = [...editForm.target_lead_sources, sourceId];
  }

  // --- Actions ---

  async function launchCampaign() {
    actionLoading = true;
    try {
      await api.post(`/crm/campaigns/${id}/launch/`, {});
      toast.success("Campaign launched", "The campaign is now running");
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to launch campaign", apiErrorDetail(err));
    } finally {
      actionLoading = false;
    }
  }

  async function pauseCampaign() {
    actionLoading = true;
    try {
      await api.post(`/crm/campaigns/${id}/pause/`, {});
      toast.success("Campaign paused", "The campaign has been paused");
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to pause campaign", apiErrorDetail(err));
    } finally {
      actionLoading = false;
    }
  }

  async function completeCampaign() {
    actionLoading = true;
    try {
      await api.post(`/crm/campaigns/${id}/complete/`, {});
      toast.success("Campaign completed", "The campaign has been marked as completed");
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to complete campaign", apiErrorDetail(err));
    } finally {
      actionLoading = false;
    }
  }

  async function deleteCampaign() {
    deleting = true;
    try {
      await api.delete(`/crm/campaigns/${id}/`);
      toast.success("Campaign deleted", "The campaign has been permanently removed");
      goto("/crm/communications");
    } catch (err) {
      toast.error("Failed to delete campaign", apiErrorDetail(err));
    } finally {
      deleting = false;
      showDeleteModal = false;
    }
  }

  // --- Edit slide-over ---

  function openEditSlideOver() {
    if (campaign) syncEditForm(campaign);
    showEditSlideOver = true;
  }

  async function saveEdit() {
    editSaving = true;
    try {
      const payload: Record<string, unknown> = {
        name: editForm.name,
        description: editForm.description,
        campaign_type: editForm.campaign_type,
        channel: editForm.channel,
        notification_template: editForm.notification_template
          ? Number(editForm.notification_template)
          : null,
        target_pipeline_stages: editForm.target_pipeline_stages,
        target_lead_sources: editForm.target_lead_sources,
        target_lead_types: editForm.target_lead_types,
        auto_create_leads_on_launch: editForm.auto_create_leads_on_launch,
        auto_create_leads_count: Number(editForm.auto_create_leads_count || "0"),
        auto_create_lead_type: editForm.auto_create_lead_type,
        spend_amount: editForm.spend_amount || "0",
        revenue_attributed: editForm.revenue_attributed || "0",
        scheduled_at: editForm.scheduled_at || null,
      };
      if (!editForm.auto_create_leads_on_launch) payload.auto_create_leads_count = 0;
      await api.patch<CampaignDetail>(`/crm/campaigns/${id}/`, payload);
      toast.success("Campaign updated", "Changes have been saved");
      showEditSlideOver = false;
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to save campaign", apiErrorDetail(err));
    } finally {
      editSaving = false;
    }
  }

  // --- Add Recipients ---

  async function openAddRecipientsModal() {
    showAddRecipientsModal = true;
    selectedLeadIds = [];
    loadingLeads = true;
    try {
      const res = await api.get<PaginatedResponse<LeadListItem>>("/crm/leads/", { status: "active", page_size: "200" });
      availableLeads = res.results;
    } catch {
      availableLeads = [];
      toast.error("Failed to load leads", "Could not fetch active leads");
    } finally {
      loadingLeads = false;
    }
  }

  function toggleLeadSelection(leadId: number) {
    if (selectedLeadIds.includes(leadId)) {
      selectedLeadIds = selectedLeadIds.filter((lid) => lid !== leadId);
    } else {
      selectedLeadIds = [...selectedLeadIds, leadId];
    }
  }

  async function addSelectedRecipients() {
    if (selectedLeadIds.length === 0) return;
    addingRecipients = true;
    try {
      await api.post(`/crm/campaigns/${id}/add_recipients/`, { lead_ids: selectedLeadIds });
      toast.success("Recipients added", `${selectedLeadIds.length} lead(s) added to this campaign`);
      showAddRecipientsModal = false;
      selectedLeadIds = [];
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to add recipients", apiErrorDetail(err));
    } finally {
      addingRecipients = false;
    }
  }

  // --- Content editing ---

  async function saveContent() {
    savingContent = true;
    try {
      await api.patch<CampaignDetail>(`/crm/campaigns/${id}/`, {
        subject: contentForm.subject,
        body: contentForm.body,
      });
      toast.success("Content saved", "Campaign content has been updated");
      await loadCampaign();
    } catch (err) {
      toast.error("Failed to save content", apiErrorDetail(err));
    } finally {
      savingContent = false;
    }
  }

  // Determine which action buttons to show based on status
  const canLaunch = $derived(
    campaign?.status === "draft" || campaign?.status === "scheduled" || campaign?.status === "paused"
  );
  const canPause = $derived(campaign?.status === "running");
  const canComplete = $derived(
    campaign?.status === "running" || campaign?.status === "paused"
  );
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !campaign}
  <div class="py-24 text-center">
    <p class="text-neutral-400 text-sm">Campaign not found</p>
    <a href="/crm/communications" class="inline-block mt-3 text-sm font-medium text-neutral-900 hover:underline">Back to Communications</a>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-6">
    {#if !embedded}
      <Breadcrumb items={[
        { label: "CRM", href: "/crm" },
        { label: "Communications", href: "/crm/communications" },
        { label: "Campaigns", href: "/crm/communications" },
        { label: campaign.name },
      ]} />
    {/if}

    <div class="flex items-start justify-between {embedded ? '' : 'mt-3'}">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">{campaign.name}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <p class="text-sm text-neutral-400 mt-1">
          {campaignTypeLabels[campaign.campaign_type] ?? campaign.campaign_type}
          <span class="mx-1.5">&middot;</span>
          {channelLabels[campaign.channel] ?? campaign.channel}
          {#if campaign.created_by_name}
            <span class="mx-1.5">&middot;</span>
            Created by {campaign.created_by_name}
          {/if}
        </p>
      </div>

      <div class="flex gap-2">
        <button
          onclick={openEditSlideOver}
          class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >
          Edit
        </button>

        {#if canLaunch}
          <button
            onclick={launchCampaign}
            disabled={actionLoading}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {actionLoading ? "Launching..." : "Launch"}
          </button>
        {/if}

        {#if canPause}
          <button
            onclick={pauseCampaign}
            disabled={actionLoading}
            class="px-4 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 transition-colors"
          >
            {actionLoading ? "Pausing..." : "Pause"}
          </button>
        {/if}

        {#if canComplete}
          <button
            onclick={completeCampaign}
            disabled={actionLoading}
            class="px-4 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 transition-colors"
          >
            {actionLoading ? "Completing..." : "Complete"}
          </button>
        {/if}

        <button
          onclick={() => (showDeleteModal = true)}
          class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-500 hover:text-neutral-900 hover:bg-neutral-50 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="border-b border-neutral-200 mb-6">
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
          {#if tab.key === "recipients" && totalRecipients > 0}
            <span class="ml-1.5 text-xs text-neutral-400">{totalRecipients}</span>
          {/if}
        </button>
      {/each}
    </nav>
  </div>

  <!-- TAB: Overview -->
  {#if activeTab === "overview"}
    <div class="space-y-6">
      <!-- Campaign Info Card -->
      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Campaign Details</h3>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between"><span class="text-neutral-400">Name</span><span class="text-neutral-900">{campaign.name}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Type</span><span class="text-neutral-900">{campaignTypeLabels[campaign.campaign_type] ?? campaign.campaign_type}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Channel</span><span class="text-neutral-900">{channelLabels[campaign.channel] ?? campaign.channel}</span></div>
            <div class="flex justify-between">
              <span class="text-neutral-400">Status</span>
              <StatusBadge status={campaign.status} />
            </div>
            <div class="flex justify-between"><span class="text-neutral-400">Scheduled At</span><span class="text-neutral-900">{fmtDateTime(campaign.scheduled_at)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Started At</span><span class="text-neutral-900">{fmtDateTime(campaign.started_at)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Completed At</span><span class="text-neutral-900">{fmtDateTime(campaign.completed_at)}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Created By</span><span class="text-neutral-900">{campaign.created_by_name ?? "\u2014"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Lead Types</span><span class="text-neutral-900">{campaign.target_lead_types.length ? campaign.target_lead_types.map((item) => fmtLabel(item)).join(", ") : "\u2014"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Auto Leads</span><span class="text-neutral-900 tabular-nums">{campaign.auto_created_leads_count}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Spend</span><span class="text-neutral-900 tabular-nums">{campaign.spend_amount ?? "0.00"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">Attributed Revenue</span><span class="text-neutral-900 tabular-nums">{campaign.revenue_attributed ?? "0.00"}</span></div>
            <div class="flex justify-between"><span class="text-neutral-400">ROI</span><span class="text-neutral-900 tabular-nums">{roiPercent.toFixed(1)}%</span></div>
          </div>
          {#if campaign.description}
            <div class="pt-3 border-t border-neutral-100">
              <span class="text-xs font-medium text-neutral-400 uppercase tracking-wider block mb-1">Description</span>
              <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{campaign.description}</p>
            </div>
          {/if}
        </div>

        <!-- Template Info -->
        <div class="space-y-6">
          {#if campaign.notification_template}
            <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Linked Template</h3>
              <div class="space-y-3 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">Template</span><span class="text-neutral-900">{campaign.template_name ?? "\u2014"}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Template ID</span><span class="text-neutral-900 tabular-nums">#{campaign.notification_template}</span></div>
              </div>
            </div>
          {/if}

          <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Dates</h3>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between"><span class="text-neutral-400">Created</span><span class="text-neutral-900">{fmtDate(campaign.created_at)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Last Updated</span><span class="text-neutral-900">{fmtDate(campaign.updated_at)}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Metrics Strip -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Metrics</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4">
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Recipients</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{totalRecipients}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Sent</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{sentCount}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Delivered</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{deliveredCount}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Opened</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{openedCount}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Clicked</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{clickedCount}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Failed</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{failedCount}</p>
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">ROI</p>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums mt-1">{roiPercent.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      <!-- Rate Bars -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Performance Rates</h3>
        <div class="space-y-5">
          <!-- Delivery Rate -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-sm text-neutral-600">Delivery Rate</span>
              <span class="text-sm font-semibold text-neutral-900 tabular-nums">{deliveryRate.toFixed(1)}%</span>
            </div>
            <div class="w-full bg-neutral-100 rounded-full h-2.5">
              <div
                class="bg-neutral-900 h-2.5 rounded-full transition-all"
                style="width: {Math.min(deliveryRate, 100)}%"
              ></div>
            </div>
          </div>

          <!-- Open Rate -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-sm text-neutral-600">Open Rate</span>
              <span class="text-sm font-semibold text-neutral-900 tabular-nums">{openRate.toFixed(1)}%</span>
            </div>
            <div class="w-full bg-neutral-100 rounded-full h-2.5">
              <div
                class="bg-neutral-700 h-2.5 rounded-full transition-all"
                style="width: {Math.min(openRate, 100)}%"
              ></div>
            </div>
          </div>

          <!-- Click Rate -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-sm text-neutral-600">Click Rate</span>
              <span class="text-sm font-semibold text-neutral-900 tabular-nums">{clickRate.toFixed(1)}%</span>
            </div>
            <div class="w-full bg-neutral-100 rounded-full h-2.5">
              <div
                class="bg-neutral-500 h-2.5 rounded-full transition-all"
                style="width: {Math.min(clickRate, 100)}%"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- TAB: Recipients -->
  {#if activeTab === "recipients"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button
          onclick={openAddRecipientsModal}
          class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + Add Recipients
        </button>
      </div>

      {#if campaign.recipients.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">No recipients have been added to this campaign yet.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Lead Name</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Email</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Phone</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Sent At</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Delivered At</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Opened At</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Clicked At</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each campaign.recipients as recipient}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-4 py-2.5 text-neutral-900 font-medium">
                    <a href="/crm/leads/{recipient.lead}" class="hover:underline">{recipient.lead_name}</a>
                  </td>
                  <td class="px-4 py-2.5 text-neutral-500">{recipient.lead_email || "\u2014"}</td>
                  <td class="px-4 py-2.5 text-neutral-500">{recipient.lead_phone || "\u2014"}</td>
                  <td class="px-4 py-2.5">
                    <StatusBadge status={recipient.status} label={recipient.status_display} />
                  </td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{fmtDateTime(recipient.sent_at)}</td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{fmtDateTime(recipient.delivered_at)}</td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{fmtDateTime(recipient.opened_at)}</td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{fmtDateTime(recipient.clicked_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  <!-- TAB: Content -->
  {#if activeTab === "content"}
    <div class="grid lg:grid-cols-2 gap-6">
      <!-- Editor -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Edit Content</h3>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Subject</span>
          <input
            bind:value={contentForm.subject}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
            placeholder="Campaign subject line"
          />
        </label>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Body</span>
          <textarea
            bind:value={contentForm.body}
            rows={16}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
            placeholder="Write your campaign content here..."
          ></textarea>
        </label>

        <div class="flex justify-end">
          <button
            onclick={saveContent}
            disabled={savingContent}
            class="inline-flex items-center px-5 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {#if savingContent}
              <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
            {/if}
            Save Content
          </button>
        </div>
      </div>

      <!-- Preview -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Preview</h3>

        {#if contentForm.subject || contentForm.body}
          <div class="border border-neutral-200 rounded-lg overflow-hidden">
            <!-- Subject header -->
            <div class="bg-neutral-50 border-b border-neutral-200 px-4 py-3">
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-0.5">Subject</p>
              <p class="text-sm font-medium text-neutral-900">{contentForm.subject || "(No subject)"}</p>
            </div>

            <!-- Body -->
            <div class="px-4 py-4">
              <p class="text-sm text-neutral-700 leading-relaxed whitespace-pre-line">{contentForm.body || "(No content)"}</p>
            </div>
          </div>
        {:else}
          <div class="border border-neutral-200 rounded-lg p-8 text-center">
            <p class="text-neutral-400 text-sm">No content to preview. Start editing to see a live preview.</p>
          </div>
        {/if}

        {#if campaign.notification_template}
          <div class="bg-neutral-50 rounded-lg border border-neutral-100 p-3">
            <p class="text-xs text-neutral-500">
              This campaign uses notification template: <span class="font-medium text-neutral-700">{campaign.template_name ?? `#${campaign.notification_template}`}</span>
            </p>
          </div>
        {/if}
      </div>
    </div>
  {/if}
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-neutral-900/50"
      onclick={() => (showDeleteModal = false)}
      aria-label="Close modal"
    ></button>

    <div class="relative bg-white rounded-xl border border-neutral-200 p-6 w-full max-w-md shadow-lg">
      <h3 class="text-lg font-semibold text-neutral-900 mb-2">Delete Campaign</h3>
      <p class="text-sm text-neutral-500 mb-6">
        Are you sure you want to delete this campaign? This action cannot be undone. All recipient data and metrics will be permanently removed.
      </p>
      <div class="flex justify-end gap-3">
        <button
          onclick={() => (showDeleteModal = false)}
          class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={deleteCampaign}
          disabled={deleting}
          class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {deleting ? "Deleting..." : "Delete Campaign"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Edit Slide-Over -->
{#if showEditSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-neutral-900/50"
      onclick={() => (showEditSlideOver = false)}
      aria-label="Close slide-over"
    ></button>

    <div class="relative bg-white w-full max-w-lg h-full overflow-y-auto shadow-xl">
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-neutral-900">Edit Campaign</h2>
          <button
            onclick={() => (showEditSlideOver = false)}
            class="text-neutral-400 hover:text-neutral-900 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Name</span>
          <input
            bind:value={editForm.name}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
            placeholder="Campaign name"
          />
        </label>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Description</span>
          <textarea
            bind:value={editForm.description}
            rows={3}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
            placeholder="Campaign description"
          ></textarea>
        </label>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Campaign Type</span>
          <select
            bind:value={editForm.campaign_type}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="email_blast">Email Blast</option>
            <option value="whatsapp_campaign">WhatsApp Campaign</option>
            <option value="sms_blast">SMS Blast</option>
            <option value="digital_ads">Digital Ads</option>
            <option value="drip">Drip Campaign</option>
            <option value="follow_up">Follow-Up</option>
          </select>
        </label>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Channel</span>
          <select
            bind:value={editForm.channel}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="email">Email</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="sms">SMS</option>
            <option value="in_app">In-App</option>
            <option value="phone">Phone</option>
            <option value="video_call">Video Call</option>
            <option value="in_person">In Person</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label class="block">
          <div class="mb-1 flex items-center justify-between">
            <span class="block text-xs font-medium text-neutral-500">Template</span>
            <a href="/settings/notifications" class="text-xs text-neutral-500 hover:text-neutral-900 hover:underline">Manage templates</a>
          </div>
          <select
            bind:value={editForm.notification_template}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="">No linked template</option>
            {#each templateOptions.filter((template) => !editForm.channel || template.channel === editForm.channel) as template}
              <option value={String(template.id)}>{template.name} ({fmtLabel(template.channel)})</option>
            {/each}
          </select>
        </label>

        <div class="rounded-lg border border-neutral-200 p-4 space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Segmentation</h3>
          <div>
            <span class="block text-xs font-medium text-neutral-500 mb-2">Lead Types</span>
            <div class="flex flex-wrap gap-2">
              {#each leadTypeOptions as option}
                <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs text-neutral-700">
                  <input
                    type="checkbox"
                    checked={editForm.target_lead_types.includes(option.value)}
                    onchange={() => toggleEditLeadType(option.value)}
                    class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                  />
                  {option.label}
                </label>
              {/each}
            </div>
          </div>
          <div>
            <span class="block text-xs font-medium text-neutral-500 mb-2">Pipeline Stages</span>
            <div class="grid grid-cols-2 gap-2">
              {#each stageOptions as option}
                <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs text-neutral-700">
                  <input
                    type="checkbox"
                    checked={editForm.target_pipeline_stages.includes(option.value)}
                    onchange={() => toggleEditStage(option.value)}
                    class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                  />
                  {option.label}
                </label>
              {/each}
            </div>
          </div>
          <div>
            <span class="block text-xs font-medium text-neutral-500 mb-2">Lead Sources</span>
            {#if sourceOptions.length === 0}
              <p class="text-xs text-neutral-400">No active lead sources found.</p>
            {:else}
              <div class="grid grid-cols-2 gap-2">
                {#each sourceOptions as source}
                  <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs text-neutral-700">
                    <input
                      type="checkbox"
                      checked={editForm.target_lead_sources.includes(source.id)}
                      onchange={() => toggleEditLeadSource(source.id)}
                      class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                    />
                    {source.name}
                  </label>
                {/each}
              </div>
            {/if}
          </div>
        </div>

        <div class="rounded-lg border border-neutral-200 p-4 space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">ROI Tracking</h3>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Spend</span>
              <input
                type="number"
                min="0"
                step="0.01"
                bind:value={editForm.spend_amount}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Attributed Revenue</span>
              <input
                type="number"
                min="0"
                step="0.01"
                bind:value={editForm.revenue_attributed}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </label>
          </div>
          <p class="text-xs text-neutral-500">Current ROI: {roiPercent.toFixed(1)}%</p>
        </div>

        <div class="rounded-lg border border-neutral-200 p-4 space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Automations</h3>
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input
              type="checkbox"
              bind:checked={editForm.auto_create_leads_on_launch}
              class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
            />
            Campaign launch auto-creates leads
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Leads To Create</span>
              <input
                type="number"
                min="0"
                bind:value={editForm.auto_create_leads_count}
                disabled={!editForm.auto_create_leads_on_launch}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 disabled:bg-neutral-50"
              />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Auto Lead Type</span>
              <select
                bind:value={editForm.auto_create_lead_type}
                disabled={!editForm.auto_create_leads_on_launch}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 disabled:bg-neutral-50"
              >
                <option value="buyer">Home Buyer</option>
                <option value="investor">Investor</option>
                <option value="tenant">Tenant</option>
              </select>
            </label>
          </div>
        </div>

        <label class="block">
          <span class="block text-xs font-medium text-neutral-500 mb-1">Scheduled At</span>
          <input
            type="datetime-local"
            bind:value={editForm.scheduled_at}
            class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>

        <div class="flex gap-3 pt-4 border-t border-neutral-200">
          <button
            onclick={saveEdit}
            disabled={editSaving}
            class="inline-flex items-center px-5 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {#if editSaving}
              <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
            {/if}
            Save Changes
          </button>
          <button
            onclick={() => (showEditSlideOver = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Add Recipients Modal -->
{#if showAddRecipientsModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-neutral-900/50"
      onclick={() => (showAddRecipientsModal = false)}
      aria-label="Close modal"
    ></button>

    <div class="relative bg-white rounded-xl border border-neutral-200 w-full max-w-2xl max-h-[80vh] flex flex-col shadow-lg">
      <div class="p-6 border-b border-neutral-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-neutral-900">Add Recipients</h3>
          <button
            onclick={() => (showAddRecipientsModal = false)}
            class="text-neutral-400 hover:text-neutral-900 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p class="text-sm text-neutral-400 mt-1">Select active leads to add as campaign recipients.</p>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        {#if loadingLeads}
          <div class="flex items-center justify-center py-12">
            <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
          </div>
        {:else if availableLeads.length === 0}
          <div class="py-12 text-center">
            <p class="text-neutral-400 text-sm">No active leads found.</p>
          </div>
        {:else}
          <div class="space-y-1">
            {#each availableLeads as lead}
              {@const isSelected = selectedLeadIds.includes(lead.id)}
              {@const alreadyRecipient = campaign?.recipients.some((r) => r.lead === lead.id) ?? false}
              <label
                class="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                       {alreadyRecipient ? 'opacity-40 cursor-not-allowed' : isSelected ? 'bg-neutral-100' : 'hover:bg-neutral-50'}"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  disabled={alreadyRecipient}
                  onchange={() => toggleLeadSelection(lead.id)}
                  class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                />
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-900 truncate">{lead.full_name}</p>
                  <p class="text-xs text-neutral-400 truncate">{lead.email || lead.phone || "No contact info"}</p>
                </div>
                {#if alreadyRecipient}
                  <span class="text-xs text-neutral-400">Already added</span>
                {/if}
              </label>
            {/each}
          </div>
        {/if}
      </div>

      <div class="p-6 border-t border-neutral-200 flex items-center justify-between">
        <span class="text-sm text-neutral-400">
          {selectedLeadIds.length} lead{selectedLeadIds.length !== 1 ? "s" : ""} selected
        </span>
        <div class="flex gap-3">
          <button
            onclick={() => (showAddRecipientsModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={addSelectedRecipients}
            disabled={selectedLeadIds.length === 0 || addingRecipients}
            class="inline-flex items-center px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {#if addingRecipients}
              <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
            {/if}
            Add Selected
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
