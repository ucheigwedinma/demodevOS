import { ApiError, api } from "$lib/api";
import type { PaginatedResponse } from "$lib/types";

export function parsePortalError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = error.data.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    for (const values of Object.values(error.fieldErrors)) {
      if (values.length > 0) return values[0];
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export async function fetchAllPortalPages<T>(
  endpoint: string,
  params: Record<string, string> = {},
  maxPages = 10,
): Promise<T[]> {
  const rows: T[] = [];
  let page = 1;

  while (page <= maxPages) {
    const response = await api.get<PaginatedResponse<T>>(endpoint, {
      ...params,
      page: String(page),
    });
    rows.push(...response.results);
    if (!response.next || response.results.length === 0) break;
    page += 1;
  }

  return rows;
}

