import { api } from "$lib/api";
import type {
  DocumentRecord,
  PaginatedResponse,
  ProjectFieldEscalation,
} from "$lib/types";

export async function fetchAllPages<T>(
  endpoint: string,
  params: Record<string, string> = {},
  maxPages = 10
): Promise<T[]> {
  const rows: T[] = [];
  let page = 1;

  while (page <= maxPages) {
    const res = await api.get<PaginatedResponse<T>>(endpoint, {
      ...params,
      page: String(page),
    });
    rows.push(...res.results);
    if (!res.next || res.results.length === 0) break;
    page += 1;
  }

  return rows;
}

export function toAmount(value: string | number | null | undefined): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeText(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function looksLikeSubcontract(value: string): boolean {
  return value.includes("subcontract") || value.includes("sub-contract");
}

function looksLikeVariation(value: string): boolean {
  return value.includes("variation order") || (value.includes("variation") && value.includes("order"));
}

export function isSubcontractDocument(doc: DocumentRecord): boolean {
  const typeText = normalizeText(doc.document_type_name);
  const titleText = normalizeText(doc.title);
  const numberText = normalizeText(doc.document_number);
  return looksLikeSubcontract(typeText) || looksLikeSubcontract(titleText) || looksLikeSubcontract(numberText);
}

export function isVariationDocument(doc: DocumentRecord): boolean {
  const typeText = normalizeText(doc.document_type_name);
  const titleText = normalizeText(doc.title);
  return looksLikeVariation(typeText) || looksLikeVariation(titleText);
}

export function isMainContractDocument(doc: DocumentRecord): boolean {
  const typeText = normalizeText(doc.document_type_name);
  const titleText = normalizeText(doc.title);
  const numberText = normalizeText(doc.document_number);
  const contractLike =
    typeText.includes("contract")
    || titleText.includes("contract")
    || numberText.includes("-con-");
  if (!contractLike) return false;
  if (isSubcontractDocument(doc)) return false;
  if (isVariationDocument(doc)) return false;
  return true;
}

const CLAIM_TYPES = new Set([
  "cost_overrun",
  "payment_delay",
  "scope_change",
  "vendor_non_performance",
  "subcontractor_non_performance",
]);

const DISPUTE_TYPES = new Set([
  "labor_dispute",
  "community_complaint",
]);

export function isClaimIssue(issue: ProjectFieldEscalation): boolean {
  return CLAIM_TYPES.has(issue.issue_type);
}

export function isDisputeIssue(issue: ProjectFieldEscalation): boolean {
  return DISPUTE_TYPES.has(issue.issue_type);
}

