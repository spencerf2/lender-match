/**
 * Editing state for a lender's criteria, as plain functions so it can be tested without React.
 * Criterion values are kept as the raw text the user typed and turned into API values on save.
 */
import type {
  CountAtLeast,
  CriterionDraft,
  CriterionOperator,
  CriterionValue,
  FieldDefinition,
  Lender,
  LenderDraft,
} from "../../api/types";

export const DEFAULT_SOFT_WEIGHT = "0.5";

/** The text inputs behind one criterion value. Which ones matter depends on the operator. */
export interface RawValue {
  low: string; // gte, lte, and the first number of between
  high: string; // second number of between
  options: string[]; // in, not_in
  count: string; // count_at_least
  minAmount: string;
  activeWithinMonths: string;
}

export interface EditRow {
  field: string;
  operator: CriterionOperator;
  raw: RawValue;
  hard: boolean;
  weight: string; // ignored when hard
  source_quote: string | null;
}

/** The lender being edited: the untouched draft plus one list of editable rows per program. */
export interface PolicyEdit {
  base: LenderDraft;
  programs: EditRow[][];
}

export type ValueResult = { ok: true; value: CriterionValue } | { ok: false; error: string };

export function emptyRaw(): RawValue {
  return { low: "", high: "", options: [], count: "", minAmount: "", activeWithinMonths: "" };
}

/** The draft the API accepts for this lender: ids, status and timestamps removed. */
export function toDraft(lender: Lender): LenderDraft {
  return {
    name: lender.name,
    source_effective_date: lender.source_effective_date ?? null,
    contacts: lender.contacts,
    notes: lender.notes,
    programs: lender.programs.map((program) => ({
      name: program.name,
      rank: program.rank ?? null,
      app_only_max_amount: program.app_only_max_amount ?? null,
      notes: program.notes ?? null,
      rates: program.rates,
      criteria: program.criteria.map((criterion) => ({
        field: criterion.field,
        operator: criterion.operator,
        value: criterion.value,
        hard: criterion.hard,
        weight: criterion.weight,
        source_quote: criterion.source_quote,
        position: criterion.position,
      })),
    })),
  };
}

function rawFromValue(operator: CriterionOperator, value: CriterionValue | undefined): RawValue {
  const raw = emptyRaw();
  if (value === null || value === undefined) return raw;
  if ((operator === "gte" || operator === "lte") && !Array.isArray(value) && typeof value !== "object") {
    raw.low = String(value);
  } else if (operator === "between" && Array.isArray(value)) {
    raw.low = String(value[0] ?? "");
    raw.high = String(value[1] ?? "");
  } else if ((operator === "in" || operator === "not_in") && Array.isArray(value)) {
    raw.options = value.map(String);
  } else if (operator === "count_at_least" && typeof value === "object" && !Array.isArray(value)) {
    raw.count = String(value.count);
    raw.minAmount = String(value.min_amount);
    raw.activeWithinMonths = String(value.active_within_months);
  }
  return raw;
}

function toRow(criterion: CriterionDraft): EditRow {
  return {
    field: criterion.field,
    operator: criterion.operator,
    raw: rawFromValue(criterion.operator, criterion.value),
    hard: criterion.hard,
    weight:
      criterion.hard || criterion.weight === null || criterion.weight === undefined
        ? DEFAULT_SOFT_WEIGHT
        : String(criterion.weight),
    source_quote: criterion.source_quote ?? null,
  };
}

export function startEdit(lender: Lender): PolicyEdit {
  const base = toDraft(lender);
  return { base, programs: base.programs.map((program) => program.criteria.map(toRow)) };
}

function replaceProgram(edit: PolicyEdit, programIndex: number, rows: EditRow[]): PolicyEdit {
  return { ...edit, programs: edit.programs.map((r, i) => (i === programIndex ? rows : r)) };
}

/** Applies a change to one criterion. Changing the operator clears the value inputs. */
export function setCriterion(
  edit: PolicyEdit,
  programIndex: number,
  criterionIndex: number,
  patch: Partial<EditRow>,
): PolicyEdit {
  const rows = edit.programs[programIndex];
  if (!rows) return edit;
  return replaceProgram(
    edit,
    programIndex,
    rows.map((row, i) => {
      if (i !== criterionIndex) return row;
      const next = { ...row, ...patch };
      if (patch.operator !== undefined && patch.operator !== row.operator && patch.raw === undefined) {
        next.raw = emptyRaw();
      }
      if (patch.hard === false && row.hard) next.weight = DEFAULT_SOFT_WEIGHT;
      return next;
    }),
  );
}

/** Adds a hard criterion on `field`, using the field's first allowed operator. */
export function addCriterion(edit: PolicyEdit, programIndex: number, field: FieldDefinition): PolicyEdit {
  const rows = edit.programs[programIndex];
  if (!rows) return edit;
  const operator = field.allowed_operators[0] ?? "gte";
  const row: EditRow = {
    field: field.key,
    operator,
    raw: emptyRaw(),
    hard: true,
    weight: DEFAULT_SOFT_WEIGHT,
    source_quote: null,
  };
  return replaceProgram(edit, programIndex, [...rows, row]);
}

export function removeCriterion(edit: PolicyEdit, programIndex: number, criterionIndex: number): PolicyEdit {
  const rows = edit.programs[programIndex];
  if (!rows) return edit;
  return replaceProgram(
    edit,
    programIndex,
    rows.filter((_, i) => i !== criterionIndex),
  );
}

function parseNumber(text: string): number | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

function parseWholeNumber(text: string, min: number): number | null {
  const n = parseNumber(text);
  return n !== null && Number.isInteger(n) && n >= min ? n : null;
}

/** Turns the raw inputs into the value shape the API expects for `operator`. */
export function criterionValueFor(operator: CriterionOperator, raw: RawValue): ValueResult {
  switch (operator) {
    case "gte":
    case "lte": {
      const n = parseNumber(raw.low);
      return n === null ? { ok: false, error: "enter a number" } : { ok: true, value: n };
    }
    case "between": {
      const low = parseNumber(raw.low);
      const high = parseNumber(raw.high);
      if (low === null || high === null) return { ok: false, error: "enter both numbers" };
      if (low > high) return { ok: false, error: "the first number must not be greater than the second" };
      return { ok: true, value: [low, high] };
    }
    case "in":
    case "not_in":
      return raw.options.length === 0
        ? { ok: false, error: "pick at least one value" }
        : { ok: true, value: [...raw.options] };
    case "is_true":
    case "is_false":
    case "is_null":
      return { ok: true, value: null };
    case "count_at_least": {
      const count = parseWholeNumber(raw.count, 1);
      const minAmount = parseNumber(raw.minAmount);
      const months = parseWholeNumber(raw.activeWithinMonths, 1);
      if (count === null) return { ok: false, error: "count must be a whole number of at least 1" };
      if (minAmount === null || minAmount < 0) return { ok: false, error: "minimum amount must be 0 or more" };
      if (months === null) return { ok: false, error: "months must be a whole number of at least 1" };
      const value: CountAtLeast = { count, min_amount: minAmount, active_within_months: months };
      return { ok: true, value };
    }
  }
}

export type DraftResult = { ok: true; draft: LenderDraft } | { ok: false; errors: string[] };

/** Builds the full LenderDraft with the edited criteria, or lists what must be fixed first. */
export function buildDraft(edit: PolicyEdit): DraftResult {
  const errors: string[] = [];
  const programs = edit.base.programs.map((program, p) => {
    const rows = edit.programs[p] ?? [];
    const criteria: CriterionDraft[] = rows.map((row, c) => {
      const where = `${program.name}, criterion ${c + 1} (${row.field})`;
      const value = criterionValueFor(row.operator, row.raw);
      if (!value.ok) errors.push(`${where}: ${value.error}`);
      let weight: number | null = null;
      if (!row.hard) {
        weight = parseNumber(row.weight);
        if (weight === null || weight <= 0) errors.push(`${where}: weight must be a number greater than 0`);
      }
      return {
        field: row.field,
        operator: row.operator,
        value: value.ok ? value.value : null,
        hard: row.hard,
        weight,
        source_quote: row.source_quote,
        position: c,
      };
    });
    return { ...program, criteria };
  });
  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, draft: { ...edit.base, programs } };
}
