<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface BomMaster {
    id: number; bom_number: string; name: string; description: string;
    project: number | null; project_name: string | null;
    unit_type: string; quantity_of_units: number;
    status: string; version: number; confidence_pct: number;
    margin_pct: string; vat_pct: string; site_location: string;
    total_estimated_cost: string; subtotal: string;
    vat_amount: string; margin_amount: string; grand_total: string;
    fx_rate_usd_ngn: string; project_variables: Record<string, number>;
    item_count: number; created_by_name: string; created_at: string; updated_at: string;
  }
  interface BomItem {
    id: number; material_name: string; category: string; section: string;
    quantity: string; unit_of_measure: string; unit_cost: string; line_total: string;
    supplier: string; supplier_vendor_name: string | null; is_approved: boolean;
    source_bom: number | null; waste_factor_pct: string; item_markup_pct: string;
    effective_quantity: string; effective_line_total: string;
  }
  interface BomDetail extends BomMaster { items: BomItem[]; }

  let loading = $state(true);
  let masters = $state<BomMaster[]>([]);
  let activeMaster = $state<BomDetail | null>(null);
  let displayCurrency = $state<"NGN" | "USD">("NGN");

  const fxRate = $derived(activeMaster ? Number(activeMaster.fx_rate_usd_ngn) || 1550 : 1550);

  const sections = $derived.by(() => {
    if (!activeMaster) return [];
    const map = new Map<string, { items: BomItem[]; subtotal: number }>();
    for (const item of activeMaster.items) {
      const sec = item.section || "Uncategorized";
      if (!map.has(sec)) map.set(sec, { items: [], subtotal: 0 });
      const entry = map.get(sec)!;
      entry.items.push(item);
      entry.subtotal += Number(item.effective_line_total || item.line_total || 0);
    }
    return Array.from(map.entries()).map(([name, data]) => ({ name, ...data }));
  });

  const wsSubtotal = $derived(activeMaster ? Number(activeMaster.total_estimated_cost || 0) : 0);
  const wsMargin = $derived(wsSubtotal * Number(activeMaster?.margin_pct || 0) / 100);
  const wsVat = $derived(wsSubtotal * Number(activeMaster?.vat_pct || 0) / 100);
  const wsGrandTotal = $derived(wsSubtotal + wsVat + wsMargin);

  function fmt(n: number): string {
    if (displayCurrency === "USD") {
      const usd = fxRate > 0 ? n / fxRate : 0;
      return `$${usd.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    }
    return `\u20A6${Math.round(n).toLocaleString()}`;
  }

  async function loadMasters() {
    loading = true;
    try {
      const res = await api.get<{ results: BomMaster[] }>("/bom/", { page_size: "200", status: "approved" });
      masters = res.results;
    } catch { toast.error("Load failed", "Could not load approved BoQs."); }
    finally { loading = false; }
  }

  async function selectMaster(id: number) {
    loading = true;
    try {
      activeMaster = await api.get<BomDetail>(`/bom/${id}/`);
    } catch { toast.error("Load failed", "Could not load BoQ."); }
    finally { loading = false; }
  }

  function exportCSV() {
    if (!activeMaster) return;
    const headers = ["#", "Material", "Category", "Section", "Qty", "Unit", "Rate (NGN)", "Amount (NGN)", "Supplier", "Approved"];
    const rows = activeMaster.items.map((item, i) => [
      i + 1, `"${item.material_name}"`, `"${item.category}"`, `"${item.section}"`,
      item.quantity, item.unit_of_measure, item.unit_cost, item.line_total,
      `"${item.supplier || item.supplier_vendor_name || ""}"`, item.is_approved ? "Yes" : "No",
    ]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${activeMaster.bom_number}-master.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  function exportPDF() {
    if (!activeMaster) return;
    const sectionRows = sections.map(sec => {
      const items = sec.items.map((item, i) => `<tr><td style="padding:4px 8px;border-bottom:1px solid #eee">${i+1}</td><td style="padding:4px 8px;border-bottom:1px solid #eee">${item.material_name}</td><td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">${Number(item.quantity).toLocaleString()}</td><td style="padding:4px 8px;border-bottom:1px solid #eee">${item.unit_of_measure}</td><td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">\u20A6${Math.round(Number(item.unit_cost)).toLocaleString()}</td><td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:600">\u20A6${Math.round(Number(item.line_total)).toLocaleString()}</td></tr>`).join("");
      return `<tr style="background:#f5f5f5"><td colspan="6" style="padding:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;font-size:11px">${sec.name} — \u20A6${Math.round(sec.subtotal).toLocaleString()}</td></tr>${items}`;
    }).join("");
    const html = `<!DOCTYPE html><html><head><title>${activeMaster.bom_number} — BoQ Master</title><style>body{font-family:Raleway,sans-serif;margin:40px;color:#171717}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;padding:6px 8px;border-bottom:2px solid #333;font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:#737373}</style></head><body><h1 style="font-size:22px;margin-bottom:4px">${activeMaster.name}</h1><p style="color:#737373;font-size:12px">${activeMaster.bom_number} &middot; v${activeMaster.version}${activeMaster.project_name ? ` &middot; ${activeMaster.project_name}` : ""} &middot; APPROVED</p><hr style="margin:16px 0;border:none;border-top:1px solid #e5e5e5"><table><thead><tr><th>#</th><th>Description</th><th style="text-align:right">Qty</th><th>Unit</th><th style="text-align:right">Rate</th><th style="text-align:right">Amount</th></tr></thead><tbody>${sectionRows}</tbody></table><hr style="margin:16px 0;border:none;border-top:2px solid #333"><table style="width:300px;margin-left:auto;font-size:13px"><tr><td style="padding:4px 0">Subtotal</td><td style="text-align:right">\u20A6${Math.round(wsSubtotal).toLocaleString()}</td></tr><tr><td style="padding:4px 0">VAT (${Number(activeMaster.vat_pct)}%)</td><td style="text-align:right">\u20A6${Math.round(wsVat).toLocaleString()}</td></tr><tr><td style="padding:4px 0">Margin (${Number(activeMaster.margin_pct)}%)</td><td style="text-align:right">\u20A6${Math.round(wsMargin).toLocaleString()}</td></tr><tr style="border-top:2px solid #333"><td style="padding:8px 0;font-weight:700;font-size:15px">Grand Total</td><td style="text-align:right;font-weight:700;font-size:15px;color:#059669">\u20A6${Math.round(wsGrandTotal).toLocaleString()}</td></tr></table></body></html>`;
    const win = window.open("", "_blank");
    if (win) { win.document.write(html); win.document.close(); win.print(); }
  }

  onMount(() => { loadMasters(); });
</script>

<svelte:head><title>BoQ Master | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">BoQ Master</h1>
      <p class="mt-1 text-sm text-neutral-500">Approved and adopted bills of quantities — the financial source of truth for live projects.</p>
    </div>
    {#if activeMaster}
      <div class="flex gap-2">
        <div class="flex rounded-md border border-neutral-200 overflow-hidden">
          <button onclick={() => (displayCurrency = "NGN")} class="px-3 py-2 text-xs font-medium transition-colors {displayCurrency === 'NGN' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">{String.fromCharCode(8358)} NGN</button>
          <button onclick={() => (displayCurrency = "USD")} class="px-3 py-2 text-xs font-medium transition-colors {displayCurrency === 'USD' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">$ USD</button>
        </div>
        <button onclick={exportCSV} class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Download CSV</button>
        <button onclick={exportPDF} class="rounded-lg bg-neutral-900 px-4 py-2 text-xs font-medium text-white hover:bg-neutral-800">Client Quotation</button>
      </div>
    {/if}
  </div>

  <!-- Master selector -->
  <div class="flex items-center gap-4">
    <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectMaster(id); }} class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm font-medium min-w-[300px] focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">Select an approved BoQ...</option>
      {#each masters as m}
        <option value={m.id} selected={activeMaster?.id === m.id}>{m.bom_number} — {m.name}</option>
      {/each}
    </select>
    {#if masters.length === 0 && !loading}
      <span class="text-xs text-neutral-400">No approved BoQs yet. Approve a draft to see it here.</span>
    {/if}
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if !activeMaster}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      Select an approved BoQ to view the master record.
    </div>
  {:else}
    <!-- Control Center Header Card -->
    <div class="rounded-2xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(12px)">
      <!-- Dark header -->
      <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-white">{activeMaster.name}</h2>
            <p class="mt-0.5 text-sm text-neutral-400">{activeMaster.bom_number} &middot; v{activeMaster.version}</p>
            <div class="mt-2 flex items-center gap-2">
              {#if activeMaster.project_name}
                <span class="inline-flex items-center rounded-full bg-indigo-500/20 text-indigo-300 px-2.5 py-0.5 text-[11px] font-medium">{activeMaster.project_name}</span>
              {/if}
              <span class="inline-flex items-center rounded-full bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 text-[11px] font-medium">Approved</span>
              {#if activeMaster.site_location}
                <span class="inline-flex items-center rounded-full bg-white/10 text-neutral-300 px-2.5 py-0.5 text-[11px] font-medium">{activeMaster.site_location}</span>
              {/if}
            </div>
          </div>
          <div class="text-right">
            <p class="text-[10px] text-emerald-400 uppercase tracking-wider font-semibold">Total Estimated Value</p>
            <p class="text-2xl font-bold text-emerald-400 tabular-nums mt-1">{fmt(wsGrandTotal)}</p>
          </div>
        </div>
      </div>

      <!-- Key figures strip -->
      <div class="grid grid-cols-5 divide-x divide-neutral-100 border-b border-neutral-100">
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Subtotal</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-neutral-900">{fmt(wsSubtotal)}</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">VAT ({Number(activeMaster.vat_pct)}%)</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-neutral-900">{fmt(wsVat)}</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Margin ({Number(activeMaster.margin_pct)}%)</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-neutral-900">{fmt(wsMargin)}</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Line Items</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-blue-700">{activeMaster.items.length}</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Confidence</p>
          <p class="mt-0.5 text-base font-bold tabular-nums {activeMaster.confidence_pct >= 90 ? 'text-emerald-600' : activeMaster.confidence_pct >= 60 ? 'text-blue-600' : 'text-amber-600'}">{activeMaster.confidence_pct}%</p>
        </div>
      </div>

      <!-- Description -->
      {#if activeMaster.description}
        <div class="px-6 py-4 border-b border-neutral-100">
          <p class="text-sm text-neutral-600">{activeMaster.description}</p>
        </div>
      {/if}
    </div>

    <!-- Sectioned read-only table -->
    {#each sections as sec (sec.name)}
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 bg-neutral-800">
          <span class="text-xs font-bold text-white uppercase tracking-wider">{sec.name}</span>
          <span class="text-sm font-bold text-emerald-400 tabular-nums">{fmt(sec.subtotal)}</span>
        </div>
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-700">
              <th class="px-4 py-2 text-left font-medium text-neutral-200 w-8">#</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Description</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-200 w-20">Qty</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200 w-16">Unit</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-200 w-28">Rate</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-200 w-32">Amount</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200">Supplier</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each sec.items as item, idx (item.id)}
              <tr class="hover:bg-neutral-50/50 {item.source_bom ? 'pl-4' : ''}">
                <td class="px-4 py-2 text-neutral-400 tabular-nums">{idx + 1}</td>
                <td class="{item.source_bom ? 'pl-8' : 'px-4'} pr-4 py-2">
                  <div class="flex items-center gap-1.5 {item.source_bom ? 'border-l-2 border-indigo-200 pl-2' : ''}">
                    {#if item.is_approved}<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>{/if}
                    <span class="font-medium text-neutral-900">{item.material_name}</span>
                    {#if item.source_bom}<span class="text-[8px] text-indigo-400 ml-1">BOM</span>{/if}
                  </div>
                </td>
                <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{Number(item.quantity).toLocaleString()}</td>
                <td class="px-3 py-2 text-neutral-500">{item.unit_of_measure}</td>
                <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{fmt(Number(item.unit_cost))}</td>
                <td class="px-3 py-2 text-right tabular-nums font-semibold text-neutral-900">{fmt(Number(item.line_total))}</td>
                <td class="px-3 py-2 text-neutral-500">{item.supplier_vendor_name || item.supplier || "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/each}

    <!-- Grand Total Footer -->
    <div class="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-6 flex items-center justify-between" style="backdrop-filter: blur(12px)">
      <div>
        <p class="text-[10px] font-semibold text-emerald-600 uppercase tracking-widest">Grand Total</p>
        <p class="text-xs text-emerald-600 mt-0.5">Subtotal {fmt(wsSubtotal)} + VAT {fmt(wsVat)} + Margin {fmt(wsMargin)}</p>
      </div>
      <p class="text-3xl font-bold text-emerald-700 tabular-nums">{fmt(wsGrandTotal)}</p>
    </div>
  {/if}
</div>
