/**
 * Conflict detection for collaborative editing.
 *
 * Before saving a record, compare the local `updated_at` snapshot
 * (taken when the form was loaded) against the server's current value.
 * If they differ, someone else saved in the meantime.
 *
 * Usage:
 *   const snapshot = captureTimestamp(record);  // when drawer opens
 *   ...
 *   if (await hasConflict(apiUrl, snapshot)) {
 *     toast.warning("Someone else saved this record. Reload?");
 *     return;
 *   }
 *   await save();
 */

import { api } from "$lib/api";

export function captureTimestamp(record: { updated_at?: string } | null): string | null {
  return record?.updated_at ?? null;
}

export async function hasConflict(
  endpoint: string,
  snapshotTimestamp: string | null,
): Promise<boolean> {
  if (!snapshotTimestamp) return false;
  try {
    const res = await api.get(endpoint);
    if (!res.ok) return false;
    const data = await res.json();
    const serverTimestamp = data.updated_at;
    if (!serverTimestamp) return false;
    return serverTimestamp !== snapshotTimestamp;
  } catch {
    return false;
  }
}
