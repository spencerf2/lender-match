import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { LenderResult, MatchRunRecord, MatchRunStatus } from "../../api/types";
import { errorMessage } from "../../lib/useLoad";

const FINAL_STATUSES: MatchRunStatus[] = ["completed", "failed", "incomplete"];

export interface RunPollingState {
  run: MatchRunRecord | null;
  results: LenderResult[] | null;
  error: string | null;
}

/** Polls GET /runs/{id} every second until the run reaches a final status, then loads results for a completed run. */
export function useRunPolling(runId: string | null, onFinished?: () => void): RunPollingState {
  const [state, setState] = useState<RunPollingState>({ run: null, results: null, error: null });

  useEffect(() => {
    setState({ run: null, results: null, error: null });
    if (!runId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;
    let inFlight = false;

    const stop = () => {
      if (timer !== undefined) clearInterval(timer);
      timer = undefined;
    };

    const tick = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const run = await api.getRun(runId);
        if (cancelled) return;
        setState((s) => ({ ...s, run, error: null }));
        if (!FINAL_STATUSES.includes(run.status)) return;
        stop();
        if (run.status === "completed") {
          const results = await api.getResults(runId);
          if (cancelled) return;
          setState((s) => ({ ...s, results }));
        }
        onFinished?.();
      } catch (err) {
        if (cancelled) return;
        stop();
        setState((s) => ({ ...s, error: errorMessage(err) }));
      } finally {
        inFlight = false;
      }
    };

    void tick();
    timer = setInterval(() => void tick(), 1000);
    return () => {
      cancelled = true;
      stop();
    };
    // onFinished is a callback from the parent; re-running on its identity would restart polling.
  }, [runId]);

  return state;
}
