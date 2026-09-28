import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { CriterionResult, LenderResult } from "../../api/types";
import { ResultsView } from "./ResultsView";

function criterion(overrides: Partial<CriterionResult> = {}): CriterionResult {
  return {
    field: "guarantor.min_fico",
    operator: "gte",
    value: 680,
    hard: true,
    weight: null,
    actual_value: 720,
    passed: true,
    explanation: "Minimum FICO across guarantors must be at least 680. Applicant has 720.",
    ...overrides,
  };
}

function lender(name: string, position: number, eligible: boolean, overrides: Partial<LenderResult> = {}): LenderResult {
  const program = {
    program_name: `${name} Standard`,
    rank: null,
    eligible,
    fit_score: 80,
    hard_failures: eligible ? 0 : 1,
    criteria: [criterion()],
    estimated_rate_pct: eligible ? "8.250" : null,
  };
  return {
    lender_name: name,
    eligible,
    best_program: program,
    fit_score: 80,
    rejection_reasons: [],
    programs: [program],
    position,
    ...overrides,
  };
}

describe("ResultsView", () => {
  // Vitest globals are off, so Testing Library does not unmount between tests on its own.
  afterEach(cleanup);

  it("eligible lenders are listed before ineligible ones", () => {
    render(
      <ResultsView
        results={[lender("Ineligible Co", 2, false), lender("Eligible Co", 1, true)]}
        fields={null}
      />,
    );
    const names = screen.getAllByTestId("lender").map((el) => el.textContent ?? "");
    expect(names[0]).toContain("Eligible Co");
    expect(names[1]).toContain("Ineligible Co");
  });

  it("an ineligible lender shows its rejection reasons while collapsed", () => {
    render(
      <ResultsView
        results={[
          lender("Advantage+ Financing", 1, false, {
            rejection_reasons: ["Requested amount must be at most $75,000. Applicant has $85,000."],
          }),
        ]}
        fields={null}
      />,
    );
    expect(screen.getByRole("button", { expanded: false })).toBeInTheDocument();
    expect(screen.getByText("Requested amount must be at most $75,000. Applicant has $85,000.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("a criterion that could not be evaluated is shown as not evaluated", () => {
    const unanswered = criterion({
      field: "judgment.fad_medical",
      passed: null,
      explanation: "fad medical: not evaluated. no answer yet",
    });
    const eligible = lender("Falcon Equipment Finance", 1, true);
    eligible.programs[0]!.criteria = [unanswered];
    render(<ResultsView results={[eligible]} fields={null} />);
    expect(screen.getByText("Not evaluated")).toBeInTheDocument();
    expect(screen.queryByText(/Passed/)).not.toBeInTheDocument();
  });
});
