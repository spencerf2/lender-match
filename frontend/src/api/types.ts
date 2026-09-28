/**
 * Hand-written to match the backend's OpenAPI schema (http://localhost:8000/openapi.json).
 * The API serializes Decimal fields as strings ("85000.00") and accepts numbers
 * or numeric strings on input, so decimals are typed as `Decimal` below.
 */

export type Decimal = string | number;

// ---- enums (backend/lender_match/enums.py) ----

export type LenderStatus = "draft" | "active" | "archived";
export type ApplicationStatus = "draft" | "submitted";
export type MatchRunStatus =
  | "queued"
  | "validating"
  | "deriving"
  | "matching"
  | "ranking"
  | "completed"
  | "failed"
  | "incomplete";
export type CriterionOperator =
  | "gte"
  | "lte"
  | "between"
  | "in"
  | "not_in"
  | "is_true"
  | "is_false"
  | "is_null"
  | "count_at_least";
export type PolicyNoteKind = "unmapped" | "informational";
export type JudgmentOutputType = "yes_no" | "choice";

// ---- application fields (GET /application-fields) ----

export type FieldType =
  | "integer"
  | "decimal"
  | "boolean"
  | "enum"
  | "probability"
  | "trade_lines";
export type FieldSource = "form" | "derived" | "judgment";
export type FieldFormat = "number" | "money" | "percent" | "years" | "text";

export interface FieldDefinition {
  key: string; // e.g. "guarantor.min_fico", "business.state"
  label: string;
  type: FieldType;
  source: FieldSource;
  nullable: boolean;
  required: boolean;
  null_passes: boolean;
  absent_text: string | null;
  values: string[] | null; // enum options; only for type "enum"
  format: FieldFormat;
  allowed_operators: CriterionOperator[];
}

// ---- applications (backend/lender_match/domain/application.py) ----

export interface BusinessDraft {
  legal_name?: string | null;
  industry?: string | null; // must be one of application field "business.industry" values
  state?: string | null; // must be one of application field "business.state" values
  founded_date?: string | null; // ISO date "YYYY-MM-DD"
  annual_revenue?: Decimal | null; // >= 0
  description?: string | null;
}

export interface GuarantorDraft {
  name?: string | null;
  ownership_pct?: Decimal | null; // 0..100
  fico?: number | null; // 300..850
  is_homeowner?: boolean;
  is_us_citizen?: boolean;
  bankruptcy_discharge_date?: string | null; // ISO date
  has_judgments?: boolean;
  has_foreclosures?: boolean;
  has_repossessions?: boolean;
}

export interface BusinessCreditDraft {
  paynet_score?: number | null; // 0..1000
}

export interface TradeLineDraft {
  creditor?: string | null;
  amount?: Decimal | null; // >= 0
  opened_on?: string | null; // ISO date
  closed_on?: string | null; // ISO date, not before opened_on
  status?: string | null;
}

export interface LoanRequestDraft {
  amount?: Decimal | null; // > 0
  term_months?: number | null; // > 0
  down_payment_amount?: Decimal; // >= 0, default 0
  equipment_type?: string | null; // one of application field "equipment.type" values
  equipment_description?: string | null;
  equipment_year?: number | null; // 1900..(current year + 1)
  equipment_mileage?: number | null; // >= 0
  is_private_party_sale?: boolean;
}

export interface ApplicationDraft {
  submitted_by?: string | null;
  business: BusinessDraft;
  guarantors: GuarantorDraft[];
  business_credit: BusinessCreditDraft;
  trade_lines: TradeLineDraft[];
  loan_request: LoanRequestDraft;
}

/** What the API returns. Every draft field is present (nulls filled in) plus computed fields. */
export interface Application {
  id: string;
  status: ApplicationStatus;
  created_at: string;
  updated_at: string;
  submitted_by: string | null;
  business: Required<BusinessDraft>;
  guarantors: Required<GuarantorDraft>[];
  business_credit: Required<BusinessCreditDraft>;
  trade_lines: Required<TradeLineDraft>[];
  loan_request: Required<LoanRequestDraft>;
  // computed by the backend
  has_personal_guarantor: boolean;
  min_fico: number | null;
  is_homeowner: boolean;
  is_us_citizen: boolean;
  has_judgments: boolean;
  has_foreclosures: boolean;
  has_repossessions: boolean;
  comparable_credit_ratio: Decimal | null;
  down_payment_pct: Decimal | null;
}

// ---- runs and results (backend/lender_match/domain/results.py) ----

export interface MatchRunRecord {
  id: string;
  application_id: string;
  status: MatchRunStatus;
  field_values: Record<string, unknown> | null;
  /** For status "incomplete": newline-separated list of missing required fields. For "failed": the error. */
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CriterionResult {
  field: string;
  operator: CriterionOperator;
  value: unknown;
  hard: boolean;
  weight: Decimal | null;
  actual_value: unknown;
  /** null when the criterion could not be evaluated (e.g. a judgment field with no answer yet). */
  passed: boolean | null;
  explanation: string;
}

export interface ProgramResult {
  program_name: string;
  rank: number | null;
  eligible: boolean;
  fit_score: number; // 0..100
  hard_failures: number;
  criteria: CriterionResult[];
  estimated_rate_pct: Decimal | null;
}

export interface LenderResult {
  lender_name: string;
  eligible: boolean;
  /** The best eligible program, or the program with the fewest hard failures when none is eligible. */
  best_program: ProgramResult | null;
  fit_score: number;
  /** Explanations of best_program's failed hard criteria when the lender is ineligible. */
  rejection_reasons: string[];
  programs: ProgramResult[];
  position: number | null;
}

// ---- lenders and policies (backend/lender_match/domain/policy.py) ----

export interface CountAtLeast {
  count: number; // >= 1
  min_amount: Decimal; // >= 0
  active_within_months: number; // >= 1
}

/**
 * Value shape depends on operator:
 *  gte, lte: number
 *  between: [number, number] (first <= second)
 *  in, not_in: non-empty string[]
 *  is_true, is_false, is_null: null
 *  count_at_least: CountAtLeast
 */
export type CriterionValue = number | [number, number] | string[] | CountAtLeast | null;

export interface CriterionDraft {
  field: string;
  operator: CriterionOperator;
  value?: CriterionValue;
  hard: boolean;
  /** Hard criteria take no weight (must be null). Soft criteria: > 0, defaults to 0.5. */
  weight?: Decimal | null;
  source_quote?: string | null;
  position?: number;
}

export interface Criterion extends CriterionDraft {
  id: string;
  value: CriterionValue;
  weight: Decimal | null;
  source_quote: string | null;
  position: number;
}

export interface RateBand {
  credit_grade?: string | null;
  min_amount: Decimal;
  max_amount?: Decimal | null; // null = no upper bound
  rate_pct: Decimal;
}

export interface ProgramDraft {
  name: string;
  rank?: number | null; // >= 1
  app_only_max_amount?: Decimal | null;
  notes?: string | null;
  criteria: CriterionDraft[];
  rates: RateBand[];
}

export interface Program extends Omit<ProgramDraft, "criteria"> {
  id: string;
  criteria: Criterion[];
}

export interface LenderContact {
  name?: string | null;
  title?: string | null;
  email?: string | null;
  phone?: string | null;
  role: string;
}

export interface PolicyNote {
  kind: PolicyNoteKind;
  text: string;
  /** A program name within the lender, or null for the whole lender. */
  program?: string | null;
}

export interface LenderDraft {
  name: string;
  source_effective_date?: string | null;
  contacts: LenderContact[];
  programs: ProgramDraft[]; // at least one
  notes: PolicyNote[];
}

export interface Lender extends Omit<LenderDraft, "programs"> {
  id: string;
  status: LenderStatus;
  created_at: string;
  updated_at: string;
  programs: Program[];
}

export interface PolicyCheck {
  problems: string[];
}

// ---- error shapes ----

/** FastAPI/Pydantic validation error (HTTP 422 on POST/PUT /applications). */
export interface ValidationErrorItem {
  type: string;
  loc: (string | number)[]; // e.g. ["body", "guarantors", 0, "fico"]
  msg: string;
  input?: unknown;
}
