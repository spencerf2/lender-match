import { useState } from "react";
import { useNavigate } from "react-router";
import { api, ApiError } from "../../api/client";
import type { LenderDraft } from "../../api/types";
import { errorMessage } from "../../lib/useLoad";
import { buttonClass, Card, inputClass, labelClass, secondaryButtonClass } from "../ui";

function problemsFrom(err: unknown): string[] {
  if (err instanceof ApiError) {
    if (err.problems?.length) return err.problems;
    if (err.validationErrors?.length) {
      return err.validationErrors.map((e) => `${e.loc.slice(1).join(".")}: ${e.msg}`);
    }
  }
  return [errorMessage(err)];
}

/** Paste a LenderDraft as JSON, check its policy, then create the lender. */
export function NewLenderForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [problems, setProblems] = useState<string[]>([]);
  const [checkedOk, setCheckedOk] = useState(false);
  const [busy, setBusy] = useState(false);

  const parse = (): LenderDraft | null => {
    try {
      return JSON.parse(text) as LenderDraft;
    } catch (err) {
      setProblems([`Not valid JSON: ${errorMessage(err)}`]);
      return null;
    }
  };

  const run = async (action: "check" | "create") => {
    setProblems([]);
    setCheckedOk(false);
    const draft = parse();
    if (!draft) return;
    setBusy(true);
    try {
      if (action === "check") {
        const result = await api.checkLender(draft);
        setProblems(result.problems);
        setCheckedOk(result.problems.length === 0);
      } else {
        const lender = await api.createLender(draft);
        navigate(`/lenders/${lender.id}`);
      }
    } catch (err) {
      setProblems(problemsFrom(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Add lender">
      <label className={labelClass} htmlFor="lender-json">
        Lender policy as JSON (same shape as the seed files)
      </label>
      <textarea
        id="lender-json"
        className={`${inputClass} mt-1 h-64 font-mono text-xs`}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setCheckedOk(false);
        }}
      />
      {problems.length > 0 ? (
        <ul role="alert" className="mt-2 list-disc rounded border border-red-300 bg-red-50 py-2 pr-3 pl-8 text-sm text-red-800">
          {problems.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      ) : null}
      {checkedOk ? <p className="mt-2 text-sm text-green-800">The policy has no problems.</p> : null}
      <div className="mt-3 flex gap-2">
        <button type="button" className={secondaryButtonClass} disabled={busy} onClick={() => void run("check")}>
          Check
        </button>
        <button type="button" className={buttonClass} disabled={busy} onClick={() => void run("create")}>
          Create
        </button>
        <button type="button" className={secondaryButtonClass} disabled={busy} onClick={onClose}>
          Cancel
        </button>
      </div>
    </Card>
  );
}
