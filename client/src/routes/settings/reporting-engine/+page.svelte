<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ReportingEngineSettings,
    ConfidentialityLabel,
    ReportTemplateListItem,
    ScheduledReportDispatch,
  } from "$lib/types";

  type Tab = "settings" | "templates" | "schedules" | "labels";
  let activeTab = $state<Tab>("settings");

  // ── Global settings (singleton) ──
  let loading = $state(true);
  let saving = $state(false);
  let form = $state<Partial<ReportingEngineSettings>>({});
  let newBoardRecipient = $state("");
  let newBoardSection = $state("");

  async function loadSettings() {
    try {
      const data = await api.get<ReportingEngineSettings>("/settings/reporting-engine/");
      form = data;
    } catch {
      toast.error("Load failed", "Could not load reporting engine settings.");
    } finally {
      loading = false;
    }
  }

  async function handleSaveSettings() {
    saving = true;
    try {
      const {
        id,
        created_at,
        updated_at,
        page_size_display,
        orientation_display,
        watermark_position_display,
        default_dispatch_format_display,
        board_pack_frequency_display,
        ...payload
      } = form as ReportingEngineSettings;
      const data = await api.patch<ReportingEngineSettings>("/settings/reporting-engine/", payload);
      form = data;
      toast.success("Saved", "Reporting engine settings updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  function addBoardRecipient() {
    const email = newBoardRecipient.trim();
    if (!email) return;
    if (!form.board_pack_recipients) form.board_pack_recipients = [];
    if (!form.board_pack_recipients.includes(email)) {
      form.board_pack_recipients = [...form.board_pack_recipients, email];
    }
    newBoardRecipient = "";
  }

  function removeBoardRecipient(email: string) {
    form.board_pack_recipients = (form.board_pack_recipients || []).filter((e) => e !== email);
  }

  function addBoardSection() {
    const section = newBoardSection.trim();
    if (!section) return;
    if (!form.board_pack_sections) form.board_pack_sections = [];
    if (!form.board_pack_sections.includes(section)) {
      form.board_pack_sections = [...form.board_pack_sections, section];
    }
    newBoardSection = "";
  }

  function removeBoardSection(section: string) {
    form.board_pack_sections = (form.board_pack_sections || []).filter((s) => s !== section);
  }

  // ── Report Templates (CRUD) ──
  let templates = $state<ReportTemplateListItem[]>([]);
  let templatesLoading = $state(true);
  let showTemplateForm = $state(false);
  let editingTemplateId = $state<number | null>(null);
  let templateForm = $state<Record<string, any>>({});

  async function loadTemplates() {
    templatesLoading = true;
    try {
      const data = await api.get<ReportTemplateListItem[]>("/settings/report-templates/");
      templates = Array.isArray(data) ? data : (data as any).results ?? [];
    } catch {
      toast.error("Load failed", "Could not load report templates.");
    } finally {
      templatesLoading = false;
    }
  }

  function openTemplateForm(tpl?: ReportTemplateListItem) {
    if (tpl) {
      editingTemplateId = tpl.id;
      templateForm = {
        name: tpl.name,
        code: tpl.code,
        description: tpl.description,
        template_type: tpl.template_type,
        output_format: tpl.output_format,
        confidentiality_label: tpl.confidentiality_label,
        is_active: tpl.is_active,
        data_sources: [],
        cross_module_joins: [],
      };
    } else {
      editingTemplateId = null;
      templateForm = {
        name: "",
        code: "",
        description: "",
        template_type: "financial",
        output_format: "pdf",
        confidentiality_label: null,
        is_active: true,
        data_sources: [],
        cross_module_joins: [],
      };
    }
    showTemplateForm = true;
  }

  async function saveTemplate() {
    try {
      if (editingTemplateId) {
        await api.patch(`/settings/report-templates/${editingTemplateId}/`, templateForm);
        toast.success("Updated", "Report template updated.");
      } else {
        await api.post("/settings/report-templates/", templateForm);
        toast.success("Created", "Report template created.");
      }
      showTemplateForm = false;
      loadTemplates();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    }
  }

  async function deleteTemplate(id: number) {
    if (!confirm("Delete this report template?")) return;
    try {
      await api.delete(`/settings/report-templates/${id}/`);
      toast.success("Deleted", "Report template removed.");
      loadTemplates();
    } catch {
      toast.error("Delete failed", "Could not delete report template.");
    }
  }

  // ── Scheduled Dispatches (CRUD) ──
  let schedules = $state<ScheduledReportDispatch[]>([]);
  let schedulesLoading = $state(true);
  let showScheduleForm = $state(false);
  let editingScheduleId = $state<number | null>(null);
  let scheduleForm = $state<Record<string, any>>({});
  let newScheduleRecipient = $state("");

  async function loadSchedules() {
    schedulesLoading = true;
    try {
      const data = await api.get<ScheduledReportDispatch[]>("/settings/scheduled-dispatches/");
      schedules = Array.isArray(data) ? data : (data as any).results ?? [];
    } catch {
      toast.error("Load failed", "Could not load scheduled dispatches.");
    } finally {
      schedulesLoading = false;
    }
  }

  function openScheduleForm(sched?: ScheduledReportDispatch) {
    if (sched) {
      editingScheduleId = sched.id;
      scheduleForm = {
        name: sched.name,
        report_template: sched.report_template,
        frequency: sched.frequency,
        dispatch_time: sched.dispatch_time,
        dispatch_day_of_week: sched.dispatch_day_of_week,
        dispatch_day_of_month: sched.dispatch_day_of_month,
        output_format: sched.output_format,
        recipients: [...sched.recipients],
        is_active: sched.is_active,
      };
    } else {
      editingScheduleId = null;
      scheduleForm = {
        name: "",
        report_template: null,
        frequency: "monthly",
        dispatch_time: "08:00",
        dispatch_day_of_week: null,
        dispatch_day_of_month: 1,
        output_format: "pdf",
        recipients: [],
        is_active: true,
      };
    }
    showScheduleForm = true;
  }

  function addScheduleRecipient() {
    const email = newScheduleRecipient.trim();
    if (!email) return;
    if (!scheduleForm.recipients) scheduleForm.recipients = [];
    if (!scheduleForm.recipients.includes(email)) {
      scheduleForm.recipients = [...scheduleForm.recipients, email];
    }
    newScheduleRecipient = "";
  }

  function removeScheduleRecipient(email: string) {
    scheduleForm.recipients = (scheduleForm.recipients || []).filter((e: string) => e !== email);
  }

  async function saveSchedule() {
    try {
      if (editingScheduleId) {
        await api.patch(`/settings/scheduled-dispatches/${editingScheduleId}/`, scheduleForm);
        toast.success("Updated", "Scheduled dispatch updated.");
      } else {
        await api.post("/settings/scheduled-dispatches/", scheduleForm);
        toast.success("Created", "Scheduled dispatch created.");
      }
      showScheduleForm = false;
      loadSchedules();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    }
  }

  async function deleteSchedule(id: number) {
    if (!confirm("Delete this scheduled dispatch?")) return;
    try {
      await api.delete(`/settings/scheduled-dispatches/${id}/`);
      toast.success("Deleted", "Scheduled dispatch removed.");
      loadSchedules();
    } catch {
      toast.error("Delete failed", "Could not delete scheduled dispatch.");
    }
  }

  // ── Confidentiality Labels (CRUD) ──
  let labels = $state<ConfidentialityLabel[]>([]);
  let labelsLoading = $state(true);
  let showLabelForm = $state(false);
  let editingLabelId = $state<number | null>(null);
  let labelForm = $state<Record<string, any>>({});

  async function loadLabels() {
    labelsLoading = true;
    try {
      const data = await api.get<ConfidentialityLabel[]>("/settings/confidentiality-labels/");
      labels = Array.isArray(data) ? data : (data as any).results ?? [];
    } catch {
      toast.error("Load failed", "Could not load confidentiality labels.");
    } finally {
      labelsLoading = false;
    }
  }

  function openLabelForm(lbl?: ConfidentialityLabel) {
    if (lbl) {
      editingLabelId = lbl.id;
      labelForm = {
        name: lbl.name,
        code: lbl.code,
        description: lbl.description,
        access_level: lbl.access_level,
        color: lbl.color,
        watermark_override: lbl.watermark_override,
        restrict_printing: lbl.restrict_printing,
        restrict_download: lbl.restrict_download,
        is_active: lbl.is_active,
        sort_order: lbl.sort_order,
      };
    } else {
      editingLabelId = null;
      labelForm = {
        name: "",
        code: "",
        description: "",
        access_level: "internal",
        color: "#6B7280",
        watermark_override: false,
        restrict_printing: false,
        restrict_download: false,
        is_active: true,
        sort_order: 0,
      };
    }
    showLabelForm = true;
  }

  async function saveLabel() {
    try {
      if (editingLabelId) {
        await api.patch(`/settings/confidentiality-labels/${editingLabelId}/`, labelForm);
        toast.success("Updated", "Confidentiality label updated.");
      } else {
        await api.post("/settings/confidentiality-labels/", labelForm);
        toast.success("Created", "Confidentiality label created.");
      }
      showLabelForm = false;
      loadLabels();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", messages[0] || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    }
  }

  async function deleteLabel(id: number) {
    if (!confirm("Delete this confidentiality label?")) return;
    try {
      await api.delete(`/settings/confidentiality-labels/${id}/`);
      toast.success("Deleted", "Confidentiality label removed.");
      loadLabels();
    } catch {
      toast.error("Delete failed", "Could not delete confidentiality label.");
    }
  }

  // ── Init ──
  $effect(() => {
    loadSettings();
    loadTemplates();
    loadSchedules();
    loadLabels();
  });

  const daysOfWeek = [
    { value: 0, label: "Monday" },
    { value: 1, label: "Tuesday" },
    { value: 2, label: "Wednesday" },
    { value: 3, label: "Thursday" },
    { value: 4, label: "Friday" },
    { value: 5, label: "Saturday" },
    { value: 6, label: "Sunday" },
  ];
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h2 class="text-xl font-semibold text-neutral-800">Reporting Engine</h2>
      <p class="text-sm text-neutral-500 mt-1">Configure report templates, PDF standards, scheduling, and confidentiality labels.</p>
    </div>
    {#if activeTab === "settings"}
      <button
        onclick={handleSaveSettings}
        disabled={saving}
        class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving…" : "Save Changes"}
      </button>
    {/if}
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 border-b border-neutral-200 mb-6">
    {#each [
      { key: "settings", label: "Global Settings" },
      { key: "templates", label: "Report Templates" },
      { key: "schedules", label: "Scheduled Dispatches" },
      { key: "labels", label: "Confidentiality Labels" },
    ] as tab}
      <button
        onclick={() => (activeTab = tab.key as Tab)}
        class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors {activeTab === tab.key
          ? 'border-neutral-800 text-neutral-800'
          : 'border-transparent text-neutral-500 hover:text-neutral-700'}"
      >
        {tab.label}
      </button>
    {/each}
  </div>

  <!-- ═══ TAB: Global Settings ═══ -->
  {#if activeTab === "settings"}
    <div class="space-y-6">
      <!-- PDF Formatting Standards -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-800 mb-4">PDF Formatting Standards</h3>
        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Page Size</span>
            <select bind:value={form.page_size} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
              <option value="a4">A4 (210 × 297 mm)</option>
              <option value="letter">US Letter (8.5 × 11 in)</option>
              <option value="legal">US Legal (8.5 × 14 in)</option>
              <option value="a3">A3 (297 × 420 mm)</option>
            </select>
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Orientation</span>
            <select bind:value={form.orientation} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
            </select>
          </label>
        </div>
        <div class="grid grid-cols-4 gap-4 mt-4">
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Top Margin (mm)</span>
            <input type="number" bind:value={form.margin_top_mm} min="0" max="100" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Bottom Margin (mm)</span>
            <input type="number" bind:value={form.margin_bottom_mm} min="0" max="100" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Left Margin (mm)</span>
            <input type="number" bind:value={form.margin_left_mm} min="0" max="100" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Right Margin (mm)</span>
            <input type="number" bind:value={form.margin_right_mm} min="0" max="100" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
        </div>
        <div class="grid grid-cols-2 gap-4 mt-4">
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Font Family</span>
            <input type="text" bind:value={form.font_family} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Font Size (pt)</span>
            <input type="number" bind:value={form.font_size_pt} min="6" max="24" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
        </div>
        <!-- Header / Footer -->
        <div class="mt-4 space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-neutral-800">Header</p>
              <p class="text-xs text-neutral-500">Display header on every page. Supports: {"{org_name}"}, {"{report_title}"}, {"{date}"}</p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              onclick={() => (form.header_enabled = !form.header_enabled)}
              class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.header_enabled ? 'bg-neutral-800' : 'bg-neutral-300'}"
            >
              <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.header_enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
            </button>
          </div>
          {#if form.header_enabled}
            <input type="text" bind:value={form.header_text} placeholder="e.g. {'{org_name}'} — {'{report_title}'}" class="block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          {/if}

          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-neutral-800">Footer</p>
              <p class="text-xs text-neutral-500">Display footer on every page. Supports: {"{page}"}, {"{total_pages}"}, {"{date}"}</p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              onclick={() => (form.footer_enabled = !form.footer_enabled)}
              class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.footer_enabled ? 'bg-neutral-800' : 'bg-neutral-300'}"
            >
              <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.footer_enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
            </button>
          </div>
          {#if form.footer_enabled}
            <input type="text" bind:value={form.footer_text} placeholder="Page {'{page}'} of {'{total_pages}'}" class="block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          {/if}
        </div>
        <!-- Cover page & TOC -->
        <div class="mt-4 space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-neutral-800">Include Cover Page</p>
              <p class="text-xs text-neutral-500">Auto-generate a cover page with org branding and report title</p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              onclick={() => (form.include_cover_page = !form.include_cover_page)}
              class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.include_cover_page ? 'bg-neutral-800' : 'bg-neutral-300'}"
            >
              <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.include_cover_page ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
            </button>
          </div>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-neutral-800">Include Table of Contents</p>
              <p class="text-xs text-neutral-500">Auto-generate a table of contents for multi-section reports</p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              onclick={() => (form.include_table_of_contents = !form.include_table_of_contents)}
              class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.include_table_of_contents ? 'bg-neutral-800' : 'bg-neutral-300'}"
            >
              <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.include_table_of_contents ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
            </button>
          </div>
        </div>
      </div>

      <!-- Watermark Rules -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-800 mb-4">Watermark Rules</h3>
        <div class="flex items-center justify-between mb-4">
          <div>
            <p class="text-sm font-medium text-neutral-800">Enable Watermark</p>
            <p class="text-xs text-neutral-500">Apply watermark text to generated report PDFs</p>
          </div>
          <!-- svelte-ignore a11y_consider_explicit_label -->
          <button
            onclick={() => (form.watermark_enabled = !form.watermark_enabled)}
            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.watermark_enabled ? 'bg-neutral-800' : 'bg-neutral-300'}"
          >
            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.watermark_enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
          </button>
        </div>
        {#if form.watermark_enabled}
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Watermark Text</span>
              <input type="text" bind:value={form.watermark_text} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Position</span>
              <select bind:value={form.watermark_position} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="center">Center</option>
                <option value="diagonal">Diagonal</option>
                <option value="top">Top</option>
                <option value="bottom">Bottom</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Opacity (%)</span>
              <input type="number" bind:value={form.watermark_opacity} min="1" max="100" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Color</span>
              <div class="mt-1 flex items-center gap-2">
                <input type="color" bind:value={form.watermark_color} class="h-9 w-9 rounded border border-neutral-300 cursor-pointer" />
                <input type="text" bind:value={form.watermark_color} class="block flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
              </div>
            </label>
          </div>
        {/if}
      </div>

      <!-- Board Pack Automation -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-800 mb-4">Board Pack Automation</h3>
        <div class="flex items-center justify-between mb-4">
          <div>
            <p class="text-sm font-medium text-neutral-800">Enable Board Pack</p>
            <p class="text-xs text-neutral-500">Automatically compile and distribute board packs on a schedule</p>
          </div>
          <!-- svelte-ignore a11y_consider_explicit_label -->
          <button
            onclick={() => (form.board_pack_enabled = !form.board_pack_enabled)}
            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {form.board_pack_enabled ? 'bg-neutral-800' : 'bg-neutral-300'}"
          >
            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {form.board_pack_enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
          </button>
        </div>
        {#if form.board_pack_enabled}
          <div class="grid grid-cols-2 gap-4 mb-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Frequency</span>
              <select bind:value={form.board_pack_frequency} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="semi_annual">Semi-Annual</option>
                <option value="annual">Annual</option>
              </select>
            </label>
          </div>
          <!-- Board Pack Recipients -->
          <div class="mb-4">
            <span class="text-xs font-medium text-neutral-600">Recipients</span>
            <div class="mt-1 flex gap-2">
              <input
                type="email"
                bind:value={newBoardRecipient}
                onkeydown={(e) => e.key === "Enter" && (e.preventDefault(), addBoardRecipient())}
                placeholder="email@example.com"
                class="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"
              />
              <button onclick={addBoardRecipient} class="px-3 py-2 bg-neutral-100 text-neutral-700 text-sm rounded-lg hover:bg-neutral-200 transition-colors">Add</button>
            </div>
            {#if (form.board_pack_recipients || []).length > 0}
              <div class="flex flex-wrap gap-2 mt-2">
                {#each form.board_pack_recipients || [] as email}
                  <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-neutral-100 text-neutral-700 text-xs rounded-full">
                    {email}
                    <button onclick={() => removeBoardRecipient(email)} class="text-neutral-400 hover:text-neutral-600">&times;</button>
                  </span>
                {/each}
              </div>
            {/if}
          </div>
          <!-- Board Pack Sections -->
          <div>
            <span class="text-xs font-medium text-neutral-600">Report Sections (template codes)</span>
            <div class="mt-1 flex gap-2">
              <input
                type="text"
                bind:value={newBoardSection}
                onkeydown={(e) => e.key === "Enter" && (e.preventDefault(), addBoardSection())}
                placeholder="e.g. FINANCIAL_SUMMARY"
                class="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"
              />
              <button onclick={addBoardSection} class="px-3 py-2 bg-neutral-100 text-neutral-700 text-sm rounded-lg hover:bg-neutral-200 transition-colors">Add</button>
            </div>
            {#if (form.board_pack_sections || []).length > 0}
              <div class="flex flex-wrap gap-2 mt-2">
                {#each form.board_pack_sections || [] as section}
                  <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-mono">
                    {section}
                    <button onclick={() => removeBoardSection(section)} class="text-blue-400 hover:text-blue-600">&times;</button>
                  </span>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Dispatch Defaults -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-800 mb-4">Dispatch Defaults</h3>
        <div class="grid grid-cols-3 gap-4">
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Default Output Format</span>
            <select bind:value={form.default_dispatch_format} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
              <option value="pdf">PDF</option>
              <option value="xlsx">Excel (XLSX)</option>
              <option value="csv">CSV</option>
            </select>
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Retention Period (days)</span>
            <input type="number" bind:value={form.dispatch_retention_days} min="1" max="730" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Reply-To Email</span>
            <input type="email" bind:value={form.dispatch_reply_to_email} placeholder="reports@company.com" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
          </label>
        </div>
      </div>
    </div>

  <!-- ═══ TAB: Report Templates ═══ -->
  {:else if activeTab === "templates"}
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-500">{templates.length} template{templates.length !== 1 ? "s" : ""}</p>
        <button onclick={() => openTemplateForm()} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
          Add Template
        </button>
      </div>

      {#if showTemplateForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">{editingTemplateId ? "Edit Template" : "New Template"}</h3>
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Name</span>
              <input type="text" bind:value={templateForm.name} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Code</span>
              <input type="text" bind:value={templateForm.code} placeholder="e.g. FINANCIAL_SUMMARY" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Type</span>
              <select bind:value={templateForm.template_type} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="financial">Financial</option>
                <option value="operational">Operational</option>
                <option value="compliance">Compliance</option>
                <option value="executive">Executive Summary</option>
                <option value="project">Project</option>
                <option value="property">Property</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Output Format</span>
              <select bind:value={templateForm.output_format} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel (XLSX)</option>
                <option value="csv">CSV</option>
                <option value="pdf_xlsx">PDF + Excel</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Confidentiality Label</span>
              <select bind:value={templateForm.confidentiality_label} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value={null}>None</option>
                {#each labels.filter(l => l.is_active) as label}
                  <option value={label.id}>{label.name}</option>
                {/each}
              </select>
            </label>
            <label class="flex items-center gap-2 self-end pb-2">
              <input type="checkbox" bind:checked={templateForm.is_active} class="rounded border-neutral-300" />
              <span class="text-sm text-neutral-700">Active</span>
            </label>
          </div>
          <label class="block mt-4">
            <span class="text-xs font-medium text-neutral-600">Description</span>
            <textarea bind:value={templateForm.description} rows="2" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"></textarea>
          </label>
          <!-- Data Sources (JSON) -->
          <div class="mt-4 p-3 bg-neutral-50 rounded-lg">
            <p class="text-xs font-medium text-neutral-600 mb-1">Data Sources (JSON)</p>
            <p class="text-xs text-neutral-400 mb-2">Define which modules/entities to pull data from. Format: [{'{'}module, entity, fields, filters{'}'}]</p>
            <textarea
              value={JSON.stringify(templateForm.data_sources || [], null, 2)}
              oninput={(e) => { try { templateForm.data_sources = JSON.parse(e.currentTarget.value); } catch {} }}
              rows="4"
              class="block w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"
            ></textarea>
          </div>
          <!-- Cross-Module Joins (JSON) -->
          <div class="mt-3 p-3 bg-neutral-50 rounded-lg">
            <p class="text-xs font-medium text-neutral-600 mb-1">Cross-Module Joins (JSON)</p>
            <p class="text-xs text-neutral-400 mb-2">Define join relationships. Format: [{'{'}left_source, right_source, join_key, join_type{'}'}]</p>
            <textarea
              value={JSON.stringify(templateForm.cross_module_joins || [], null, 2)}
              oninput={(e) => { try { templateForm.cross_module_joins = JSON.parse(e.currentTarget.value); } catch {} }}
              rows="4"
              class="block w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"
            ></textarea>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button onclick={() => (showTemplateForm = false)} class="px-4 py-2 text-sm text-neutral-600 hover:text-neutral-800 transition-colors">Cancel</button>
            <button onclick={saveTemplate} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
              {editingTemplateId ? "Update" : "Create"}
            </button>
          </div>
        </div>
      {/if}

      {#if templatesLoading}
        <div class="flex items-center justify-center py-10">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if templates.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-10 text-center">
          <p class="text-sm text-neutral-500">No report templates configured yet.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Code</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Name</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Type</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Format</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Label</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Schedules</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Status</th>
                <th class="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each templates as tpl}
                <tr class="hover:bg-neutral-50">
                  <td class="px-4 py-3 font-mono text-xs text-neutral-700">{tpl.code}</td>
                  <td class="px-4 py-3 text-neutral-800">{tpl.name}</td>
                  <td class="px-4 py-3 text-neutral-600">{tpl.template_type_display}</td>
                  <td class="px-4 py-3 text-neutral-600">{tpl.output_format_display}</td>
                  <td class="px-4 py-3">
                    {#if tpl.confidentiality_label_name}
                      <span class="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-700">{tpl.confidentiality_label_name}</span>
                    {:else}
                      <span class="text-xs text-neutral-400">—</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-neutral-600">{tpl.schedule_count}</td>
                  <td class="px-4 py-3">
                    <span class="text-xs px-2 py-0.5 rounded-full {tpl.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                      {tpl.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button onclick={() => openTemplateForm(tpl)} class="text-xs text-neutral-500 hover:text-neutral-800 mr-2">Edit</button>
                    {#if !tpl.is_system}
                      <button onclick={() => deleteTemplate(tpl.id)} class="text-xs text-red-500 hover:text-red-700">Delete</button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

  <!-- ═══ TAB: Scheduled Dispatches ═══ -->
  {:else if activeTab === "schedules"}
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-500">{schedules.length} schedule{schedules.length !== 1 ? "s" : ""}</p>
        <button onclick={() => openScheduleForm()} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
          Add Schedule
        </button>
      </div>

      {#if showScheduleForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">{editingScheduleId ? "Edit Schedule" : "New Schedule"}</h3>
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Name</span>
              <input type="text" bind:value={scheduleForm.name} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Report Template</span>
              <select bind:value={scheduleForm.report_template} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value={null}>Select template…</option>
                {#each templates.filter(t => t.is_active) as tpl}
                  <option value={tpl.id}>{tpl.name} ({tpl.code})</option>
                {/each}
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Frequency</span>
              <select bind:value={scheduleForm.frequency} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Dispatch Time</span>
              <input type="time" bind:value={scheduleForm.dispatch_time} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            {#if scheduleForm.frequency === "weekly"}
              <label class="block">
                <span class="text-xs font-medium text-neutral-600">Day of Week</span>
                <select bind:value={scheduleForm.dispatch_day_of_week} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                  {#each daysOfWeek as day}
                    <option value={day.value}>{day.label}</option>
                  {/each}
                </select>
              </label>
            {/if}
            {#if ["monthly", "quarterly", "annual"].includes(scheduleForm.frequency)}
              <label class="block">
                <span class="text-xs font-medium text-neutral-600">Day of Month (1–28)</span>
                <input type="number" bind:value={scheduleForm.dispatch_day_of_month} min="1" max="28" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
              </label>
            {/if}
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Output Format</span>
              <select bind:value={scheduleForm.output_format} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel (XLSX)</option>
                <option value="csv">CSV</option>
                <option value="pdf_xlsx">PDF + Excel</option>
              </select>
            </label>
            <label class="flex items-center gap-2 self-end pb-2">
              <input type="checkbox" bind:checked={scheduleForm.is_active} class="rounded border-neutral-300" />
              <span class="text-sm text-neutral-700">Active</span>
            </label>
          </div>
          <!-- Recipients -->
          <div class="mt-4">
            <span class="text-xs font-medium text-neutral-600">Recipients</span>
            <div class="mt-1 flex gap-2">
              <input
                type="email"
                bind:value={newScheduleRecipient}
                onkeydown={(e) => e.key === "Enter" && (e.preventDefault(), addScheduleRecipient())}
                placeholder="email@example.com"
                class="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"
              />
              <button onclick={addScheduleRecipient} class="px-3 py-2 bg-neutral-100 text-neutral-700 text-sm rounded-lg hover:bg-neutral-200 transition-colors">Add</button>
            </div>
            {#if (scheduleForm.recipients || []).length > 0}
              <div class="flex flex-wrap gap-2 mt-2">
                {#each scheduleForm.recipients || [] as email}
                  <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-neutral-100 text-neutral-700 text-xs rounded-full">
                    {email}
                    <button onclick={() => removeScheduleRecipient(email)} class="text-neutral-400 hover:text-neutral-600">&times;</button>
                  </span>
                {/each}
              </div>
            {/if}
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button onclick={() => (showScheduleForm = false)} class="px-4 py-2 text-sm text-neutral-600 hover:text-neutral-800 transition-colors">Cancel</button>
            <button onclick={saveSchedule} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
              {editingScheduleId ? "Update" : "Create"}
            </button>
          </div>
        </div>
      {/if}

      {#if schedulesLoading}
        <div class="flex items-center justify-center py-10">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if schedules.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-10 text-center">
          <p class="text-sm text-neutral-500">No scheduled dispatches configured yet.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Name</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Template</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Frequency</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Time</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Format</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Recipients</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Status</th>
                <th class="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each schedules as sched}
                <tr class="hover:bg-neutral-50">
                  <td class="px-4 py-3 text-neutral-800">{sched.name}</td>
                  <td class="px-4 py-3 text-neutral-600 font-mono text-xs">{sched.report_template_code}</td>
                  <td class="px-4 py-3 text-neutral-600">{sched.frequency_display}</td>
                  <td class="px-4 py-3 text-neutral-600">{sched.dispatch_time}</td>
                  <td class="px-4 py-3 text-neutral-600">{sched.output_format_display}</td>
                  <td class="px-4 py-3 text-neutral-600">{sched.recipients.length}</td>
                  <td class="px-4 py-3">
                    <span class="text-xs px-2 py-0.5 rounded-full {sched.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                      {sched.is_active ? "Active" : "Paused"}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button onclick={() => openScheduleForm(sched)} class="text-xs text-neutral-500 hover:text-neutral-800 mr-2">Edit</button>
                    <button onclick={() => deleteSchedule(sched.id)} class="text-xs text-red-500 hover:text-red-700">Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

  <!-- ═══ TAB: Confidentiality Labels ═══ -->
  {:else if activeTab === "labels"}
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-500">{labels.length} label{labels.length !== 1 ? "s" : ""}</p>
        <button onclick={() => openLabelForm()} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
          Add Label
        </button>
      </div>

      {#if showLabelForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-800 mb-4">{editingLabelId ? "Edit Label" : "New Label"}</h3>
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Name</span>
              <input type="text" bind:value={labelForm.name} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Code</span>
              <input type="text" bind:value={labelForm.code} placeholder="e.g. confidential" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Access Level</span>
              <select bind:value={labelForm.access_level} class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500">
                <option value="public">Public</option>
                <option value="internal">Internal</option>
                <option value="confidential">Confidential</option>
                <option value="strictly_confidential">Strictly Confidential</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Badge Color</span>
              <div class="mt-1 flex items-center gap-2">
                <input type="color" bind:value={labelForm.color} class="h-9 w-9 rounded border border-neutral-300 cursor-pointer" />
                <input type="text" bind:value={labelForm.color} class="block flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
              </div>
            </label>
            <label class="block col-span-2">
              <span class="text-xs font-medium text-neutral-600">Description</span>
              <textarea bind:value={labelForm.description} rows="2" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500"></textarea>
            </label>
          </div>
          <div class="mt-4 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-800">Force Watermark</p>
                <p class="text-xs text-neutral-500">Override global watermark settings for reports with this label</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                onclick={() => (labelForm.watermark_override = !labelForm.watermark_override)}
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {labelForm.watermark_override ? 'bg-neutral-800' : 'bg-neutral-300'}"
              >
                <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {labelForm.watermark_override ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
              </button>
            </div>
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-800">Restrict Printing</p>
                <p class="text-xs text-neutral-500">Prevent printing of reports with this classification</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                onclick={() => (labelForm.restrict_printing = !labelForm.restrict_printing)}
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {labelForm.restrict_printing ? 'bg-neutral-800' : 'bg-neutral-300'}"
              >
                <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {labelForm.restrict_printing ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
              </button>
            </div>
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-neutral-800">Restrict Download</p>
                <p class="text-xs text-neutral-500">Prevent downloading of reports with this classification</p>
              </div>
              <!-- svelte-ignore a11y_consider_explicit_label -->
              <button
                onclick={() => (labelForm.restrict_download = !labelForm.restrict_download)}
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {labelForm.restrict_download ? 'bg-neutral-800' : 'bg-neutral-300'}"
              >
                <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {labelForm.restrict_download ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
              </button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4 mt-4">
            <label class="block">
              <span class="text-xs font-medium text-neutral-600">Sort Order</span>
              <input type="number" bind:value={labelForm.sort_order} min="0" class="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500" />
            </label>
            <label class="flex items-center gap-2 self-end pb-2">
              <input type="checkbox" bind:checked={labelForm.is_active} class="rounded border-neutral-300" />
              <span class="text-sm text-neutral-700">Active</span>
            </label>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button onclick={() => (showLabelForm = false)} class="px-4 py-2 text-sm text-neutral-600 hover:text-neutral-800 transition-colors">Cancel</button>
            <button onclick={saveLabel} class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
              {editingLabelId ? "Update" : "Create"}
            </button>
          </div>
        </div>
      {/if}

      {#if labelsLoading}
        <div class="flex items-center justify-center py-10">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
        </div>
      {:else if labels.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-10 text-center">
          <p class="text-sm text-neutral-500">No confidentiality labels configured yet.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Label</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Code</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Access Level</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Watermark</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Restrictions</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase">Status</th>
                <th class="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each labels as label}
                <tr class="hover:bg-neutral-50">
                  <td class="px-4 py-3">
                    <span class="inline-flex items-center gap-2">
                      <span class="w-3 h-3 rounded-full" style="background-color: {label.color}"></span>
                      <span class="text-neutral-800">{label.name}</span>
                    </span>
                  </td>
                  <td class="px-4 py-3 font-mono text-xs text-neutral-600">{label.code}</td>
                  <td class="px-4 py-3 text-neutral-600">{label.access_level_display}</td>
                  <td class="px-4 py-3">
                    {#if label.watermark_override}
                      <span class="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">Forced</span>
                    {:else}
                      <span class="text-xs text-neutral-400">Default</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3">
                    <span class="text-xs text-neutral-500">
                      {[
                        label.restrict_printing && "No Print",
                        label.restrict_download && "No Download",
                      ].filter(Boolean).join(", ") || "None"}
                    </span>
                  </td>
                  <td class="px-4 py-3">
                    <span class="text-xs px-2 py-0.5 rounded-full {label.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                      {label.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button onclick={() => openLabelForm(label)} class="text-xs text-neutral-500 hover:text-neutral-800 mr-2">Edit</button>
                    {#if !label.is_system}
                      <button onclick={() => deleteLabel(label.id)} class="text-xs text-red-500 hover:text-red-700">Delete</button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
{/if}
