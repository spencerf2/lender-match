import type { CriterionOperator, CriterionValue } from "../../api/types";
import { formatMoney } from "../../lib/format";

export const OPERATOR_LABELS: Record<CriterionOperator, string> = {
  gte: "at least",
  lte: "at most",
  between: "between",
  in: "one of",
  not_in: "not one of",
  is_true: "is true",
  is_false: "is false",
  is_null: "is empty",
  count_at_least: "count at least",
};

export function describeValue(operator: CriterionOperator, value: CriterionValue): string {
  if (value === null || value === undefined) return "—";
  if (operator === "between" && Array.isArray(value)) return `${String(value[0])} to ${String(value[1])}`;
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") {
    return `count ${value.count} of at least ${formatMoney(value.min_amount)} active within ${value.active_within_months} months`;
  }
  return String(value);
}
