import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../api/client";
import type { Lender } from "../api/types";
import { humanize } from "../lib/format";
import { errorMessage, useLoad } from "../lib/useLoad";
import { buttonClass, Card, ErrorBanner, Loading, PageTitle, secondaryButtonClass } from "../components/ui";
import { ProgramCard } from "../components/lenders/ProgramCard";
import {
  addCriterion,
  buildDraft,
  removeCriterion,
  setCriterion,
  startEdit,
  type PolicyEdit,
} from "../components/lenders/policyEdit";

function saveErrors(err: unknown): string[] {
  if (err instanceof ApiError) {
    if (err.problems?.length) return err.problems;
    if (err.validationErrors?.length) return err.validationErrors.map((e) => e.msg);
  }
  return [errorMessage(err)];
}

export function LenderDetailPage() {
  const { id = "" } = useParams();
  const loaded = useLoad(() => api.getLender(id), [id]);
  const { data: fields } = useLoad(() => api.applicationFields(), []);
  const [lender, setLender] = useState<Lender | null>(null);
  const [edit, setEdit] = useState<PolicyEdit | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setLender(loaded.data);
  }, [loaded.data]);

  if (loaded.loading && !lender) return <Loading what="Loading lender" />;
  if (loaded.error) return <ErrorBanner message={loaded.error} />;
  if (!lender) return null;

  const cancel = () => {
    setEdit(null);
    setProblems([]);
  };

  const save = async () => {
    if (!edit) return;
    setSaved(false);
    const built = buildDraft(edit);
    if (!built.ok) {
      setProblems(built.errors);
      return;
    }
    setSaving(true);
    setProblems([]);
    try {
      const check = await api.checkLender(built.draft);
      if (check.problems.length > 0) {
        setProblems(check.problems);
        return;
      }
      const updated = await api.replaceLender(lender.id, built.draft);
      setLender(updated);
      setEdit(null);
      setSaved(true);
    } catch (err) {
      setProblems(saveErrors(err));
    } finally {
      setSaving(false);
    }
  };

  const saveBar = (withProblems: boolean) => edit ? (
    <div className="mb-4">
      {withProblems && problems.length > 0 ? (
        <div role="alert" className="mb-2 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          <p className="font-medium">The policy was not saved:</p>
          <ul className="list-disc pl-5">
            {problems.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex gap-2">
        <button type="button" className={buttonClass} disabled={saving} onClick={() => void save()}>
          {saving ? "Saving…" : "Save policy"}
        </button>
        <button type="button" className={secondaryButtonClass} disabled={saving} onClick={cancel}>
          Cancel
        </button>
      </div>
    </div>
  ) : null;

  return (
    <div>
      <p className="mb-2 text-sm">
        <Link to="/lenders" className="text-blue-700 underline">
          ← Lenders
        </Link>
      </p>
      <PageTitle
        actions={
          edit ? null : (
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={() => {
                setSaved(false);
                setProblems([]);
                setEdit(startEdit(lender));
              }}
            >
              Edit criteria
            </button>
          )
        }
      >
        {lender.name} <span className="ml-2 rounded bg-gray-200 px-2 py-0.5 align-middle text-sm font-normal">{lender.status}</span>
      </PageTitle>
      {saved ? (
        <p role="status" className="mb-4 rounded border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-800">
          Saved.
        </p>
      ) : null}

      <Card title="Contacts">
        {lender.contacts.length === 0 ? (
          <p className="text-sm text-gray-600">No contacts.</p>
        ) : (
          <ul className="text-sm">
            {lender.contacts.map((c, i) => (
              <li key={i}>
                <span className="font-medium">{c.name ?? "—"}</span>
                {c.title ? `, ${c.title}` : ""} ({humanize(c.role)}){c.email ? ` · ${c.email}` : ""}
                {c.phone ? ` · ${c.phone}` : ""}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {saveBar(true)}

      {lender.programs.map((program, p) => (
        <ProgramCard
          key={program.id}
          program={program}
          fields={fields}
          editing={
            edit
              ? {
                  rows: edit.programs[p] ?? [],
                  onChange: (c, patch) => setEdit((e) => (e ? setCriterion(e, p, c, patch) : e)),
                  onRemove: (c) => setEdit((e) => (e ? removeCriterion(e, p, c) : e)),
                  onAdd: (field) => setEdit((e) => (e ? addCriterion(e, p, field) : e)),
                }
              : null
          }
        />
      ))}

      {saveBar(false)}

      <Card title="Policy notes">
        {lender.notes.length === 0 ? (
          <p className="text-sm text-gray-600">No policy notes.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {lender.notes.map((note, i) => (
              <li key={i}>
                <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs">{note.kind}</span>
                <span className="text-gray-600">{note.program ?? "whole lender"}:</span> {note.text}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
