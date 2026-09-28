import type { FieldDefinition, Program } from "../../api/types";
import { fieldLabel, formatMoney, formatPercent } from "../../lib/format";
import { Card } from "../ui";
import { AddCriterion, CriterionEditRow } from "./CriterionEditor";
import { describeValue, OPERATOR_LABELS } from "./criterionText";
import type { EditRow } from "./policyEdit";

const th = "py-2 pr-3 font-medium";

export interface ProgramEditing {
  rows: EditRow[];
  onChange: (criterionIndex: number, patch: Partial<EditRow>) => void;
  onRemove: (criterionIndex: number) => void;
  onAdd: (field: FieldDefinition) => void;
}

export function ProgramCard({
  program,
  fields,
  editing,
}: {
  program: Program;
  fields: FieldDefinition[] | null;
  editing: ProgramEditing | null;
}) {
  return (
    <Card title={`Program: ${program.name}`}>
      <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-gray-600">Rank</dt>
        <dd>{program.rank ?? "—"}</dd>
        <dt className="text-gray-600">App-only max amount</dt>
        <dd>{formatMoney(program.app_only_max_amount)}</dd>
        {program.notes ? (
          <>
            <dt className="text-gray-600">Notes</dt>
            <dd>{program.notes}</dd>
          </>
        ) : null}
      </dl>

      <h3 className="mb-1 font-medium">Criteria</h3>
      <table className="mb-4 w-full text-left text-sm">
        <thead className="border-b text-gray-600">
          <tr>
            <th className={th}>Field</th>
            <th className={th}>Operator</th>
            <th className={th}>Value</th>
            <th className={th}>Hard/Soft</th>
            <th className={th}>Weight</th>
            {editing ? <th className={th} /> : null}
          </tr>
        </thead>
        <tbody>
          {editing
            ? editing.rows.map((row, i) => (
                <CriterionEditRow
                  key={i}
                  row={row}
                  fields={fields}
                  onChange={(patch) => editing.onChange(i, patch)}
                  onRemove={() => editing.onRemove(i)}
                />
              ))
            : program.criteria.map((c) => (
                <tr key={c.id} className="border-b align-top last:border-0">
                  <td className="py-2 pr-3">
                    {fieldLabel(fields, c.field)}
                    {c.source_quote ? <div className="text-xs text-gray-500">“{c.source_quote}”</div> : null}
                  </td>
                  <td className="py-2 pr-3">{OPERATOR_LABELS[c.operator]}</td>
                  <td className="py-2 pr-3">{describeValue(c.operator, c.value)}</td>
                  <td className="py-2 pr-3">{c.hard ? "hard" : "soft"}</td>
                  <td className="py-2 pr-3">{c.hard ? "—" : String(c.weight ?? "—")}</td>
                </tr>
              ))}
        </tbody>
      </table>
      {editing ? <AddCriterion fields={fields} onAdd={editing.onAdd} /> : null}
      {!editing && program.criteria.length === 0 ? <p className="mb-4 text-sm text-gray-600">No criteria.</p> : null}

      <h3 className="mt-4 mb-1 font-medium">Rate bands</h3>
      {program.rates.length === 0 ? (
        <p className="text-sm text-gray-600">No rate bands.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="border-b text-gray-600">
            <tr>
              <th className={th}>Credit grade</th>
              <th className={th}>Min amount</th>
              <th className={th}>Max amount</th>
              <th className={th}>Rate</th>
            </tr>
          </thead>
          <tbody>
            {program.rates.map((band, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="py-2 pr-3">{band.credit_grade ?? "—"}</td>
                <td className="py-2 pr-3">{formatMoney(band.min_amount)}</td>
                <td className="py-2 pr-3">
                  {band.max_amount === null || band.max_amount === undefined ? "no upper bound" : formatMoney(band.max_amount)}
                </td>
                <td className="py-2 pr-3">{formatPercent(band.rate_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
