import { api } from "$lib/api";
import type {
  BudgetLineItemRead,
  BudgetListItem,
  MasterDataEntry,
  PaginatedResponse,
} from "$lib/types";

export type BudgetLineOption = {
  id: number;
  label: string;
  budgetName: string;
};

export async function fetchBudgetLineOptions(): Promise<BudgetLineOption[]> {
  try {
    const budgetRes = await api.get<PaginatedResponse<BudgetListItem>>("/finance/budgets/", {
      page_size: "200",
      ordering: "name",
    });

    const nestedResults = await Promise.all(
      budgetRes.results.map(async (budget) => {
        try {
          const lines = await api.get<PaginatedResponse<BudgetLineItemRead>>(
            `/finance/budgets/${budget.id}/line-items/`,
            { page_size: "200", ordering: "sort_order" }
          );
          return lines.results.map((line) => ({
            id: line.id,
            budgetName: budget.name,
            label: `${line.account_code} - ${line.account_name} (${budget.name})`,
          }));
        } catch {
          return [] as BudgetLineOption[];
        }
      })
    );

    return nestedResults.flat();
  } catch {
    return [];
  }
}

export async function fetchCostCodeOptions(): Promise<MasterDataEntry[]> {
  try {
    const res = await api.get<PaginatedResponse<MasterDataEntry>>("/settings/master-data/", {
      category: "cost_code",
      is_active: "true",
      page_size: "200",
      ordering: "label",
    });
    return res.results;
  } catch {
    return [];
  }
}
