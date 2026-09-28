import type { ApplicationDraft, ValidationErrorItem } from "../../api/types";
import { toNumber } from "../../lib/format";

/** Client-side mirror of the API's required fields and value ranges.
 *  Keys are dotted paths into the draft, e.g. "guarantors.0.fico" or "loan_request.amount". */
export function validateDraft(draft: ApplicationDraft): Record<string, string> {
  const errors: Record<string, string> = {};
  const required = "Required.";

  const range = (key: string, value: unknown, min: number | null, max: number | null, opts: { integer?: boolean; exclusiveMin?: boolean } = {}) => {
    const n = toNumber(value as string | number | null | undefined);
    if (n === null) return;
    if (opts.integer && !Number.isInteger(n)) errors[key] = "Must be a whole number.";
    else if (min !== null && (opts.exclusiveMin ? n <= min : n < min))
      errors[key] = opts.exclusiveMin ? `Must be greater than ${min}.` : `Must be at least ${min}.`;
    else if (max !== null && n > max) errors[key] = `Must be at most ${max}.`;
  };

  const { business, guarantors, business_credit, trade_lines, loan_request } = draft;

  if (!business.state) errors["business.state"] = required;
  if (!business.industry) errors["business.industry"] = required;
  range("business.annual_revenue", business.annual_revenue, 0, null);

  if (!guarantors.some((g) => toNumber(g.fico) !== null)) {
    if (guarantors.length === 0) errors["guarantors"] = "At least one guarantor with a FICO score is required.";
    else errors["guarantors.0.fico"] = "At least one guarantor needs a FICO score.";
  }
  guarantors.forEach((g, i) => {
    range(`guarantors.${i}.fico`, g.fico, 300, 850, { integer: true });
    range(`guarantors.${i}.ownership_pct`, g.ownership_pct, 0, 100);
  });

  range("business_credit.paynet_score", business_credit.paynet_score, 0, 1000, { integer: true });

  trade_lines.forEach((t, i) => {
    range(`trade_lines.${i}.amount`, t.amount, 0, null);
    if (t.opened_on && t.closed_on && t.closed_on < t.opened_on)
      errors[`trade_lines.${i}.closed_on`] = "Closed date cannot be before the opened date.";
  });

  if (toNumber(loan_request.amount) === null) errors["loan_request.amount"] = required;
  else range("loan_request.amount", loan_request.amount, 0, null, { exclusiveMin: true });
  if (toNumber(loan_request.term_months) === null) errors["loan_request.term_months"] = required;
  else range("loan_request.term_months", loan_request.term_months, 0, null, { integer: true, exclusiveMin: true });
  if (!loan_request.equipment_type) errors["loan_request.equipment_type"] = required;
  range("loan_request.down_payment_amount", loan_request.down_payment_amount, 0, null);
  range("loan_request.equipment_year", loan_request.equipment_year, 1900, new Date().getFullYear() + 1, { integer: true });
  range("loan_request.equipment_mileage", loan_request.equipment_mileage, 0, null, { integer: true });

  return errors;
}

// Keys that correspond to a single form input; anything else (e.g. a whole trade line) goes to the banner.
const FIELD_KEY = new RegExp(
  "^(submitted_by" +
    "|business\\.(legal_name|industry|state|founded_date|annual_revenue|description)" +
    "|guarantors\\.\\d+\\.(name|ownership_pct|fico|is_homeowner|is_us_citizen|bankruptcy_discharge_date|has_judgments|has_foreclosures|has_repossessions)" +
    "|business_credit\\.paynet_score" +
    "|trade_lines\\.\\d+\\.(creditor|amount|opened_on|closed_on|status)" +
    "|loan_request\\.(amount|term_months|down_payment_amount|equipment_type|equipment_description|equipment_year|equipment_mileage|is_private_party_sale)" +
    ")$",
);

/** Maps a 422 body's `loc` (["body", "guarantors", 0, "fico"]) to the same dotted keys. Unmapped items come back separately. */
export function mapServerErrors(items: ValidationErrorItem[]): { fields: Record<string, string>; unmapped: string[] } {
  const fields: Record<string, string> = {};
  const unmapped: string[] = [];
  for (const item of items) {
    const path = item.loc[0] === "body" ? item.loc.slice(1) : item.loc;
    const key = path.join(".");
    if (FIELD_KEY.test(key)) fields[key] = item.msg;
    else unmapped.push(key ? `${key}: ${item.msg}` : item.msg);
  }
  return { fields, unmapped };
}
