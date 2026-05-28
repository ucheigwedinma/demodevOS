import { toAmount } from "$lib/contracts";
import type {
  AllowanceListItem,
  BonusListItem,
  CompensationRecord,
  DeductionListItem,
  TaxRecordListItem,
} from "$lib/types";

export type PayrollProfileCalculationInput = {
  compensation: CompensationRecord | null;
  allowances: AllowanceListItem[];
  deductions: DeductionListItem[];
  bonuses: BonusListItem[];
  taxRecords: TaxRecordListItem[];
  includeNhf: boolean;
  includePendingBonus: boolean;
};

export type PayrollProfileCalculationResult = {
  baseSalary: number;
  recurringAllowances: number;
  approvedBonuses: number;
  pendingBonuses: number;
  grossPay: number;
  paye: number;
  pensionEmployee: number;
  pensionEmployer: number;
  nhf: number;
  loanRepayment: number;
  insurance: number;
  unionDues: number;
  otherDeductions: number;
  statutoryDeductions: number;
  voluntaryDeductions: number;
  totalDeductions: number;
  netPay: number;
  totalPackage: number;
};

function monthlyize(amount: number, frequency: string | null | undefined): number {
  switch (frequency) {
    case "annually":
      return amount / 12;
    case "quarterly":
      return amount / 3;
    case "one_time":
      return amount;
    default:
      return amount;
  }
}

function latestTaxRecord(records: TaxRecordListItem[]): TaxRecordListItem | null {
  if (!records.length) return null;
  return [...records].sort((left, right) => {
    const yearGap = Number(right.fiscal_year || 0) - Number(left.fiscal_year || 0);
    if (yearGap !== 0) return yearGap;
    return right.updated_at.localeCompare(left.updated_at);
  })[0];
}

export function calculatePayrollProfileTotals(
  input: PayrollProfileCalculationInput
): PayrollProfileCalculationResult {
  const baseSalary = toAmount(input.compensation?.base_salary);
  const recurringAllowances = input.allowances
    .filter((item) => item.is_active)
    .reduce((sum, item) => sum + monthlyize(toAmount(item.amount), item.frequency), 0);

  const approvedBonuses = input.bonuses
    .filter((item) => item.status === "approved" || item.status === "paid")
    .reduce((sum, item) => sum + monthlyize(toAmount(item.amount), "one_time"), 0);

  const pendingBonuses = input.bonuses
    .filter((item) => item.status === "pending")
    .reduce((sum, item) => sum + monthlyize(toAmount(item.amount), "one_time"), 0);

  const grossPay =
    baseSalary +
    recurringAllowances +
    approvedBonuses +
    (input.includePendingBonus ? pendingBonuses : 0);

  const deductionBuckets = {
    tax: 0,
    pension: 0,
    loan: 0,
    insurance: 0,
    union: 0,
    other: 0,
  };

  for (const item of input.deductions) {
    if (!item.is_active) continue;
    const monthlyAmount = monthlyize(toAmount(item.amount), item.frequency);
    if (item.deduction_type === "tax") deductionBuckets.tax += monthlyAmount;
    else if (item.deduction_type === "pension") deductionBuckets.pension += monthlyAmount;
    else if (item.deduction_type === "loan") deductionBuckets.loan += monthlyAmount;
    else if (item.deduction_type === "insurance") deductionBuckets.insurance += monthlyAmount;
    else if (item.deduction_type === "union") deductionBuckets.union += monthlyAmount;
    else deductionBuckets.other += monthlyAmount;
  }

  const suggestedPensionEmployee = baseSalary > 0 ? baseSalary * 0.08 : 0;
  const pensionEmployee = Math.max(deductionBuckets.pension, suggestedPensionEmployee);
  const pensionEmployer = baseSalary > 0 ? baseSalary * 0.1 : 0;

  const taxRecord = latestTaxRecord(input.taxRecords);
  const suggestedPaye = taxRecord ? toAmount(taxRecord.tax_amount) / 12 : grossPay * 0.06;
  const paye = Math.max(deductionBuckets.tax, suggestedPaye);

  const nhf = input.includeNhf && baseSalary > 0 ? baseSalary * 0.025 : 0;
  const statutoryDeductions = paye + pensionEmployee + nhf;
  const voluntaryDeductions =
    deductionBuckets.loan +
    deductionBuckets.insurance +
    deductionBuckets.union +
    deductionBuckets.other;
  const totalDeductions = statutoryDeductions + voluntaryDeductions;
  const totalPackage = grossPay + pensionEmployer;
  const netPay = Math.max(0, grossPay - totalDeductions);

  return {
    baseSalary,
    recurringAllowances,
    approvedBonuses,
    pendingBonuses,
    grossPay,
    paye,
    pensionEmployee,
    pensionEmployer,
    nhf,
    loanRepayment: deductionBuckets.loan,
    insurance: deductionBuckets.insurance,
    unionDues: deductionBuckets.union,
    otherDeductions: deductionBuckets.other,
    statutoryDeductions,
    voluntaryDeductions,
    totalDeductions,
    netPay,
    totalPackage,
  };
}
