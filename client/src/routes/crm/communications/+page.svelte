<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import CampaignDetailPage from "../campaigns/[id]/+page.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type { PaginatedResponse } from "$lib/types";

  const pageSize = 25;

  type Tab = "communications" | "campaigns" | "followup" | "documents" | "meetings";
  let activeTab = $state<Tab>("communications");
  const tabs: { key: Tab; label: string }[] = [
    { key: "communications", label: "Communications Log" },
    { key: "campaigns", label: "Campaigns" },
    { key: "followup", label: "Follow-Up SLA" },
    { key: "documents", label: "Document Tracking" },
    { key: "meetings", label: "Meetings" },
  ];

  // --- Helpers ---
  function fmtDate(d: string | null): string {
    if (!d) return "\u2014";
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtDateTime(d: string | null): string {
    if (!d) return "\u2014";
    return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  }

  const chBadge: Record<string, string> = {
    email: "bg-neutral-200 text-neutral-600", whatsapp: "bg-neutral-300 text-neutral-700",
    in_app: "bg-neutral-900 text-white", phone: "bg-neutral-100 text-neutral-500", sms: "bg-neutral-100 text-neutral-400",
    video_call: "bg-neutral-400 text-neutral-800", in_person: "bg-neutral-500 text-white",
  };

  const stBadge: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-500", sent: "bg-neutral-200 text-neutral-700",
    delivered: "bg-neutral-300 text-neutral-800", read: "bg-neutral-600 text-white",
    received: "bg-neutral-700 text-white", failed: "bg-neutral-900 text-white",
    completed: "bg-neutral-800 text-white", pending: "bg-neutral-100 text-neutral-500",
    active: "bg-neutral-200 text-neutral-700", running: "bg-neutral-200 text-neutral-700", paused: "bg-neutral-300 text-neutral-600",
    cancelled: "bg-neutral-400 text-neutral-800", scheduled: "bg-neutral-100 text-neutral-600",
    overdue: "bg-neutral-700 text-white", escalated: "bg-neutral-900 text-white",
    confirmed: "bg-neutral-600 text-white", no_show: "bg-neutral-300 text-neutral-700",
    rescheduled: "bg-neutral-200 text-neutral-600",
  };

  function badge(map: Record<string, string>, key: string): string {
    return map[key] ?? "bg-neutral-100 text-neutral-600";
  }

  function lbl(s: string): string {
    return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  function breakdownCount(source: any, key: string): number {
    if (!source) return 0;
    if (Array.isArray(source)) {
      const row = source.find((item) => item?.channel === key || item?.direction === key);
      return Number(row?.count ?? 0);
    }
    if (typeof source === "object") return Number(source[key] ?? 0);
    return 0;
  }

  function fieldErr(errs: Record<string, string[]>, f: string): string {
    return errs[f]?.[0] ?? "";
  }

  function pgNums(cur: number, tot: number): number[] {
    const r: number[] = [], mx = 5;
    let s = Math.max(1, cur - Math.floor(mx / 2));
    let e = Math.min(tot, s + mx - 1);
    if (e - s + 1 < mx) s = Math.max(1, e - mx + 1);
    for (let i = s; i <= e; i++) r.push(i);
    return r;
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function deb(fn: () => void) { clearTimeout(debounceTimer); debounceTimer = setTimeout(fn, 300); }

  // ================================================
  // TAB 1: Communications Log
  // ================================================
  let commViewMode = $state<"logs" | "threads">("logs");
  let commListError = $state<string | null>(null);
  let campListError = $state<string | null>(null);
  let fuListError = $state<string | null>(null);
  let docListError = $state<string | null>(null);
  let meetListError = $state<string | null>(null);
  let commItems = $state<any[]>([]);
  let commCount = $state(0);
  let commLoading = $state(true);
  let commPage = $state(1);
  let commSearch = $state("");
  let commChannel = $state("");
  let commDirection = $state("");
  let commStatus = $state("");
  let commOverview = $state<any>(null);
  let showCommSlide = $state(false);
  let savingComm = $state(false);
  let commErrors = $state<Record<string, string[]>>({});
  let commDetail = $state<any>(null);
  let threadDetail = $state<any>(null);
  let threadMessages = $state<any[]>([]);
  let threadMessagesLoading = $state(false);
  let activeLeads = $state<any[]>([]);
  let commForm = $state({ lead: "", channel: "email", direction: "outbound", subject: "", body: "", summary: "", from_address: "", to_address: "", communicated_at: "" });
  let commPages = $derived(Math.max(1, Math.ceil(commCount / pageSize)));
  let threadItems = $state<any[]>([]);
  let threadCount = $state(0);
  let threadLoading = $state(true);
  let threadPage = $state(1);
  let threadPages = $derived(Math.max(1, Math.ceil(threadCount / pageSize)));

  // KPI from overview
  let kpiTotal = $derived(Number(commOverview?.total_communications ?? commOverview?.total ?? 0));
  let kpiInbound = $derived(breakdownCount(commOverview?.direction_breakdown, "inbound"));
  let kpiOutbound = $derived(breakdownCount(commOverview?.direction_breakdown, "outbound"));
  let kpiEmails = $derived(breakdownCount(commOverview?.channel_breakdown, "email"));
  let kpiCalls = $derived(breakdownCount(commOverview?.channel_breakdown, "phone"));
  let kpiWhatsapp = $derived(breakdownCount(commOverview?.channel_breakdown, "whatsapp"));
  let kpiInApp = $derived(breakdownCount(commOverview?.channel_breakdown, "in_app"));
  let kpiReminderSoon = $derived(Number(commOverview?.payment_reminders_due_soon ?? 0));
  let kpiReminderOverdue = $derived(Number(commOverview?.payment_reminders_overdue ?? 0));

  async function fetchOverview() {
    try { commOverview = await api.get("/crm/communications/overview/"); } catch (err) { console.error("[crm/communications]", err); commOverview = null; }
  }

  async function fetchComms() {
    commLoading = true;
    commListError = null;
    try {
      const p: Record<string, string> = { page: String(commPage), page_size: String(pageSize) };
      if (commSearch) p.search = commSearch;
      if (commChannel) p.channel = commChannel;
      if (commDirection) p.direction = commDirection;
      if (commStatus) p.status = commStatus;
      const res = await api.get<PaginatedResponse<any>>("/crm/communications/", p);
      commItems = res.results; commCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      commItems = []; commCount = 0;
      commListError = err instanceof Error ? err.message : "Could not load communications.";
    }
    commLoading = false;
  }

  async function fetchThreads() {
    threadLoading = true;
    commListError = null;
    try {
      const p: Record<string, string> = { page: String(threadPage), page_size: String(pageSize) };
      if (commSearch) p.search = commSearch;
      if (commChannel) p.channel = commChannel;
      if (commDirection) p.direction = commDirection;
      if (commStatus) p.status = commStatus;
      const res = await api.get<PaginatedResponse<any>>("/crm/communications/threads/", p);
      threadItems = res.results;
      threadCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      threadItems = [];
      threadCount = 0;
      commListError = err instanceof Error ? err.message : "Could not load communication threads.";
    }
    threadLoading = false;
  }

  async function openCommunicationDetail(entry: any) {
    commDetail = entry;
    if (!entry?.id) return;
    try {
      commDetail = await api.get(`/crm/communications/${entry.id}/`);
    } catch (err) {
      console.error("[crm/communications]", err);
      // Keep fallback list payload if detail fetch fails.
    }
  }

  async function openThreadDetail(thread: any) {
    threadDetail = thread;
    threadMessages = [];
    threadMessagesLoading = true;
    try {
      const res = await api.get<PaginatedResponse<any>>(
        `/crm/communications/threads/${thread.thread_key}/messages/`,
        { page_size: "200" },
      );
      threadMessages = res.results ?? [];
    } catch (err) {
      console.error("[crm/communications]", err);
      threadMessages = [];
    }
    threadMessagesLoading = false;
  }

  function closeThreadDetail() {
    threadDetail = null;
    threadMessages = [];
    threadMessagesLoading = false;
  }

  async function fetchLeads() {
    try {
      const res = await api.get<PaginatedResponse<any>>("/crm/leads/", { status: "active", page_size: "200" });
      activeLeads = res.results;
    } catch (err) { console.error("[crm/communications]", err); activeLeads = []; }
  }

  function resetCommForm() {
    commForm = { lead: "", channel: "email", direction: "outbound", subject: "", body: "", summary: "", from_address: "", to_address: "", communicated_at: "" };
    commErrors = {};
  }

  async function createComm(e: Event) {
    e.preventDefault(); savingComm = true; commErrors = {};
    try {
      const pl: Record<string, unknown> = { ...commForm, lead: Number(commForm.lead) };
      if (!commForm.communicated_at) delete pl.communicated_at;
      await api.post("/crm/communications/", pl);
      toast.success("Communication logged"); showCommSlide = false; resetCommForm(); fetchComms(); fetchOverview();
    } catch (err) {
      console.error("[crm/communications]", err);
      if (err instanceof ApiError) { commErrors = err.fieldErrors; toast.error("Validation error", "Please fix the highlighted fields"); }
      else toast.error("Error", "Could not save communication");
    }
    savingComm = false;
  }

  // ================================================
  // TAB 2: Campaigns
  // ================================================
  let campItems = $state<any[]>([]);
  let campCount = $state(0);
  let campLoading = $state(true);
  let campPage = $state(1);
  let campSearch = $state("");
  let campType = $state("");
  let campStat = $state("");
  let showCampSlide = $state(false);
  let savingCamp = $state(false);
  let campErrors = $state<Record<string, string[]>>({});
  let campLeadSources = $state<any[]>([]);
  let campTemplates = $state<any[]>([]);
  let campForm = $state({
    name: "",
    description: "",
    campaign_type: "email_blast",
    channel: "email",
    notification_template: "",
    subject: "",
    body: "",
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
  let campPages = $derived(Math.max(1, Math.ceil(campCount / pageSize)));
  let showCampaignDetailDrawer = $state(false);
  let selectedCampaignId = $state<number | null>(null);

  const campLeadTypeOptions = [
    { value: "buyer", label: "Home Buyers" },
    { value: "investor", label: "Investors" },
    { value: "tenant", label: "Tenants" },
  ] as const;
  const campStageOptions = [
    { value: "inquiry", label: "Inquiry" },
    { value: "qualified", label: "Qualified" },
    { value: "site_visit", label: "Site Visit" },
    { value: "offer_made", label: "Offer Made" },
    { value: "reservation", label: "Reservation" },
    { value: "spa_issued", label: "SPA Issued" },
    { value: "closed", label: "Closed" },
  ] as const;

  async function fetchCampLeadSources() {
    try {
      const res = await api.get<PaginatedResponse<any>>("/crm/sources/", {
        is_active: "true",
        page_size: "200",
      });
      campLeadSources = res.results ?? [];
    } catch (err) {
      console.error("[crm/communications]", err);
      campLeadSources = [];
    }
  }

  async function fetchCampTemplates() {
    try {
      const res = await api.get<PaginatedResponse<any>>("/settings/notifications/templates/", {
        is_active: "true",
        page_size: "200",
      });
      campTemplates = res.results ?? [];
    } catch (err) {
      console.error("[crm/communications]", err);
      campTemplates = [];
    }
  }

  function toggleCampStage(stage: string) {
    if (campForm.target_pipeline_stages.includes(stage)) {
      campForm.target_pipeline_stages = campForm.target_pipeline_stages.filter((item) => item !== stage);
      return;
    }
    campForm.target_pipeline_stages = [...campForm.target_pipeline_stages, stage];
  }

  function toggleCampLeadSource(sourceId: number) {
    if (campForm.target_lead_sources.includes(sourceId)) {
      campForm.target_lead_sources = campForm.target_lead_sources.filter((item) => item !== sourceId);
      return;
    }
    campForm.target_lead_sources = [...campForm.target_lead_sources, sourceId];
  }

  function toggleCampLeadType(leadType: string) {
    if (campForm.target_lead_types.includes(leadType)) {
      campForm.target_lead_types = campForm.target_lead_types.filter((item) => item !== leadType);
      return;
    }
    campForm.target_lead_types = [...campForm.target_lead_types, leadType];
  }

  async function fetchCamps() {
    campLoading = true;
    campListError = null;
    try {
      const p: Record<string, string> = { page: String(campPage), page_size: String(pageSize) };
      if (campSearch) p.search = campSearch;
      if (campType) p.campaign_type = campType;
      if (campStat) p.status = campStat;
      const res = await api.get<PaginatedResponse<any>>("/crm/campaigns/", p);
      campItems = res.results; campCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      campItems = []; campCount = 0;
      campListError = err instanceof Error ? err.message : "Could not load campaigns.";
    }
    campLoading = false;
  }

  function resetCampForm() {
    campForm = {
      name: "",
      description: "",
      campaign_type: "email_blast",
      channel: "email",
      notification_template: "",
      subject: "",
      body: "",
      scheduled_at: "",
      target_pipeline_stages: [],
      target_lead_sources: [],
      target_lead_types: [],
      auto_create_leads_on_launch: false,
      auto_create_leads_count: "0",
      auto_create_lead_type: "buyer",
      spend_amount: "",
      revenue_attributed: "",
    };
    campErrors = {};
  }

  async function createCamp(e: Event) {
    e.preventDefault(); savingCamp = true; campErrors = {};
    try {
      const pl: Record<string, unknown> = {
        ...campForm,
        auto_create_leads_count: Number(campForm.auto_create_leads_count || "0"),
        spend_amount: campForm.spend_amount || "0",
        revenue_attributed: campForm.revenue_attributed || "0",
      };
      pl.notification_template = campForm.notification_template ? Number(campForm.notification_template) : null;
      if (!campForm.auto_create_leads_on_launch) pl.auto_create_leads_count = 0;
      if (!campForm.scheduled_at) delete pl.scheduled_at;
      const r = await api.post<any>("/crm/campaigns/", pl);
      toast.success("Campaign created", r.name); showCampSlide = false; resetCampForm(); fetchCamps();
    } catch (err) {
      console.error("[crm/communications]", err);
      if (err instanceof ApiError) { campErrors = err.fieldErrors; toast.error("Validation error"); }
      else toast.error("Error", "Could not create campaign");
    }
    savingCamp = false;
  }

  function openCampaignDetailDrawer(campaignId: number, syncUrl = true) {
    selectedCampaignId = campaignId;
    showCampaignDetailDrawer = true;
    if (!syncUrl) return;
    const params = new URLSearchParams($page.url.searchParams);
    params.set("tab", "campaigns");
    params.set("campaign", String(campaignId));
    goto(`/crm/communications?${params.toString()}`, {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    });
  }

  function closeCampaignDetailDrawer() {
    showCampaignDetailDrawer = false;
    selectedCampaignId = null;
    if (!$page.url.searchParams.has("campaign")) return;
    const params = new URLSearchParams($page.url.searchParams);
    params.delete("campaign");
    const query = params.toString();
    goto(query ? `/crm/communications?${query}` : "/crm/communications", {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    });
  }

  // ================================================
  // TAB 3: Follow-Up SLA
  // ================================================
  let fuRules = $state<any[]>([]);
  let fuRulesLoading = $state(true);
  let fuTasks = $state<any[]>([]);
  let fuTaskCount = $state(0);
  let fuTaskLoading = $state(true);
  let fuTaskPage = $state(1);
  let fuTaskStat = $state("");
  let showRuleSlide = $state(false);
  let savingRule = $state(false);
  let ruleErrors = $state<Record<string, string[]>>({});
  let editingRule = $state<any>(null);
  let ruleForm = $state({ name: "", trigger_stage: "inquiry", follow_up_within_hours: "24", required_activity_type: "call", is_active: true });
  let fuTaskPages = $derived(Math.max(1, Math.ceil(fuTaskCount / pageSize)));

  async function fetchRules() {
    fuRulesLoading = true;
    fuListError = null;
    try {
      fuRules = await api.get<any[]>("/crm/follow-up-rules/");
    } catch (err) {
      console.error("[crm/communications]", err);
      fuRules = [];
      fuListError = err instanceof Error ? err.message : "Could not load follow-up rules.";
    }
    fuRulesLoading = false;
  }

  async function fetchTasks() {
    fuTaskLoading = true;
    fuListError = null;
    try {
      const p: Record<string, string> = { page: String(fuTaskPage), page_size: String(pageSize) };
      if (fuTaskStat) p.status = fuTaskStat;
      const res = await api.get<PaginatedResponse<any>>("/crm/follow-up-tasks/", p);
      fuTasks = res.results; fuTaskCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      fuTasks = []; fuTaskCount = 0;
      fuListError = err instanceof Error ? err.message : "Could not load follow-up tasks.";
    }
    fuTaskLoading = false;
  }

  function resetRuleForm() {
    ruleForm = { name: "", trigger_stage: "inquiry", follow_up_within_hours: "24", required_activity_type: "call", is_active: true };
    ruleErrors = {}; editingRule = null;
  }

  function editRule(rule: any) {
    editingRule = rule;
    ruleForm = { name: rule.name, trigger_stage: rule.trigger_stage, follow_up_within_hours: String(rule.follow_up_within_hours), required_activity_type: rule.required_activity_type, is_active: rule.is_active };
    showRuleSlide = true;
  }

  async function saveRule(e: Event) {
    e.preventDefault(); savingRule = true; ruleErrors = {};
    try {
      const pl = { ...ruleForm, follow_up_within_hours: Number(ruleForm.follow_up_within_hours) };
      if (editingRule) { await api.patch(`/crm/follow-up-rules/${editingRule.id}/`, pl); toast.success("Rule updated"); }
      else { await api.post("/crm/follow-up-rules/", pl); toast.success("Rule created"); }
      showRuleSlide = false; resetRuleForm(); fetchRules();
    } catch (err) {
      console.error("[crm/communications]", err);
      if (err instanceof ApiError) { ruleErrors = err.fieldErrors; toast.error("Validation error"); }
      else toast.error("Error", "Could not save rule");
    }
    savingRule = false;
  }

  async function completeTask(id: number) {
    try { await api.post(`/crm/follow-up-tasks/${id}/complete_task/`, {}); toast.success("Task completed"); fetchTasks(); }
    catch { toast.error("Error", "Could not complete task"); }
  }

  async function escalateTask(id: number) {
    try { await api.post(`/crm/follow-up-tasks/${id}/escalate/`, {}); toast.success("Task escalated"); fetchTasks(); }
    catch { toast.error("Error", "Could not escalate task"); }
  }

  // ================================================
  // TAB 4: Document Tracking
  // ================================================
  let docEvents = $state<any[]>([]);
  let docCount = $state(0);
  let docLoading = $state(true);
  let docPage = $state(1);
  let docSearch = $state("");
  let docType = $state("");
  let showDocSlide = $state(false);
  let savingDoc = $state(false);
  let docErrors = $state<Record<string, string[]>>({});
  let docForm = $state({ lead: "", event_type: "sent", document_name: "", delivered_via: "", delivered_to: "", notes: "" });
  let docPages = $derived(Math.max(1, Math.ceil(docCount / pageSize)));

  async function fetchDocs() {
    docLoading = true;
    docListError = null;
    try {
      const p: Record<string, string> = { page: String(docPage), page_size: String(pageSize) };
      if (docSearch) p.search = docSearch;
      if (docType) p.event_type = docType;
      const res = await api.get<PaginatedResponse<any>>("/crm/document-events/", p);
      docEvents = res.results; docCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      docEvents = []; docCount = 0;
      docListError = err instanceof Error ? err.message : "Could not load document events.";
    }
    docLoading = false;
  }

  function resetDocForm() {
    docForm = { lead: "", event_type: "sent", document_name: "", delivered_via: "", delivered_to: "", notes: "" };
    docErrors = {};
  }

  async function createDoc(e: Event) {
    e.preventDefault(); savingDoc = true; docErrors = {};
    try {
      await api.post("/crm/document-events/", { ...docForm, lead: Number(docForm.lead) });
      toast.success("Document event recorded"); showDocSlide = false; resetDocForm(); fetchDocs();
    } catch (err) {
      console.error("[crm/communications]", err);
      if (err instanceof ApiError) { docErrors = err.fieldErrors; toast.error("Validation error"); }
      else toast.error("Error", "Could not save event");
    }
    savingDoc = false;
  }

  // ================================================
  // TAB 5: Meetings
  // ================================================
  let meetItems = $state<any[]>([]);
  let meetCount = $state(0);
  let meetLoading = $state(true);
  let meetPage = $state(1);
  let meetSearch = $state("");
  let meetType = $state("");
  let meetOutcome = $state("");
  let showMeetSlide = $state(false);
  let savingMeet = $state(false);
  let meetErrors = $state<Record<string, string[]>>({});
  let meetForm = $state({ lead: "", title: "", meeting_type: "site_visit", scheduled_start: "", scheduled_end: "", location: "", meeting_link: "", agenda: "" });
  let meetPages = $derived(Math.max(1, Math.ceil(meetCount / pageSize)));

  async function fetchMeets() {
    meetLoading = true;
    meetListError = null;
    try {
      const p: Record<string, string> = { page: String(meetPage), page_size: String(pageSize) };
      if (meetSearch) p.search = meetSearch;
      if (meetType) p.meeting_type = meetType;
      if (meetOutcome) p.outcome = meetOutcome;
      const res = await api.get<PaginatedResponse<any>>("/crm/meetings/", p);
      meetItems = res.results; meetCount = res.count;
    } catch (err) {
      console.error("[crm/communications]", err);
      meetItems = []; meetCount = 0;
      meetListError = err instanceof Error ? err.message : "Could not load meetings.";
    }
    meetLoading = false;
  }

  function resetMeetForm() {
    meetForm = { lead: "", title: "", meeting_type: "site_visit", scheduled_start: "", scheduled_end: "", location: "", meeting_link: "", agenda: "" };
    meetErrors = {};
  }

  async function createMeet(e: Event) {
    e.preventDefault(); savingMeet = true; meetErrors = {};
    try {
      const pl: Record<string, unknown> = { ...meetForm, lead: Number(meetForm.lead) };
      if (!meetForm.scheduled_end) delete pl.scheduled_end;
      await api.post("/crm/meetings/", pl);
      toast.success("Meeting created"); showMeetSlide = false; resetMeetForm(); fetchMeets();
    } catch (err) {
      console.error("[crm/communications]", err);
      if (err instanceof ApiError) { meetErrors = err.fieldErrors; toast.error("Validation error"); }
      else toast.error("Error", "Could not create meeting");
    }
    savingMeet = false;
  }

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const COMM_SAMPLES = [
    { channel: "email", direction: "outbound", subject: "Follow-up: Lekki Phase 3 Unit Tour", body: "Dear Mr. Ogundimu, thank you for visiting our Lekki Phase 3 development last Friday. As discussed, I have attached the floor plans for Units 12-16 in Block A. Please let me know a convenient time to discuss the payment options.", summary: "Sent follow-up after site visit", from_address: "sales@devco.ng", to_address: "tunde@ogundimugroup.com" },
    { channel: "phone", direction: "inbound", subject: "Pricing inquiry — Ikoyi Waterfront", body: "Client called to ask about current pricing for 3-bed units at Ikoyi Waterfront. Quoted range of N85M-N120M depending on floor and view. Client requested brochure by email.", summary: "Inbound pricing call, brochure requested", from_address: "+2348081234572", to_address: "+2348031234567" },
    { channel: "whatsapp", direction: "outbound", subject: "Payment plan options — Eko Atlantic", body: "Good afternoon Mrs. Bello. Following our conversation, here are the three payment plan structures for Eko Atlantic Tower B: (1) 100% upfront with 5% discount, (2) 60/40 split over 12 months, (3) 30/30/40 over 18 months.", summary: "Shared payment plan structures via WhatsApp", from_address: "+2348031234567", to_address: "+2348051234569" },
  ];

  const CAMP_SAMPLES = [
    { name: "Q2 2026 — Lekki Phase 3 Launch", description: "Targeted email blast for Phase 3 unit release to qualified leads", campaign_type: "email_blast", channel: "email", subject: "Exclusive Preview: Lekki Phase 3 Units Now Available", body: "Dear Valued Client,\n\nWe are pleased to announce the release of premium units in Lekki Phase 3. As a pre-qualified buyer, you have priority access before the public launch.\n\nSchedule your private viewing today." },
    { name: "Ikoyi Waterfront — Investor Drip", description: "Automated drip sequence for investor leads interested in Ikoyi Waterfront", campaign_type: "drip", channel: "email", subject: "Ikoyi Waterfront: Your Investment Opportunity Awaits", body: "Hello,\n\nIkoyi Waterfront continues to deliver exceptional ROI. Current occupancy is at 94%, and rental yields are averaging 8.2% per annum.\n\nDownload our latest investor report." },
    { name: "Eko Atlantic — SMS Re-engagement", description: "SMS blast to dormant leads from Eko Atlantic enquiries in Q4 2025", campaign_type: "sms_blast", channel: "sms", subject: "Eko Atlantic — Limited Units Remaining", body: "Hi! Eko Atlantic Tower B has just 12 units left. Prices start at N45M. Reply YES for a callback or visit ekoatlantic.ng/tower-b" },
  ];

  let devIdx = $state(0);

  function devFillComm() {
    const sample = COMM_SAMPLES[devIdx % COMM_SAMPLES.length];
    devIdx++;
    commForm.channel = sample.channel;
    commForm.direction = sample.direction;
    commForm.subject = sample.subject;
    commForm.body = sample.body;
    commForm.summary = sample.summary;
    commForm.from_address = sample.from_address;
    commForm.to_address = sample.to_address;
    commForm.communicated_at = new Date().toISOString().slice(0, 16);
    if (activeLeads.length > 0) commForm.lead = String(activeLeads[devIdx % activeLeads.length].id);
  }

  function devFillCamp() {
    const sample = CAMP_SAMPLES[devIdx % CAMP_SAMPLES.length];
    devIdx++;
    campForm.name = sample.name;
    campForm.description = sample.description;
    campForm.campaign_type = sample.campaign_type;
    campForm.channel = sample.channel;
    campForm.subject = sample.subject;
    campForm.body = sample.body;
    campForm.notification_template = "";
    campForm.scheduled_at = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 16);
    campForm.target_lead_types = sample.name.includes("Investor") ? ["investor"] : ["buyer"];
    campForm.spend_amount = "2500000";
    campForm.revenue_attributed = "8750000";
    campForm.auto_create_leads_on_launch = true;
    campForm.auto_create_leads_count = "12";
    campForm.auto_create_lead_type = campForm.target_lead_types[0] ?? "buyer";
    if (campLeadSources.length > 0) campForm.target_lead_sources = [campLeadSources[0].id];
  }

  // ================================================
  // Slide-over management
  // ================================================
  let anySlide = $derived(showCommSlide || showCampSlide || showRuleSlide || showDocSlide || showMeetSlide);

  function closeAll() {
    showCommSlide = false; showCampSlide = false; showRuleSlide = false; showDocSlide = false; showMeetSlide = false;
    commDetail = null;
    threadDetail = null;
    threadMessages = [];
    threadMessagesLoading = false;
    showCampaignDetailDrawer = false;
    selectedCampaignId = null;
  }

  function openCreate() {
    closeAll();
    if (activeTab === "communications") { resetCommForm(); showCommSlide = true; if (!activeLeads.length) fetchLeads(); }
    else if (activeTab === "campaigns") {
      resetCampForm();
      showCampSlide = true;
      if (!campLeadSources.length) fetchCampLeadSources();
      if (!campTemplates.length) fetchCampTemplates();
    }
    else if (activeTab === "followup") { resetRuleForm(); showRuleSlide = true; }
    else if (activeTab === "documents") { resetDocForm(); showDocSlide = true; if (!activeLeads.length) fetchLeads(); }
    else if (activeTab === "meetings") { resetMeetForm(); showMeetSlide = true; if (!activeLeads.length) fetchLeads(); }
  }

  // ================================================
  // Init
  // ================================================
  $effect(() => {
    const tabParam = $page.url.searchParams.get("tab");
    if (!tabParam) return;
    if (tabParam === "communications" || tabParam === "campaigns" || tabParam === "followup" || tabParam === "documents" || tabParam === "meetings") {
      if (activeTab !== tabParam) activeTab = tabParam;
    }
  });

  $effect(() => {
    const campaignParam = $page.url.searchParams.get("campaign");
    if (!campaignParam) return;
    const id = Number(campaignParam);
    if (!Number.isInteger(id) || id <= 0) return;
    if (activeTab !== "campaigns") activeTab = "campaigns";
    if (showCampaignDetailDrawer && selectedCampaignId === id) return;
    openCampaignDetailDrawer(id, false);
  });

  $effect(() => {
    if (activeTab === "communications") {
      if (commViewMode === "logs") fetchComms();
      else fetchThreads();
      fetchOverview();
    }
    else if (activeTab === "campaigns") {
      fetchCamps();
      if (!campLeadSources.length) fetchCampLeadSources();
      if (!campTemplates.length) fetchCampTemplates();
    }
    else if (activeTab === "followup") { fetchRules(); fetchTasks(); }
    else if (activeTab === "documents") fetchDocs();
    else if (activeTab === "meetings") fetchMeets();
  });

  // Input class shorthand
  const ic = "w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-neutral-500">CRM</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-800 tracking-wide">Communication Engine</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage communications, campaigns, follow-ups, documents, and meetings</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      {activeTab === "communications" ? "Log Communication" : activeTab === "campaigns" ? "New Campaign" : activeTab === "followup" ? "New Rule" : activeTab === "documents" ? "Log Event" : "New Meeting"}
    </button>
  </div>

  <!-- Tabs -->
  <div class="border-b border-neutral-200">
    <nav class="flex gap-6 -mb-px">
      {#each tabs as tab}
        <button onclick={() => { activeTab = tab.key; }} class="pb-3 text-sm font-medium border-b-2 transition-colors {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}">{tab.label}</button>
      {/each}
    </nav>
  </div>

  <!-- ======================= TAB 1: Communications Log ======================= -->
  {#if activeTab === "communications"}
    {#if commOverview}
      <div class="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-9 gap-4">
        {#each [
          ["Total", kpiTotal, "text-violet-900"],
          ["Inbound", kpiInbound, "text-violet-800"],
          ["Outbound", kpiOutbound, "text-violet-700"],
          ["Emails", kpiEmails, "text-violet-600"],
          ["Calls", kpiCalls, "text-violet-500"],
          ["WhatsApp", kpiWhatsapp, "text-violet-400"],
          ["In-App", kpiInApp, "text-neutral-700"],
          ["Due Soon", kpiReminderSoon, "text-orange-600"],
          ["Overdue", kpiReminderOverdue, "text-rose-600"],
        ] as [k, v, valueClass]}
          <div class="bg-white rounded-xl border border-neutral-200 p-5">
            <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">{k}</p>
            <p class="mt-2 text-2xl font-semibold tabular-nums {valueClass}">{(v as number).toLocaleString()}</p>
          </div>
        {/each}
      </div>
    {/if}

    <div class="bg-white rounded-xl border border-neutral-200 p-5">
      <div class="mb-4 inline-flex items-center gap-1 rounded-lg border border-neutral-200 p-1">
        <button
          onclick={() => { commViewMode = "logs"; commPage = 1; fetchComms(); }}
          class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors {commViewMode === 'logs' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}"
        >
          Logs
        </button>
        <button
          onclick={() => { commViewMode = "threads"; threadPage = 1; fetchThreads(); }}
          class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors {commViewMode === 'threads' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}"
        >
          Threads
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
          <input
            type="text"
            placeholder="Subject, lead..."
            value={commSearch}
            oninput={(e) => {
              commSearch = (e.target as HTMLInputElement).value;
              deb(() => {
                commPage = 1;
                threadPage = 1;
                if (commViewMode === "logs") fetchComms();
                else fetchThreads();
              });
            }}
            class={ic}
          /></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Channel</span>
          <select value={commChannel} onchange={(e) => { commChannel = (e.target as HTMLSelectElement).value; commPage = 1; threadPage = 1; if (commViewMode === "logs") fetchComms(); else fetchThreads(); }} class={ic}>
            <option value="">All</option><option value="email">Email</option><option value="whatsapp">WhatsApp</option><option value="sms">SMS</option><option value="in_app">In-App</option><option value="phone">Phone</option><option value="video_call">Video</option><option value="in_person">In Person</option>
          </select></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Direction</span>
          <select value={commDirection} onchange={(e) => { commDirection = (e.target as HTMLSelectElement).value; commPage = 1; threadPage = 1; if (commViewMode === "logs") fetchComms(); else fetchThreads(); }} class={ic}>
            <option value="">All</option><option value="inbound">Inbound</option><option value="outbound">Outbound</option>
          </select></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
          <select value={commStatus} onchange={(e) => { commStatus = (e.target as HTMLSelectElement).value; commPage = 1; threadPage = 1; if (commViewMode === "logs") fetchComms(); else fetchThreads(); }} class={ic}>
            <option value="">All</option><option value="draft">Draft</option><option value="sent">Sent</option><option value="delivered">Delivered</option><option value="read">Read</option><option value="received">Received</option><option value="failed">Failed</option>
          </select></label>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if commViewMode === "logs" && commLoading}
        <div class="flex items-center justify-center py-20"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if commViewMode === "threads" && threadLoading}
        <div class="flex items-center justify-center py-20"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if commListError}
        <div class="p-6">
          <DataStateBanner
            title={commViewMode === "logs" ? "Couldn't load communications" : "Couldn't load threads"}
            message={commListError}
            onretry={commViewMode === "logs" ? fetchComms : fetchThreads}
          />
        </div>
      {:else if commViewMode === "logs" && commItems.length === 0}
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <svg class="mx-auto h-12 w-12 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" /></svg>
          <p class="text-neutral-500 text-sm">No communications found</p>
          <button onclick={openCreate} class="mt-3 text-sm font-medium text-neutral-900 hover:underline">Log your first communication</button>
        </div>
      {:else if commViewMode === "threads" && threadItems.length === 0}
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <svg class="mx-auto h-12 w-12 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M8.625 9.75h6.75m-6.75 3h4.5m2.625 5.25H7.5A2.25 2.25 0 0 1 5.25 15.75V8.25A2.25 2.25 0 0 1 7.5 6h9A2.25 2.25 0 0 1 18.75 8.25v5.879a2.25 2.25 0 0 1-.659 1.591l-1.682 1.682A2.25 2.25 0 0 1 14.818 18H15.75Z" /></svg>
          <p class="text-neutral-500 text-sm">No conversation threads found</p>
        </div>
      {:else}
        {#if commViewMode === "logs"}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="border-b border-neutral-200 bg-neutral-50/50">
                <tr>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Lead</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Channel</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Direction</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Status</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Subject</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Performed By</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Date</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each commItems as item}
                  <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => { openCommunicationDetail(item); }}>
                    <td class="px-5 py-4 text-sm font-medium text-neutral-900">{item.lead_name ?? "\u2014"}</td>
                    <td class="px-5 py-4"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge(chBadge, item.channel)}">{lbl(item.channel)}</span></td>
                    <td class="px-5 py-4 text-sm text-neutral-600 capitalize">{item.direction}</td>
                    <td class="px-5 py-4"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge(stBadge, item.status)}">{lbl(item.status)}</span></td>
                    <td class="px-5 py-4 text-sm text-neutral-700 max-w-xs truncate">{item.subject || "\u2014"}</td>
                    <td class="px-5 py-4 text-sm text-neutral-600">{item.performed_by_name ?? "\u2014"}</td>
                    <td class="px-5 py-4 text-sm text-neutral-500">{fmtDateTime(item.communicated_at)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          {@render pager(commPage, commPages, commCount, (p) => { commPage = p; fetchComms(); })}
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="border-b border-neutral-200 bg-neutral-50/50">
                <tr>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Lead</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Channel</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Participants</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Messages</th>
                  <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Latest</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each threadItems as thread}
                  <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openThreadDetail(thread)}>
                    <td class="px-5 py-4 text-sm font-medium text-neutral-900">{thread.lead_name || "\u2014"}</td>
                    <td class="px-5 py-4"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge(chBadge, thread.channel)}">{lbl(thread.channel)}</span></td>
                    <td class="px-5 py-4 text-sm text-neutral-600 max-w-sm truncate">{thread.participants?.join(" • ") || "\u2014"}</td>
                    <td class="px-5 py-4 text-sm text-neutral-600 tabular-nums">{thread.message_count}</td>
                    <td class="px-5 py-4 text-sm text-neutral-500">{fmtDateTime(thread.last_message_at)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          {@render pager(threadPage, threadPages, threadCount, (p) => { threadPage = p; fetchThreads(); })}
        {/if}
      {/if}
    </div>
  {/if}

  <!-- ======================= TAB 2: Campaigns ======================= -->
  {#if activeTab === "campaigns"}
    <div class="bg-white rounded-xl border border-neutral-200 p-5">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
          <input type="text" placeholder="Campaign name..." value={campSearch} oninput={(e) => { campSearch = (e.target as HTMLInputElement).value; deb(() => { campPage = 1; fetchCamps(); }); }} class={ic} /></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Type</span>
          <select value={campType} onchange={(e) => { campType = (e.target as HTMLSelectElement).value; campPage = 1; fetchCamps(); }} class={ic}>
            <option value="">All</option><option value="email_blast">Email Blast</option><option value="drip">Drip</option><option value="sms_blast">SMS Blast</option><option value="digital_ads">Digital Ads</option><option value="whatsapp_campaign">WhatsApp</option><option value="follow_up">Follow-Up</option>
          </select></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
          <select value={campStat} onchange={(e) => { campStat = (e.target as HTMLSelectElement).value; campPage = 1; fetchCamps(); }} class={ic}>
            <option value="">All</option><option value="draft">Draft</option><option value="scheduled">Scheduled</option><option value="running">Running</option><option value="paused">Paused</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option>
          </select></label>
      </div>
    </div>

    {#if campLoading}
      <div class="flex items-center justify-center py-20"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
    {:else if campListError}
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <DataStateBanner
          title="Couldn't load campaigns"
          message={campListError}
          onretry={fetchCamps}
        />
      </div>
    {:else if campItems.length === 0}
      <div class="bg-white rounded-xl border border-neutral-200 flex flex-col items-center justify-center py-20 text-center">
        <svg class="mx-auto h-12 w-12 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38a1.125 1.125 0 0 1-1.54-.41l-.363-.63a8.962 8.962 0 0 1-.952-4.165c.054-.89.19-1.758.396-2.594m0-4.97a10.065 10.065 0 0 1-.396-2.593A8.96 8.96 0 0 1 9.497 6.64l.363-.63a1.125 1.125 0 0 1 1.54-.41l.657.38c.523.301.71.96.463 1.51a9.065 9.065 0 0 1-.985 2.784M7.5 12H3" /></svg>
        <p class="text-neutral-500 text-sm">No campaigns found</p>
        <button onclick={openCreate} class="mt-3 text-sm font-medium text-neutral-900 hover:underline">Create your first campaign</button>
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each campItems as c}
          <button onclick={() => openCampaignDetailDrawer(c.id)} class="bg-white rounded-xl border border-neutral-200 p-5 text-left hover:border-neutral-400 transition-colors">
            <div class="flex items-start justify-between mb-3">
              <h3 class="text-sm font-semibold text-neutral-900 truncate pr-2">{c.name}</h3>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0 {badge(stBadge, c.status)}">{lbl(c.status)}</span>
            </div>
            <div class="flex gap-2 mb-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">{lbl(c.campaign_type)}</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {badge(chBadge, c.channel)}">{lbl(c.channel)}</span>
            </div>
            <div class="text-xs text-neutral-500 mb-1">{c.total_recipients ?? 0} recipients</div>
            <div class="text-xs text-neutral-500 mb-3">ROI: {Number(c.roi_percent ?? 0).toFixed(1)}%</div>
            {#if c.open_rate != null || c.click_rate != null}
              <div class="space-y-2">
                {#if c.open_rate != null}
                  <div>
                    <div class="flex justify-between text-xs text-neutral-500 mb-1"><span>Open Rate</span><span class="tabular-nums">{c.open_rate.toFixed(1)}%</span></div>
                    <div class="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden"><div class="h-full bg-violet-300 rounded-full" style="width: {c.open_rate}%"></div></div>
                  </div>
                {/if}
                {#if c.click_rate != null}
                  <div>
                    <div class="flex justify-between text-xs text-neutral-500 mb-1"><span>Click Rate</span><span class="tabular-nums">{c.click_rate.toFixed(1)}%</span></div>
                    <div class="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden"><div class="h-full bg-violet-700 rounded-full" style="width: {c.click_rate}%"></div></div>
                  </div>
                {/if}
              </div>
            {/if}
          </button>
        {/each}
      </div>
      {@render pager(campPage, campPages, campCount, (p) => { campPage = p; fetchCamps(); })}
    {/if}
  {/if}

  <!-- ======================= TAB 3: Follow-Up SLA ======================= -->
  {#if activeTab === "followup"}
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="flex items-center justify-between px-5 py-4 border-b border-neutral-200">
        <h2 class="text-sm font-semibold text-neutral-900">Follow-Up Rules</h2>
        <button onclick={openCreate} class="text-sm font-medium text-neutral-700 hover:text-neutral-900 transition-colors">+ Add Rule</button>
      </div>
      {#if fuRulesLoading}
        <div class="flex items-center justify-center py-12"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if fuListError}
        <div class="p-6">
          <DataStateBanner
            title="Couldn't load follow-up rules"
            message={fuListError}
            onretry={fetchRules}
          />
        </div>
      {:else if fuRules.length === 0}
        <div class="py-12 text-center text-sm text-neutral-400">No follow-up rules configured</div>
      {:else}
        <div class="divide-y divide-neutral-100">
          {#each fuRules as rule}
            <button onclick={() => editRule(rule)} class="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-neutral-50 transition-colors">
              <div>
                <span class="text-sm font-medium text-neutral-900">{rule.name}</span>
                <span class="ml-2 text-xs text-neutral-400">Stage: {lbl(rule.trigger_stage)} | Within {rule.follow_up_within_hours}h | {lbl(rule.required_activity_type)}</span>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {rule.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">{rule.is_active ? "Active" : "Inactive"}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="flex items-center justify-between px-5 py-4 border-b border-neutral-200">
        <h2 class="text-sm font-semibold text-neutral-900">Follow-Up Tasks</h2>
        <select value={fuTaskStat} onchange={(e) => { fuTaskStat = (e.target as HTMLSelectElement).value; fuTaskPage = 1; fetchTasks(); }} class="px-3 py-1.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
          <option value="">All</option><option value="pending">Pending</option><option value="completed">Completed</option><option value="overdue">Overdue</option><option value="escalated">Escalated</option>
        </select>
      </div>
      {#if fuTaskLoading}
        <div class="flex items-center justify-center py-12"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if fuListError}
        <div class="p-6">
          <DataStateBanner
            title="Couldn't load follow-up tasks"
            message={fuListError}
            onretry={fetchTasks}
          />
        </div>
      {:else if fuTasks.length === 0}
        <div class="py-12 text-center text-sm text-neutral-400">No follow-up tasks</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50/50">
              <tr>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Lead</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Rule</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Due Date</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Status</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Overdue</th>
                <th class="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-neutral-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each fuTasks as t}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-4 text-sm font-medium text-neutral-900">{t.lead_name ?? "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{t.rule_name ?? "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-500">{fmtDateTime(t.due_at ?? t.due_date)}</td>
                  <td class="px-5 py-4"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge(stBadge, t.status)}">{lbl(t.status)}</span></td>
                  <td class="px-5 py-4">{#if t.is_overdue}<span class="inline-block w-2 h-2 rounded-full bg-neutral-900"></span>{:else}<span class="text-neutral-300">&mdash;</span>{/if}</td>
                  <td class="px-5 py-4 text-right">
                    {#if t.status === "pending" || t.status === "overdue"}
                      <div class="inline-flex gap-2">
                        <button onclick={() => completeTask(t.id)} class="text-xs font-medium text-neutral-700 hover:text-neutral-900 transition-colors">Complete</button>
                        <button onclick={() => escalateTask(t.id)} class="text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors">Escalate</button>
                      </div>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {@render pager(fuTaskPage, fuTaskPages, fuTaskCount, (p) => { fuTaskPage = p; fetchTasks(); })}
      {/if}
    </div>
  {/if}

  <!-- ======================= TAB 4: Document Tracking ======================= -->
  {#if activeTab === "documents"}
    <div class="bg-white rounded-xl border border-neutral-200 p-5">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
          <input type="text" placeholder="Document name, lead..." value={docSearch} oninput={(e) => { docSearch = (e.target as HTMLInputElement).value; deb(() => { docPage = 1; fetchDocs(); }); }} class={ic} /></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Event Type</span>
          <select value={docType} onchange={(e) => { docType = (e.target as HTMLSelectElement).value; docPage = 1; fetchDocs(); }} class={ic}>
            <option value="">All</option><option value="sent">Sent</option><option value="delivered">Delivered</option><option value="viewed">Viewed</option><option value="signed">Signed</option><option value="returned">Returned</option>
          </select></label>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if docLoading}
        <div class="flex items-center justify-center py-20"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if docListError}
        <div class="p-6">
          <DataStateBanner
            title="Couldn't load document events"
            message={docListError}
            onretry={fetchDocs}
          />
        </div>
      {:else if docEvents.length === 0}
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <svg class="mx-auto h-12 w-12 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
          <p class="text-neutral-500 text-sm">No document events</p>
          <button onclick={openCreate} class="mt-3 text-sm font-medium text-neutral-900 hover:underline">Log your first event</button>
        </div>
      {:else}
        <div class="divide-y divide-neutral-100">
          {#each docEvents as evt}
            <div class="flex items-start gap-4 px-5 py-4">
              <div class="mt-1 w-2 h-2 rounded-full bg-neutral-400 shrink-0"></div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-sm font-medium text-neutral-900">{evt.lead_name ?? "Unknown"}</span>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {badge(stBadge, evt.event_type)}">{lbl(evt.event_type)}</span>
                </div>
                <p class="text-sm text-neutral-700">{evt.document_name}</p>
                {#if evt.delivered_via}<p class="text-xs text-neutral-400 mt-0.5">via {lbl(evt.delivered_via)}</p>{/if}
              </div>
              <span class="text-xs text-neutral-400 shrink-0">{fmtDateTime(evt.created_at)}</span>
            </div>
          {/each}
        </div>
        {@render pager(docPage, docPages, docCount, (p) => { docPage = p; fetchDocs(); })}
      {/if}
    </div>
  {/if}

  <!-- ======================= TAB 5: Meetings ======================= -->
  {#if activeTab === "meetings"}
    <div class="bg-white rounded-xl border border-neutral-200 p-5">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
          <input type="text" placeholder="Title, lead..." value={meetSearch} oninput={(e) => { meetSearch = (e.target as HTMLInputElement).value; deb(() => { meetPage = 1; fetchMeets(); }); }} class={ic} /></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Type</span>
          <select value={meetType} onchange={(e) => { meetType = (e.target as HTMLSelectElement).value; meetPage = 1; fetchMeets(); }} class={ic}>
            <option value="">All</option><option value="site_visit">Site Visit</option><option value="presentation">Presentation</option><option value="negotiation">Negotiation</option><option value="closing">Closing</option><option value="follow_up">Follow Up</option><option value="other">Other</option>
          </select></label>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Outcome</span>
          <select value={meetOutcome} onchange={(e) => { meetOutcome = (e.target as HTMLSelectElement).value; meetPage = 1; fetchMeets(); }} class={ic}>
            <option value="">All</option><option value="scheduled">Scheduled</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option><option value="no_show">No Show</option><option value="rescheduled">Rescheduled</option>
          </select></label>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if meetLoading}
        <div class="flex items-center justify-center py-20"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if meetListError}
        <div class="p-6">
          <DataStateBanner
            title="Couldn't load meetings"
            message={meetListError}
            onretry={fetchMeets}
          />
        </div>
      {:else if meetItems.length === 0}
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <svg class="mx-auto h-12 w-12 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg>
          <p class="text-neutral-500 text-sm">No meetings found</p>
          <button onclick={openCreate} class="mt-3 text-sm font-medium text-neutral-900 hover:underline">Schedule your first meeting</button>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50/50">
              <tr>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Title</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Lead</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Type</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Outcome</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Scheduled</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Location</th>
                <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Organizer</th>
                <th class="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-neutral-400 font-medium">Duration</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each meetItems as m}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-4 text-sm font-medium text-neutral-900">{m.title}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{m.lead_name ?? "\u2014"}</td>
                  <td class="px-5 py-4"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">{lbl(m.meeting_type)}</span></td>
                  <td class="px-5 py-4">{#if m.outcome}<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge(stBadge, m.outcome)}">{lbl(m.outcome)}</span>{:else}<span class="text-neutral-300">\u2014</span>{/if}</td>
                  <td class="px-5 py-4 text-sm text-neutral-500">{fmtDateTime(m.scheduled_start)}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600 max-w-xs truncate">{m.location || "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{m.organized_by_name ?? "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-500 text-right tabular-nums">{m.duration_minutes ? `${m.duration_minutes}m` : "\u2014"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {@render pager(meetPage, meetPages, meetCount, (p) => { meetPage = p; fetchMeets(); })}
      {/if}
    </div>
  {/if}
</div>

{#if showCampaignDetailDrawer && selectedCampaignId !== null}
  <button
    class="fixed inset-0 z-998 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeCampaignDetailDrawer}
    tabindex="-1"
    aria-label="Close campaign detail drawer"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-999 w-full max-w-6xl bg-white shadow-2xl slide-over-enter flex flex-col">
    <div class="shrink-0 border-b border-neutral-100 px-6 py-4 flex items-center justify-between">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-500">Campaign Detail</h2>
      <button
        onclick={closeCampaignDetailDrawer}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close campaign detail drawer"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <CampaignDetailPage campaignId={selectedCampaignId} embedded={true} />
    </div>
  </aside>
{/if}

<!-- ======================= Pagination Snippet ======================= -->
{#snippet pager(cur: number, tot: number, cnt: number, go: (p: number) => void)}
  <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
    <p class="text-sm text-neutral-400">Showing {(cur - 1) * pageSize + 1}&ndash;{Math.min(cur * pageSize, cnt)} of {cnt}</p>
    {#if tot > 1}
      <div class="flex items-center gap-1">
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <button onclick={() => go(cur - 1)} disabled={cur <= 1} class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
        </button>
        {#each pgNums(cur, tot) as pg}
          <button onclick={() => go(pg)} class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === cur ? 'bg-neutral-900 text-white border-neutral-900' : 'border-neutral-200 hover:bg-neutral-50'}">{pg}</button>
        {/each}
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <button onclick={() => go(cur + 1)} disabled={cur >= tot} class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
        </button>
      </div>
    {/if}
  </div>
{/snippet}

<!-- ======================= Communication Detail Modal ======================= -->
{#if commDetail}
  <button class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default" onclick={() => { commDetail = null; }} tabindex="-1" aria-label="Close"></button>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg modal-enter" onclick={(e) => e.stopPropagation()}>
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
        <h2 class="text-lg font-semibold text-neutral-900">Communication Detail</h2>
        <button onclick={() => { commDetail = null; }} class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Lead</span><span class="text-neutral-900 font-medium">{commDetail.lead_name ?? "\u2014"}</span></div>
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Channel</span><span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {badge(chBadge, commDetail.channel)}">{lbl(commDetail.channel)}</span></div>
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Direction</span><span class="text-neutral-700 capitalize">{commDetail.direction}</span></div>
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Status</span><span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {badge(stBadge, commDetail.status)}">{lbl(commDetail.status)}</span></div>
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">From</span><span class="text-neutral-700">{commDetail.from_address || "\u2014"}</span></div>
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">To</span><span class="text-neutral-700">{commDetail.to_address || "\u2014"}</span></div>
        </div>
        {#if commDetail.subject}<div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Subject</span><p class="text-sm text-neutral-900">{commDetail.subject}</p></div>{/if}
        {#if commDetail.body}<div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Body</span><p class="text-sm text-neutral-700 whitespace-pre-wrap">{commDetail.body}</p></div>{/if}
        {#if commDetail.summary}<div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Summary</span><p class="text-sm text-neutral-600">{commDetail.summary}</p></div>{/if}
        {#if commDetail.attachments?.length}
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Attachments</span>
            <div class="space-y-1">{#each commDetail.attachments as att}<a href={att.file_url ?? att.url ?? att.file} target="_blank" rel="noopener" class="block text-sm text-neutral-700 hover:text-neutral-900 underline">{att.name ?? att.file_name ?? "Attachment"}</a>{/each}</div>
          </div>
        {/if}
        {#if commDetail.call_recording_url ?? commDetail.call_recording}
          <div><span class="text-neutral-400 block text-xs uppercase tracking-wider mb-1">Call Recording</span><audio controls src={commDetail.call_recording_url ?? commDetail.call_recording} class="w-full mt-1"></audio></div>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if threadDetail}
  <button class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default" onclick={closeThreadDetail} tabindex="-1" aria-label="Close thread"></button>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-4xl modal-enter" onclick={(e) => e.stopPropagation()}>
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
        <div>
          <h2 class="text-lg font-semibold text-neutral-900">Conversation Thread</h2>
          <p class="text-xs text-neutral-500 mt-1">
            {threadDetail.lead_name || "\u2014"} • {lbl(threadDetail.channel)} • {threadDetail.message_count} messages
          </p>
        </div>
        <button onclick={closeThreadDetail} class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="px-6 py-5 space-y-3 max-h-[70vh] overflow-y-auto">
        {#if threadMessagesLoading}
          <div class="flex items-center justify-center py-16"><div class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
        {:else if threadMessages.length === 0}
          <p class="py-10 text-center text-sm text-neutral-500">No messages found for this thread.</p>
        {:else}
          {#each threadMessages as message}
            <button class="w-full rounded-lg border border-neutral-200 p-4 text-left hover:border-neutral-300 transition-colors" onclick={() => { threadDetail = null; threadMessages = []; openCommunicationDetail(message); }}>
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-neutral-900">{message.subject || "\u2014"}</p>
                  <p class="mt-1 text-xs text-neutral-500">{message.summary || message.body || "\u2014"}</p>
                </div>
                <div class="text-right">
                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {badge(stBadge, message.status)}">{lbl(message.status)}</span>
                  <p class="mt-1 text-xs text-neutral-500">{fmtDateTime(message.communicated_at)}</p>
                </div>
              </div>
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- ======================= Slide-Overs ======================= -->
{#if anySlide}
  <button class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default" onclick={closeAll} tabindex="-1" aria-label="Close panel"></button>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg flex flex-col bg-white shadow-2xl slide-over-enter">
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-900">
        {#if showCommSlide}Log Communication{:else if showCampSlide}New Campaign{:else if showRuleSlide}{editingRule ? "Edit Rule" : "New Rule"}{:else if showDocSlide}Log Document Event{:else}New Meeting{/if}
      </h2>
      <button onclick={closeAll} class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors" aria-label="Close">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      {#if showCommSlide}
        <form id="so-form" onsubmit={createComm} class="space-y-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead</span>
            <select bind:value={commForm.lead} required class={ic}><option value="">Select lead</option>{#each activeLeads as l}<option value={String(l.id)}>{l.full_name ?? `${l.first_name} ${l.last_name}`}</option>{/each}</select>
            {#if fieldErr(commErrors, "lead")}<p class="mt-1 text-xs text-red-500">{fieldErr(commErrors, "lead")}</p>{/if}</label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Channel</span>
              <select bind:value={commForm.channel} class={ic}><option value="email">Email</option><option value="whatsapp">WhatsApp</option><option value="sms">SMS</option><option value="in_app">In-App</option><option value="phone">Phone</option><option value="video_call">Video</option><option value="in_person">In Person</option></select></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Direction</span>
              <select bind:value={commForm.direction} class={ic}><option value="outbound">Outbound</option><option value="inbound">Inbound</option></select></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Subject</span>
            <input type="text" bind:value={commForm.subject} class={ic} />{#if fieldErr(commErrors, "subject")}<p class="mt-1 text-xs text-red-500">{fieldErr(commErrors, "subject")}</p>{/if}</label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Body</span>
            <textarea bind:value={commForm.body} rows="3" class="{ic} resize-none"></textarea></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Summary</span>
            <input type="text" bind:value={commForm.summary} class={ic} /></label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">From</span><input type="text" bind:value={commForm.from_address} class={ic} /></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">To</span><input type="text" bind:value={commForm.to_address} class={ic} /></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Date/Time</span>
            <input type="datetime-local" bind:value={commForm.communicated_at} class={ic} /></label>
        </form>
      {/if}

      {#if showCampSlide}
        <form id="so-form" onsubmit={createCamp} class="space-y-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Name</span>
            <input type="text" bind:value={campForm.name} required class={ic} />{#if fieldErr(campErrors, "name")}<p class="mt-1 text-xs text-red-500">{fieldErr(campErrors, "name")}</p>{/if}</label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
            <textarea bind:value={campForm.description} rows="2" class="{ic} resize-none"></textarea></label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Type</span>
              <select bind:value={campForm.campaign_type} class={ic}><option value="email_blast">Email Blast</option><option value="drip">Drip</option><option value="sms_blast">SMS Blast</option><option value="digital_ads">Digital Ads</option><option value="whatsapp_campaign">WhatsApp Campaign</option><option value="follow_up">Follow-Up</option></select></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Channel</span>
              <select bind:value={campForm.channel} class={ic}><option value="email">Email</option><option value="sms">SMS</option><option value="whatsapp">WhatsApp</option><option value="in_app">In-App</option><option value="other">Other</option></select></label>
          </div>
          <div>
            <div class="mb-1.5 flex items-center justify-between">
              <span class="block text-sm font-medium text-neutral-700">Template</span>
              <a href="/settings/notifications" class="text-xs text-neutral-500 hover:text-neutral-900 hover:underline">Manage templates</a>
            </div>
            <select bind:value={campForm.notification_template} class={ic}>
              <option value="">No linked template</option>
              {#each campTemplates.filter((template) => !campForm.channel || template.channel === campForm.channel) as template}
                <option value={String(template.id)}>{template.name} ({lbl(template.channel)})</option>
              {/each}
            </select>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Subject</span><input type="text" bind:value={campForm.subject} class={ic} /></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Body</span><textarea bind:value={campForm.body} rows="4" class="{ic} resize-none"></textarea></label>
          <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Segmentation</p>
            <div>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead Types</span>
              <div class="flex flex-wrap gap-2">
                {#each campLeadTypeOptions as option}
                  <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700">
                    <input
                      type="checkbox"
                      checked={campForm.target_lead_types.includes(option.value)}
                      onchange={() => toggleCampLeadType(option.value)}
                      class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                    />
                    {option.label}
                  </label>
                {/each}
              </div>
            </div>
            <div>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Pipeline Stages</span>
              <div class="grid grid-cols-2 gap-2">
                {#each campStageOptions as option}
                  <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700">
                    <input
                      type="checkbox"
                      checked={campForm.target_pipeline_stages.includes(option.value)}
                      onchange={() => toggleCampStage(option.value)}
                      class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                    />
                    {option.label}
                  </label>
                {/each}
              </div>
            </div>
            <div>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead Sources</span>
              {#if campLeadSources.length === 0}
                <p class="text-xs text-neutral-400">No active lead sources found.</p>
              {:else}
                <div class="grid grid-cols-2 gap-2">
                  {#each campLeadSources as source}
                    <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700">
                      <input
                        type="checkbox"
                        checked={campForm.target_lead_sources.includes(source.id)}
                        onchange={() => toggleCampLeadSource(source.id)}
                        class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                      />
                      {source.name}
                    </label>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
          <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">ROI Tracking</p>
            <div class="grid grid-cols-2 gap-4">
              <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Spend</span>
                <input type="number" min="0" step="0.01" bind:value={campForm.spend_amount} class={ic} /></label>
              <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Attributed Revenue</span>
                <input type="number" min="0" step="0.01" bind:value={campForm.revenue_attributed} class={ic} /></label>
            </div>
          </div>
          <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Automations</p>
            <label class="flex items-center gap-3">
              <input
                type="checkbox"
                bind:checked={campForm.auto_create_leads_on_launch}
                class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
              />
              <span class="text-sm font-medium text-neutral-700">Campaign launch auto-creates leads</span>
            </label>
            <div class="grid grid-cols-2 gap-4">
              <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Leads To Create</span>
                <input
                  type="number"
                  min="0"
                  bind:value={campForm.auto_create_leads_count}
                  class={ic}
                  disabled={!campForm.auto_create_leads_on_launch}
                /></label>
              <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Auto Lead Type</span>
                <select bind:value={campForm.auto_create_lead_type} class={ic} disabled={!campForm.auto_create_leads_on_launch}>
                  <option value="buyer">Home Buyer</option>
                  <option value="investor">Investor</option>
                  <option value="tenant">Tenant</option>
                </select></label>
            </div>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Scheduled At</span><input type="datetime-local" bind:value={campForm.scheduled_at} class={ic} /></label>
        </form>
      {/if}

      {#if showRuleSlide}
        <form id="so-form" onsubmit={saveRule} class="space-y-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Rule Name</span>
            <input type="text" bind:value={ruleForm.name} required class={ic} />{#if fieldErr(ruleErrors, "name")}<p class="mt-1 text-xs text-red-500">{fieldErr(ruleErrors, "name")}</p>{/if}</label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Trigger Stage</span>
              <select bind:value={ruleForm.trigger_stage} class={ic}><option value="inquiry">Inquiry</option><option value="qualified">Qualified</option><option value="site_visit">Site Visit</option><option value="offer_made">Offer Made</option><option value="reservation">Reservation</option><option value="spa_issued">SPA Issued</option></select></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Within Hours</span>
              <input type="number" bind:value={ruleForm.follow_up_within_hours} min="1" required class="{ic} tabular-nums" /></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Required Activity</span>
            <select bind:value={ruleForm.required_activity_type} class={ic}><option value="call">Call</option><option value="email">Email</option><option value="meeting">Meeting</option><option value="whatsapp">WhatsApp</option><option value="any">Any</option></select></label>
          <label class="flex items-center gap-3"><input type="checkbox" bind:checked={ruleForm.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" /><span class="text-sm font-medium text-neutral-700">Active</span></label>
        </form>
      {/if}

      {#if showDocSlide}
        <form id="so-form" onsubmit={createDoc} class="space-y-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead</span>
            <select bind:value={docForm.lead} required class={ic}><option value="">Select lead</option>{#each activeLeads as l}<option value={String(l.id)}>{l.full_name ?? `${l.first_name} ${l.last_name}`}</option>{/each}</select>
            {#if fieldErr(docErrors, "lead")}<p class="mt-1 text-xs text-red-500">{fieldErr(docErrors, "lead")}</p>{/if}</label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Event Type</span>
            <select bind:value={docForm.event_type} class={ic}><option value="sent">Sent</option><option value="delivered">Delivered</option><option value="viewed">Viewed</option><option value="signed">Signed</option><option value="returned">Returned</option></select></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Document Name</span>
            <input type="text" bind:value={docForm.document_name} required class={ic} />{#if fieldErr(docErrors, "document_name")}<p class="mt-1 text-xs text-red-500">{fieldErr(docErrors, "document_name")}</p>{/if}</label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivered Via</span><input type="text" bind:value={docForm.delivered_via} placeholder="email, courier..." class={ic} /></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivered To</span><input type="text" bind:value={docForm.delivered_to} class={ic} /></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span><textarea bind:value={docForm.notes} rows="3" class="{ic} resize-none"></textarea></label>
        </form>
      {/if}

      {#if showMeetSlide}
        <form id="so-form" onsubmit={createMeet} class="space-y-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead</span>
            <select bind:value={meetForm.lead} required class={ic}><option value="">Select lead</option>{#each activeLeads as l}<option value={String(l.id)}>{l.full_name ?? `${l.first_name} ${l.last_name}`}</option>{/each}</select>
            {#if fieldErr(meetErrors, "lead")}<p class="mt-1 text-xs text-red-500">{fieldErr(meetErrors, "lead")}</p>{/if}</label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
            <input type="text" bind:value={meetForm.title} required class={ic} />{#if fieldErr(meetErrors, "title")}<p class="mt-1 text-xs text-red-500">{fieldErr(meetErrors, "title")}</p>{/if}</label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Type</span>
            <select bind:value={meetForm.meeting_type} class={ic}><option value="site_visit">Site Visit</option><option value="presentation">Presentation</option><option value="negotiation">Negotiation</option><option value="closing">Closing</option><option value="follow_up">Follow Up</option><option value="other">Other</option></select></label>
          <div class="grid grid-cols-2 gap-4">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Start</span><input type="datetime-local" bind:value={meetForm.scheduled_start} required class={ic} /></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">End</span><input type="datetime-local" bind:value={meetForm.scheduled_end} class={ic} /></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Location</span><input type="text" bind:value={meetForm.location} class={ic} /></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Meeting Link</span><input type="url" bind:value={meetForm.meeting_link} placeholder="https://..." class={ic} /></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Agenda</span><textarea bind:value={meetForm.agenda} rows="3" class="{ic} resize-none"></textarea></label>
        </form>
      {/if}
    </div>

    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      {#if isDev && showCommSlide}
        <button type="button" onclick={devFillComm} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      {#if isDev && showCampSlide}
        <button type="button" onclick={devFillCamp} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeAll} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" form="so-form" disabled={savingComm || savingCamp || savingRule || savingDoc || savingMeet}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
        {#if savingComm || savingCamp || savingRule || savingDoc || savingMeet}Saving...{:else}Save{/if}
      </button>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(e) => {
    if (e.key !== "Escape") return;
    if (showCampaignDetailDrawer) {
      closeCampaignDetailDrawer();
      return;
    }
    if (commDetail) {
      commDetail = null;
      return;
    }
    if (anySlide) closeAll();
  }}
/>

<style>
  .slide-over-enter { animation: slide-in-right 0.25s ease-out; }
  @keyframes slide-in-right { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .modal-enter { animation: modal-scale-in 0.2s ease-out; }
  @keyframes modal-scale-in { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
</style>
