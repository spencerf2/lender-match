import type { ApplicationDraft } from "../../api/types";

/** Form state keeps every text, number and date input as a string; toDraft converts on submit. */

export interface GuarantorForm {
  name: string;
  ownership_pct: string;
  fico: string;
  is_homeowner: boolean;
  is_us_citizen: boolean;
  bankruptcy_discharge_date: string;
  has_judgments: boolean;
  has_foreclosures: boolean;
  has_repossessions: boolean;
}

export interface TradeLineForm {
  creditor: string;
  amount: string;
  opened_on: string;
  closed_on: string;
  status: string;
}

export interface ApplicationForm {
  submitted_by: string;
  business: {
    legal_name: string;
    industry: string;
    state: string;
    founded_date: string;
    annual_revenue: string;
    description: string;
  };
  guarantors: GuarantorForm[];
  business_credit: { paynet_score: string };
  trade_lines: TradeLineForm[];
  loan_request: {
    amount: string;
    term_months: string;
    down_payment_amount: string;
    equipment_type: string;
    equipment_description: string;
    equipment_year: string;
    equipment_mileage: string;
    is_private_party_sale: boolean;
  };
}

export const emptyGuarantor = (): GuarantorForm => ({
  name: "",
  ownership_pct: "",
  fico: "",
  is_homeowner: false,
  is_us_citizen: false,
  bankruptcy_discharge_date: "",
  has_judgments: false,
  has_foreclosures: false,
  has_repossessions: false,
});

export const emptyTradeLine = (): TradeLineForm => ({
  creditor: "",
  amount: "",
  opened_on: "",
  closed_on: "",
  status: "",
});

export const emptyForm = (): ApplicationForm => ({
  submitted_by: "",
  business: { legal_name: "", industry: "", state: "", founded_date: "", annual_revenue: "", description: "" },
  guarantors: [emptyGuarantor()],
  business_credit: { paynet_score: "" },
  trade_lines: [],
  loan_request: {
    amount: "",
    term_months: "",
    down_payment_amount: "",
    equipment_type: "",
    equipment_description: "",
    equipment_year: "",
    equipment_mileage: "",
    is_private_party_sale: false,
  },
});

const text = (v: string): string | null => (v.trim() === "" ? null : v.trim());
const num = (v: string): number | null => {
  if (v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

export function toDraft(form: ApplicationForm): ApplicationDraft {
  const b = form.business;
  const l = form.loan_request;
  return {
    submitted_by: text(form.submitted_by),
    business: {
      legal_name: text(b.legal_name),
      industry: text(b.industry),
      state: text(b.state),
      founded_date: text(b.founded_date),
      annual_revenue: num(b.annual_revenue),
      description: text(b.description),
    },
    guarantors: form.guarantors.map((g) => ({
      name: text(g.name),
      ownership_pct: num(g.ownership_pct),
      fico: num(g.fico),
      is_homeowner: g.is_homeowner,
      is_us_citizen: g.is_us_citizen,
      bankruptcy_discharge_date: text(g.bankruptcy_discharge_date),
      has_judgments: g.has_judgments,
      has_foreclosures: g.has_foreclosures,
      has_repossessions: g.has_repossessions,
    })),
    business_credit: { paynet_score: num(form.business_credit.paynet_score) },
    trade_lines: form.trade_lines.map((t) => ({
      creditor: text(t.creditor),
      amount: num(t.amount),
      opened_on: text(t.opened_on),
      closed_on: text(t.closed_on),
      status: text(t.status),
    })),
    loan_request: {
      amount: num(l.amount),
      term_months: num(l.term_months),
      // The API field is non-nullable with a default of 0, so an empty input sends 0.
      down_payment_amount: num(l.down_payment_amount) ?? 0,
      equipment_type: text(l.equipment_type),
      equipment_description: text(l.equipment_description),
      equipment_year: num(l.equipment_year),
      equipment_mileage: num(l.equipment_mileage),
      is_private_party_sale: l.is_private_party_sale,
    },
  };
}
