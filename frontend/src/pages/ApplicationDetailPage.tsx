import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api/client";
import type { MatchRunRecord } from "../api/types";
import { ApplicationSummary } from "../components/applications/ApplicationSummary";
import { ResultsView } from "../components/results/ResultsView";
import { useRunPolling } from "../components/results/useRunPolling";
import { Card, ErrorBanner, Loading, PageTitle, buttonClass } from "../components/ui";
import { formatDate, humanize } from "../lib/format";
import { errorMessage, useLoad } from "../lib/useLoad";

const newestFirst = (runs: MatchRunRecord[]) => [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at));

export function ApplicationDetailPage() {
  const { id = "" } = useParams();
  const application = useLoad(() => api.getApplication(id), [id]);
  const runs = useLoad(() => api.listRuns(id), [id]);
  const fields = useLoad(() => api.applicationFields(), []);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const polling = useRunPolling(selectedRunId, runs.reload);

  // On first load, show the most recent run if there is one.
  useEffect(() => {
    if (selectedRunId === null && runs.data && runs.data.length > 0) {
      setSelectedRunId(newestFirst(runs.data)[0]?.id ?? null);
    }
  }, [runs.data, selectedRunId]);

  async function startRun() {
    setStarting(true);
    setStartError(null);
    try {
      const run = await api.startRun(id);
      setSelectedRunId(run.id);
      runs.reload();
    } catch (err) {
      setStartError(errorMessage(err));
    } finally {
      setStarting(false);
    }
  }

  if (application.loading) return <Loading what="Loading application" />;
  if (application.error || !application.data)
    return <ErrorBanner message={application.error ?? "Application not found."} />;

  const app = application.data;
  const run = polling.run;

  return (
    <div>
      <p className="mb-2 text-sm">
        <Link to="/applications" className="text-blue-700 underline">
          ← Applications
        </Link>
      </p>
      <PageTitle
        actions={
          <button type="button" className={buttonClass} onClick={startRun} disabled={starting}>
            {starting ? "Starting run…" : "Run matching"}
          </button>
        }
      >
        {app.business.legal_name ?? "Untitled"}
      </PageTitle>
      <p className="mb-4 text-sm text-gray-600">
        Created {formatDate(app.created_at)}
        {app.submitted_by ? ` by ${app.submitted_by}` : ""}
      </p>
      <ErrorBanner message={startError} />

      <Card title="Runs">
        <ErrorBanner message={runs.error} />
        {runs.loading && !runs.data ? <Loading what="Loading runs" /> : null}
        {runs.data && runs.data.length === 0 ? (
          <p className="text-sm text-gray-600">No runs yet. Use "Run matching" to match this application against lenders.</p>
        ) : null}
        {runs.data && runs.data.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-600">
              <tr>
                <th className="py-1 pr-3">Created</th>
                <th className="py-1 pr-3">Status</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {newestFirst(runs.data).map((r) => {
                const selected = r.id === selectedRunId;
                return (
                  <tr key={r.id} className={`border-b last:border-0 ${selected ? "bg-gray-100" : ""}`}>
                    <td className="py-1 pr-3">{formatDate(r.created_at)}</td>
                    <td className="py-1 pr-3">{humanize(r.status)}</td>
                    <td className="py-1">
                      {selected ? (
                        <span className="text-gray-500">Showing</span>
                      ) : (
                        <button type="button" className="text-blue-700 underline" onClick={() => setSelectedRunId(r.id)}>
                          Show results
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </Card>

      {selectedRunId ? (
        <Card title="Results">
          <ErrorBanner message={polling.error} />
          {!run && !polling.error ? <Loading what="Loading run" /> : null}
          {run && run.status !== "completed" && run.status !== "failed" && run.status !== "incomplete" ? (
            <p role="status" className="text-sm text-gray-700">
              Run status: {humanize(run.status)}…
            </p>
          ) : null}
          {run?.status === "incomplete" ? (
            <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <p>This application needs these fields before it can be matched:</p>
              <ul className="mt-1 list-disc pl-5">
                {(run.error ?? "")
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .map((line) => (
                    <li key={line}>{line}</li>
                  ))}
              </ul>
            </div>
          ) : null}
          {run?.status === "failed" ? <ErrorBanner message={`The run failed: ${run.error ?? "no error text"}`} /> : null}
          {run?.status === "completed" && !polling.results && !polling.error ? <Loading what="Loading results" /> : null}
          {run?.status === "completed" && polling.results ? (
            <ResultsView results={polling.results} fields={fields.data} />
          ) : null}
        </Card>
      ) : null}

      <ApplicationSummary application={app} />
    </div>
  );
}

