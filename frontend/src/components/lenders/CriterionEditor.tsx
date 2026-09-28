import { useState } from "react";
import type { CriterionOperator, FieldDefinition } from "../../api/types";
import { capitalize, fieldLabel } from "../../lib/format";
import { inputClass, secondaryButtonClass } from "../ui";
import { OPERATOR_LABELS } from "./criterionText";
import type { EditRow, RawValue } from "./policyEdit";

const smallInput = `${inputClass} max-w-28`;

function ValueInputs({
  row,
  field,
  onChange,
}: {
  row: EditRow;
  field: FieldDefinition | undefined;
  onChange: (raw: RawValue) => void;
}) {
  const { raw, operator } = row;
  const set = (patch: Partial<RawValue>) => onChange({ ...raw, ...patch });

  if (operator === "gte" || operator === "lte") {
    return (
      <input aria-label="Value" className={smallInput} inputMode="decimal" value={raw.low} onChange={(e) => set({ low: e.target.value })} />
    );
  }
  if (operator === "between") {
    return (
      <div className="flex items-center gap-1">
        <input aria-label="From" className={smallInput} inputMode="decimal" value={raw.low} onChange={(e) => set({ low: e.target.value })} />
        <span>to</span>
        <input aria-label="To" className={smallInput} inputMode="decimal" value={raw.high} onChange={(e) => set({ high: e.target.value })} />
      </div>
    );
  }
  if (operator === "in" || operator === "not_in") {
    const options = field?.values ?? [];
    const toggle = (option: string, checked: boolean) =>
      set({ options: checked ? [...raw.options, option] : raw.options.filter((o) => o !== option) });
    return (
      <div className="max-h-40 overflow-y-auto rounded border border-gray-200 p-1">
        {options.map((option) => (
          <label key={option} className="flex items-center gap-1 text-xs">
            <input type="checkbox" checked={raw.options.includes(option)} onChange={(e) => toggle(option, e.target.checked)} />
            {option}
          </label>
        ))}
      </div>
    );
  }
  if (operator === "count_at_least") {
    return (
      <div className="flex flex-col gap-1 text-xs">
        <label>
          Count <input className={smallInput} inputMode="numeric" value={raw.count} onChange={(e) => set({ count: e.target.value })} />
        </label>
        <label>
          Min amount ($) <input className={smallInput} inputMode="decimal" value={raw.minAmount} onChange={(e) => set({ minAmount: e.target.value })} />
        </label>
        <label>
          Active within (months){" "}
          <input className={smallInput} inputMode="numeric" value={raw.activeWithinMonths} onChange={(e) => set({ activeWithinMonths: e.target.value })} />
        </label>
      </div>
    );
  }
  return <span className="text-gray-500">—</span>;
}

export function CriterionEditRow({
  row,
  fields,
  onChange,
  onRemove,
}: {
  row: EditRow;
  fields: FieldDefinition[] | null;
  onChange: (patch: Partial<EditRow>) => void;
  onRemove: () => void;
}) {
  const field = fields?.find((f) => f.key === row.field);
  const operators: CriterionOperator[] = field?.allowed_operators ?? [row.operator];
  return (
    <tr className="border-b align-top last:border-0">
      <td className="py-2 pr-3">
        {fieldLabel(fields, row.field)}
        {row.source_quote ? <div className="text-xs text-gray-500">“{row.source_quote}”</div> : null}
      </td>
      <td className="py-2 pr-3">
        <select
          aria-label="Operator"
          className={inputClass}
          value={row.operator}
          onChange={(e) => onChange({ operator: e.target.value as CriterionOperator })}
        >
          {operators.map((op) => (
            <option key={op} value={op}>
              {OPERATOR_LABELS[op]}
            </option>
          ))}
        </select>
      </td>
      <td className="py-2 pr-3">
        <ValueInputs row={row} field={field} onChange={(raw) => onChange({ raw })} />
      </td>
      <td className="py-2 pr-3">
        <select
          aria-label="Hard or soft"
          className={inputClass}
          value={row.hard ? "hard" : "soft"}
          onChange={(e) => onChange({ hard: e.target.value === "hard" })}
        >
          <option value="hard">hard</option>
          <option value="soft">soft</option>
        </select>
      </td>
      <td className="py-2 pr-3">
        <input
          aria-label="Weight"
          className={smallInput}
          inputMode="decimal"
          disabled={row.hard}
          value={row.hard ? "" : row.weight}
          onChange={(e) => onChange({ weight: e.target.value })}
        />
      </td>
      <td className="py-2">
        <button type="button" className={secondaryButtonClass} onClick={onRemove}>
          Remove
        </button>
      </td>
    </tr>
  );
}

/** Picks an application field for a new criterion. */
export function AddCriterion({
  fields,
  onAdd,
}: {
  fields: FieldDefinition[] | null;
  onAdd: (field: FieldDefinition) => void;
}) {
  const [key, setKey] = useState("");
  const sorted = [...(fields ?? [])].sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
  const chosen = sorted.find((f) => f.key === key);
  return (
    <div className="mt-2 flex items-center gap-2">
      <select aria-label="Application field" className={`${inputClass} max-w-xs`} value={key} onChange={(e) => setKey(e.target.value)}>
        <option value="">Choose an application field…</option>
        {sorted.map((f) => (
          <option key={f.key} value={f.key}>
            {capitalize(f.label)}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={secondaryButtonClass}
        disabled={!chosen}
        onClick={() => {
          if (chosen) {
            onAdd(chosen);
            setKey("");
          }
        }}
      >
        Add criterion
      </button>
    </div>
  );
}
