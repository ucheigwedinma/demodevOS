/**
 * Real-time auto-refresh utility for data tables and dashboards.
 *
 * Usage in any page:
 *
 *   import { useAutoRefresh } from "$lib/realtime.svelte";
 *
 *   // Single model:
 *   useAutoRefresh("PurchaseOrder", fetchData);
 *
 *   // Multiple models:
 *   useAutoRefresh(["PurchaseOrder", "GoodsReceipt", "Bill"], fetchData);
 *
 *   // With debounce (default 2s):
 *   useAutoRefresh("Lead", fetchLeads, { debounceMs: 3000 });
 *
 *   // Only on specific actions:
 *   useAutoRefresh("PurchaseOrder", fetchPOs, { actions: ["created", "deleted"] });
 *
 *   // Dashboard mode — returns reactive refreshing flag:
 *   const live = useLiveKpis(["Project", "Bill", "Invoice"], loadDashboard, { debounceMs: 3000 });
 *   // live.refreshing is true while the fetch is running
 *
 * The fetch function is called automatically when a matching WebSocket
 * `data.changed` event arrives. Debounced to prevent flooding on rapid changes.
 */

import { ws } from "$lib/stores/websocket.svelte";

interface AutoRefreshOptions {
  /** Debounce time in ms (default 2000) */
  debounceMs?: number;
  /** Only refresh on these actions (default: all) */
  actions?: ("created" | "updated" | "deleted")[];
}

/**
 * Auto-refresh a fetch function when a matching model change arrives via WebSocket.
 *
 * Call this at the top level of your component's <script> block.
 */
export function useAutoRefresh(
  models: string | string[],
  fetchFn: () => void | Promise<void>,
  options?: AutoRefreshOptions,
) {
  const modelSet = new Set(Array.isArray(models) ? models : [models]);
  const debounceMs = options?.debounceMs ?? 2000;
  const allowedActions = options?.actions ? new Set(options.actions) : null;
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  $effect(() => {
    const change = ws.lastDataChange;
    if (!change) return;
    if (!modelSet.has(change.model)) return;
    if (allowedActions && !allowedActions.has(change.action)) return;

    // Debounce to prevent rapid re-fetches
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      fetchFn();
    }, debounceMs);
  });
}

/**
 * Dashboard variant of useAutoRefresh that exposes a reactive `refreshing` flag.
 * Use with the LiveBadge component for visual feedback.
 *
 * Call this at the top level of your component's <script> block.
 */
export function useLiveKpis(
  models: string | string[],
  fetchFn: () => void | Promise<void>,
  options?: AutoRefreshOptions,
): { readonly refreshing: boolean } {
  let refreshing = $state(false);

  const wrappedFetch = async () => {
    refreshing = true;
    try {
      await fetchFn();
    } finally {
      refreshing = false;
    }
  };

  useAutoRefresh(models, wrappedFetch, options);

  return {
    get refreshing() { return refreshing; },
  };
}
