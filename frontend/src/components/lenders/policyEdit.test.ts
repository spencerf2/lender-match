import { describe, expect, it } from "vitest";
import type { Criterion, Lender } from "../../api/types";
import { buildDraft, criterionValueFor, emptyRaw, removeCriterion, setCriterion, startEdit, toDraft } from "./policyEdit";

function criterion(overrides: Partial<Criterion>): Criterion {
  return {
    id: "c",
    field: "guarantor.min_fico",
    operator: "gte",
    value: 680,
    hard: true,
    weight: null,
    source_quote: null,
    position: 0,
    ...overrides,
  };
}

const lender: Lender = {
  id: "l1",
  name: "Test Lender",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  source_effective_date: null,
  contacts: [],
  notes: [],
  programs: [
    {
      id: "p1",
      name: "A",
      rank: 1,
      app_only_max_amount: null,
      notes: null,
      rates: [],
      criteria: [
        criterion({ id: "c1" }),
        criterion({ id: "c2", field: "loan.amount", operator: "lte", value: 75000, hard: false, weight: "0.5", position: 1 }),
      ],
    },
    { id: "p2", name: "B", rank: 2, app_only_max_amount: null, notes: null, rates: [], criteria: [criterion({ id: "c3" })] },
  ],
};

describe("editing a lender policy", () => {
  it("the draft sent to the API carries no ids, status or timestamps", () => {
    const draft = toDraft(lender);
    expect(draft).not.toHaveProperty("id");
    expect(draft).not.toHaveProperty("status");
    expect(draft.programs[0]).not.toHaveProperty("id");
    expect(draft.programs[0]?.criteria[0]).not.toHaveProperty("id");
  });

  it("switching a criterion to hard clears its weight", () => {
    const edit = setCriterion(startEdit(lender), 0, 1, { hard: true });
    const built = buildDraft(edit);
    expect(built.ok && built.draft.programs[0]?.criteria[1]?.weight).toBeNull();
  });

  it("a between value with the numbers out of order is rejected before the API is called", () => {
    const result = criterionValueFor("between", { ...emptyRaw(), low: "700", high: "650" });
    expect(result.ok).toBe(false);
    const edit = setCriterion(startEdit(lender), 0, 0, { operator: "between", raw: { ...emptyRaw(), low: "700", high: "650" } });
    expect(buildDraft(edit).ok).toBe(false);
  });

  it("removing a criterion from a program leaves the other programs untouched", () => {
    const built = buildDraft(removeCriterion(startEdit(lender), 0, 0));
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    expect(built.draft.programs[0]?.criteria.map((c) => c.field)).toEqual(["loan.amount"]);
    expect(built.draft.programs[1]).toEqual(toDraft(lender).programs[1]);
  });
});
