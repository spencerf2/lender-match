import { useState } from "react";
import type { CriterionResult, FieldDefinition, LenderResult, ProgramResult } from "../../api/types";
import { fieldLabel, formatPercent } from "../../lib/format";

export function ResultsView({ results, fields }: { results: LenderResult[]; fields: FieldDefinition[] | null }) {
  const eligible = results.filter((r) => r.eligible);
  const ineligible = results.filter((r) => !r.eligible);

  if (results.length === 0) return <p className="text-sm text-gray-600">This run has no lender results.</p>;

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-base font-medium">Eligible lenders ({eligible.length})</h3>
        {eligible.length === 0 ? <p className="text-sm text-gray-600">No lender is eligible for this application.</p> : null}
        <div className="space-y-3">
          {eligible.map((lender) => (
            <EligibleLender key={lender.lender_name} lender={lender} fields={fields} />
          ))}
        </div>
      </section>
      {ineligible.length > 0 ? (
        <section>
          <h3 className="mb-2 text-base font-medium">Ineligible lenders ({ineligible.length})</h3>
          <div className="space-y-2">
            {ineligible.map((lender) => (
              <IneligibleLender key={lender.lender_name} lender={lender} fields={fields} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function EligibleLender({ lender, fields }: { lender: LenderResult; fields: FieldDefinition[] | null }) {
  return (
    <article data-testid="lender" className="rounded border border-green-300 bg-white p-4">
      <header className="mb-3 flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <span className="text-sm text-gray-500">#{lender.position ?? "—"}</span>
        <span className="text-lg font-semibold">{lender.lender_name}</span>
        <span className="text-sm">Fit score: {lender.fit_score}</span>
        <span className="text-sm">Best program: {lender.best_program?.program_name ?? "—"}</span>
        <span className="text-sm">Estimated rate: {formatPercent(lender.best_program?.estimated_rate_pct)}</span>
      </header>
      <Programs lender={lender} fields={fields} />
    </article>
  );
}

function IneligibleLender({ lender, fields }: { lender: LenderResult; fields: FieldDefinition[] | null }) {
  const [open, setOpen] = useState(false);
  return (
    <article data-testid="lender" className="rounded border border-gray-300 bg-white">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
          <span className="text-sm text-gray-500">#{lender.position ?? "—"}</span>
          <span className="font-semibold">{lender.lender_name}</span>
          <span className="text-sm">Fit score: {lender.fit_score}</span>
          <span className="ml-auto text-sm text-gray-500">{open ? "Hide details" : "Show details"}</span>
        </div>
        {lender.rejection_reasons.length > 0 ? (
          <ul className="mt-2 list-disc pl-5 text-sm text-red-800">
            {lender.rejection_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : null}
      </button>
      {open ? (
        <div className="border-t px-4 py-3">
          <Programs lender={lender} fields={fields} />
        </div>
      ) : null}
    </article>
  );
}

function Programs({ lender, fields }: { lender: LenderResult; fields: FieldDefinition[] | null }) {
  const bestName = lender.best_program?.program_name;
  const programs = [...lender.programs].sort(
    (a, b) => Number(b.program_name === bestName) - Number(a.program_name === bestName),
  );
  return (
    <div className="space-y-4">
      {programs.map((program) => (
        <ProgramBlock
          key={program.program_name}
          program={program}
          isBest={program.program_name === bestName}
          fields={fields}
        />
      ))}
    </div>
  );
}

function ProgramBlock({
  program,
  isBest,
  fields,
}: {
  program: ProgramResult;
  isBest: boolean;
  fields: FieldDefinition[] | null;
}) {
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span className="font-medium">Program: {program.program_name}</span>
        {isBest ? <span className="rounded bg-gray-900 px-1.5 py-0.5 text-xs text-white">Best program</span> : null}
        <span className={program.eligible ? "text-green-700" : "text-red-700"}>
          {program.eligible ? "Eligible" : "Ineligible"}
        </span>
        <span>Fit score: {program.fit_score}</span>
        <span>Hard failures: {program.hard_failures}</span>
        <span>Estimated rate: {formatPercent(program.estimated_rate_pct)}</span>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="border-b text-gray-600">
          <tr>
            <th className="py-1 pr-3">Field</th>
            <th className="py-1 pr-3">Explanation</th>
            <th className="py-1 pr-3">Hard/Soft</th>
            <th className="py-1">Result</th>
          </tr>
        </thead>
        <tbody>
          {program.criteria.map((criterion, i) => (
            <tr key={`${criterion.field}-${i}`} className="border-b align-top last:border-0">
              <td className="py-1 pr-3">{fieldLabel(fields, criterion.field)}</td>
              <td className="py-1 pr-3">{criterion.explanation}</td>
              <td className="py-1 pr-3">{criterion.hard ? "Hard" : "Soft"}</td>
              <td className="py-1 whitespace-nowrap">
                <CriterionMark criterion={criterion} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CriterionMark({ criterion }: { criterion: CriterionResult }) {
  if (criterion.passed === null) return <span className="text-gray-500">Not evaluated</span>;
  return criterion.passed ? (
    <span className="font-medium text-green-700">✓ Passed</span>
  ) : (
    <span className="font-medium text-red-700">✗ Failed</span>
  );
}
