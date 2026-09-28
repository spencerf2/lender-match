import { describe, expect, it } from "vitest";
import { emptyForm, toDraft } from "./formState";
import type { ApplicationForm } from "./formState";
import { mapServerErrors, validateDraft } from "./validate";

function completeForm(): ApplicationForm {
  const form = emptyForm();
  form.business.state = "TX";
  form.business.industry = "trucking";
  form.guarantors[0]!.fico = "720";
  form.loan_request.amount = "85000";
  form.loan_request.term_months = "48";
  form.loan_request.equipment_type = "class_8_truck";
  return form;
}

describe("validateDraft", () => {
  it("a draft with every required field filled in has no errors", () => {
    expect(validateDraft(toDraft(completeForm()))).toEqual({});
  });

  it("a draft missing the state is incomplete", () => {
    const form = completeForm();
    form.business.state = "";
    expect(validateDraft(toDraft(form))).toEqual({ "business.state": "Required." });
  });

  it("a fico below 300 is rejected", () => {
    const form = completeForm();
    form.guarantors[0]!.fico = "250";
    expect(validateDraft(toDraft(form))["guarantors.0.fico"]).toMatch(/at least 300/);
  });

  it("a trade line closed before it was opened is rejected", () => {
    const form = completeForm();
    form.trade_lines.push({ creditor: "", amount: "1000", opened_on: "2024-05-01", closed_on: "2024-01-01", status: "" });
    expect(validateDraft(toDraft(form))["trade_lines.0.closed_on"]).toBeDefined();
  });
});

describe("mapServerErrors", () => {
  it("an API error on a guarantor's fico lands on that guarantor's fico input", () => {
    const { fields, unmapped } = mapServerErrors([
      { type: "greater_than_equal", loc: ["body", "guarantors", 0, "fico"], msg: "Input should be greater than or equal to 300" },
      { type: "value_error", loc: ["body", "trade_lines", 0], msg: "closed_on must not be before opened_on" },
    ]);
    expect(fields).toEqual({ "guarantors.0.fico": "Input should be greater than or equal to 300" });
    expect(unmapped).toHaveLength(1);
  });

  it("an API error on a path that is not a form input goes to the banner instead of vanishing", () => {
    const { fields, unmapped } = mapServerErrors([
      { type: "extra_forbidden", loc: ["body", "business_credit", "trade_lines"], msg: "Extra inputs are not permitted" },
    ]);
    expect(fields).toEqual({});
    expect(unmapped).toEqual(["business_credit.trade_lines: Extra inputs are not permitted"]);
  });
});
