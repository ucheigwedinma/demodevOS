<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    ProjectListItem,
    ProjectVariationOrder,
    ProjectVariationOrderStatus,
  } from "$lib/types";

  let {
    open = false,
    projects = [],
    onclose,
    onsaved,
  }: {
    open?: boolean;
    projects?: ProjectListItem[];
    onclose?: () => void;
    onsaved?: () => void;
  } = $props();

  let saving = $state(false);
  let supportingFiles = $state<File[]>([]);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  type VariationForm = ReturnType<typeof defaultForm>;

  function defaultForm() {
    return {
      project: "",
      variation_number: "",
      title: "",
      change_summary: "",
      reason: "",
      status: "draft" as ProjectVariationOrderStatus,
      contract_value: "",
      requested_date: new Date().toISOString().slice(0, 10),
      due_date: "",
      related_document: "",
    };
  }

  const VARIATION_SAMPLES: VariationForm[] = [
    {
      project: "",
      variation_number: "",
      title: "Façade cladding material upgrade",
      change_summary: "Replace standard aluminium composite cladding on north and east elevations with natural stone rainscreen system per updated architect specification. Includes revised fixing brackets, additional waterproofing membrane, and extended installation programme.",
      reason: "Client directive following design review — upgraded finish to match neighbouring building standards and planning condition amendments.",
      status: "submitted",
      contract_value: "245000",
      requested_date: new Date().toISOString().slice(0, 10),
      due_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
      related_document: "",
    },
    {
      project: "",
      variation_number: "",
      title: "Additional piling for revised geotechnical report",
      change_summary: "Install 12 additional CFA piles (600mm diameter, 18m depth) on grid lines D-F after updated ground investigation revealed deeper-than-expected clay layer. Includes revised pile cap design and additional reinforcement.",
      reason: "Unforeseen ground conditions — supplementary geotechnical survey SI-2024-03 identified soft clay stratum 4m below original borehole depths.",
      status: "under_review",
      contract_value: "187500",
      requested_date: new Date().toISOString().slice(0, 10),
      due_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
      related_document: "",
    },
    {
      project: "",
      variation_number: "",
      title: "MEP riser relocation — Block C",
      change_summary: "Relocate main mechanical and electrical risers from grid line 7 to grid line 9 in Block C to accommodate enlarged lift shaft. Includes rerouting of HVAC ductwork, electrical busbar trunking, and plumbing stacks across floors 2-15.",
      reason: "Structural redesign of lift core required larger shaft dimensions, conflicting with original riser position.",
      status: "draft",
      contract_value: "312000",
      requested_date: new Date().toISOString().slice(0, 10),
      due_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      related_document: "",
    },
  ];

  let devIdx = 0;

  function devFill() {
    const sample = VARIATION_SAMPLES[devIdx % VARIATION_SAMPLES.length];
    devIdx++;
    form = {
      ...sample,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
    };
  }

  function reset() {
    form = defaultForm();
    supportingFiles = [];
  }

  function close() {
    reset();
    onclose?.();
  }

  function onFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    supportingFiles = Array.from(input.files ?? []);
  }

  function parseProjectId(value: string): number | null {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (firstField) return firstField;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  async function uploadSupportingFiles(variationId: number, files: File[]): Promise<boolean> {
    try {
      for (const file of files) {
        const payload = new FormData();
        payload.append("file", file);
        payload.append("caption", file.name);
        await api.upload(`/projects/variations/${variationId}/upload-supporting-file/`, payload);
      }
      return true;
    } catch {
      return false;
    }
  }

  async function handleSubmit(event: Event) {
    event.preventDefault();
    const projectId = parseProjectId(form.project);
    if (!projectId) {
      toast.error("Validation error", "Project is required.");
      return;
    }
    if (!form.title.trim()) {
      toast.error("Validation error", "Variation title is required.");
      return;
    }

    saving = true;
    try {
      const created = await api.post<ProjectVariationOrder>("/projects/variations/", {
        project: projectId,
        variation_number: form.variation_number.trim(),
        title: form.title.trim(),
        change_summary: form.change_summary.trim(),
        reason: form.reason.trim(),
        status: form.status,
        contract_value: form.contract_value || "0",
        currency: currency.config.code,
        requested_date: form.requested_date || new Date().toISOString().slice(0, 10),
        due_date: form.due_date || null,
        related_document: parseProjectId(form.related_document),
      });

      if (supportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(created.id, supportingFiles);
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Variation order was created, but supporting files failed to upload.",
          );
        }
      }

      toast.success("Variation created", `Variation ${created.variation_number} has been registered.`);
      reset();
      onclose?.();
      onsaved?.();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save variation order."));
    } finally {
      saving = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") close();
  }

  $effect(() => {
    if (open) reset();
  });
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={close}
    role="presentation"
  ></div>

  <!-- Drawer -->
  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[560px] bg-white shadow-2xl
           flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="New Variation Order"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-5 bg-linear-to-br from-neutral-900 to-neutral-800">
      <div class="min-w-0 flex-1">
        <h2 class="text-base font-semibold text-white">New Variation Order</h2>
        <p class="text-xs text-neutral-400 mt-0.5">Register a change order against a project</p>
      </div>
      <button
        onclick={close}
        class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white transition-colors ml-4 shrink-0"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto">
      <form onsubmit={handleSubmit} class="p-6 space-y-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span>
            <select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">Select project</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Variation Number (Optional)</span>
            <input bind:value={form.variation_number} placeholder="Auto-generated if empty" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span>
          <input bind:value={form.title} placeholder="e.g. Façade finish change order" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Change Summary</span>
          <textarea bind:value={form.change_summary} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Reason</span>
          <textarea bind:value={form.reason} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span>
          <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="superseded">Superseded</option>
            <option value="archived">Archived</option>
          </select>
        </label>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Contract Value</span>
            <input type="number" min="0" step="0.01" bind:value={form.contract_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Currency</span>
            <p class="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
              {currency.config.code}
            </p>
          </label>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Requested Date</span>
            <DateInput bind:value={form.requested_date} />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Due Date</span>
            <DateInput bind:value={form.due_date} />
          </label>
        </div>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Linked Document ID (Optional)</span>
          <input type="number" min="1" bind:value={form.related_document} placeholder="Repository document ID" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <label class="block rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
          <span class="block text-xs font-semibold uppercase tracking-wider text-neutral-500">Supporting Photos/Documents</span>
          <input type="file" multiple onchange={onFilesSelected} class="mt-2 w-full text-sm" />
          {#if supportingFiles.length > 0}
            <p class="mt-2 text-xs text-neutral-500">{supportingFiles.length} file(s) selected</p>
          {/if}
        </label>

        <!-- Actions -->
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
            Cancel
          </button>
          {#if isDev}
            <button
              type="button"
              onclick={devFill}
              class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
            >
              Dev Fill
            </button>
          {/if}
          <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
            {saving ? "Saving..." : "Create Variation"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>
