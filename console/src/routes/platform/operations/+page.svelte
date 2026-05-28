<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Operation {
    key: string;
    label: string;
    description: string;
    group: "seed" | "operations";
    status: "idle" | "running" | "success" | "error";
    output: string;
    showOutput: boolean;
  }

  let operations = $state<Operation[]>([
    // Seed Data
    { key: "seed_platform_editions", label: "Platform Editions", description: "Seed Essentials, Growth, Scale, and Custom tier definitions.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_platform_governance", label: "Platform Governance", description: "Seed event keys, email templates, workflows, and access policies.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_rbac", label: "Roles & Permissions", description: "Seed default RBAC roles and permission sets.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_master_data", label: "Master Data", description: "Seed master data entries (currencies, countries, etc.).", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_feature_flags", label: "Feature Flags", description: "Seed feature flag definitions with default states.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_metrics_contract", label: "KPI Definitions", description: "Seed KPI metric definitions and thresholds.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_access_scopes", label: "Access Scopes", description: "Seed data scope definitions for access control.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_access_policies", label: "Access Policies", description: "Seed default access control policies.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_risk_mitigation_rules", label: "Risk Mitigation Rules", description: "Seed risk mitigation strategies and rules.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_status_badges", label: "Status Badges", description: "Seed status badge definitions and color mappings.", group: "seed", status: "idle", output: "", showOutput: false },
    { key: "seed_project_templates", label: "Project Templates", description: "Seed default project templates with phases and tasks.", group: "seed", status: "idle", output: "", showOutput: false },
    // Operations
    { key: "dispatch_scheduled_reports", label: "Dispatch Reports", description: "Trigger dispatch of all due scheduled reports.", group: "operations", status: "idle", output: "", showOutput: false },
  ]);

  let seedOps = $derived(operations.filter((o) => o.group === "seed"));
  let otherOps = $derived(operations.filter((o) => o.group === "operations"));

  async function runOperation(op: Operation) {
    op.status = "running";
    op.output = "";
    op.showOutput = false;

    try {
      const res = await api.post<{ status: string; output?: string; detail?: string }>(
        "/platform/operations/run/",
        { command: op.key },
      );

      if (res.status === "ok") {
        op.status = "success";
        op.output = res.output ?? "Completed successfully.";
        toast.success(`${op.label}`, "Command executed successfully.");
      } else {
        op.status = "error";
        op.output = res.detail ?? "Unknown error.";
        toast.error(`${op.label} failed`, res.detail ?? "Unknown error.");
      }
    } catch (e) {
      op.status = "error";
      op.output = e instanceof Error ? e.message : "Request failed.";
      toast.error(`${op.label} failed`);
    }

    op.showOutput = true;
  }

  function statusIcon(status: Operation["status"]): string {
    switch (status) {
      case "idle": return "bg-neutral-100 text-neutral-400";
      case "running": return "bg-neutral-100 text-neutral-600";
      case "success": return "bg-emerald-50 text-emerald-600";
      case "error": return "bg-red-50 text-red-600";
    }
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div>
    <h1 class="text-xl font-semibold text-neutral-900">Operations</h1>
    <p class="text-sm text-neutral-500 mt-1">Run seed commands and platform operations. All commands are idempotent and safe to re-run.</p>
  </div>

  <!-- Seed Data -->
  <div>
    <h2 class="text-sm font-semibold text-neutral-900 mb-3">Seed Data</h2>
    <div class="grid grid-cols-2 gap-3">
      {#each seedOps as op}
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg {statusIcon(op.status)} flex items-center justify-center shrink-0 mt-0.5">
              {#if op.status === "running"}
                <div class="w-3.5 h-3.5 border-2 border-neutral-300 border-t-neutral-600 rounded-full animate-spin"></div>
              {:else if op.status === "success"}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              {:else if op.status === "error"}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                </svg>
              {/if}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <h3 class="text-sm font-medium text-neutral-900">{op.label}</h3>
                <button
                  onclick={() => runOperation(op)}
                  disabled={op.status === "running"}
                  class="px-3 py-1 text-xs font-medium rounded-lg border transition-colors shrink-0
                         {op.status === 'running'
                           ? 'border-neutral-100 text-neutral-400 cursor-not-allowed'
                           : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300'}"
                >
                  {op.status === "running" ? "Running..." : "Run"}
                </button>
              </div>
              <p class="text-xs text-neutral-500 mt-0.5">{op.description}</p>

              {#if op.showOutput && op.output}
                <div class="mt-2">
                  <button
                    onclick={() => op.showOutput = !op.showOutput}
                    class="text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
                  >
                    Hide output
                  </button>
                  <pre class="mt-1 text-xs text-neutral-600 bg-neutral-50 rounded-lg p-2 overflow-x-auto max-h-32 font-mono">{op.output}</pre>
                </div>
              {:else if op.output && !op.showOutput}
                <button
                  onclick={() => op.showOutput = true}
                  class="mt-1 text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  Show output
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Operations -->
  <div>
    <h2 class="text-sm font-semibold text-neutral-900 mb-3">Operations</h2>
    <div class="grid grid-cols-2 gap-3">
      {#each otherOps as op}
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg {statusIcon(op.status)} flex items-center justify-center shrink-0 mt-0.5">
              {#if op.status === "running"}
                <div class="w-3.5 h-3.5 border-2 border-neutral-300 border-t-neutral-600 rounded-full animate-spin"></div>
              {:else if op.status === "success"}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              {:else if op.status === "error"}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" />
                </svg>
              {/if}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <h3 class="text-sm font-medium text-neutral-900">{op.label}</h3>
                <button
                  onclick={() => runOperation(op)}
                  disabled={op.status === "running"}
                  class="px-3 py-1 text-xs font-medium rounded-lg border transition-colors shrink-0
                         {op.status === 'running'
                           ? 'border-neutral-100 text-neutral-400 cursor-not-allowed'
                           : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300'}"
                >
                  {op.status === "running" ? "Running..." : "Run"}
                </button>
              </div>
              <p class="text-xs text-neutral-500 mt-0.5">{op.description}</p>

              {#if op.showOutput && op.output}
                <div class="mt-2">
                  <button
                    onclick={() => op.showOutput = !op.showOutput}
                    class="text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
                  >
                    Hide output
                  </button>
                  <pre class="mt-1 text-xs text-neutral-600 bg-neutral-50 rounded-lg p-2 overflow-x-auto max-h-32 font-mono">{op.output}</pre>
                </div>
              {:else if op.output && !op.showOutput}
                <button
                  onclick={() => op.showOutput = true}
                  class="mt-1 text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  Show output
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  </div>
</div>
