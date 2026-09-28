import type {
  Application,
  ApplicationDraft,
  FieldDefinition,
  Lender,
  LenderDraft,
  LenderResult,
  MatchRunRecord,
  PolicyCheck,
  ValidationErrorItem,
} from "./types";

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/** Any non-2xx response. `validationErrors` is set for FastAPI 422 bodies,
 *  `problems` for the policy check's 422 body ({ problems: string[] }). */
export class ApiError extends Error {
  readonly status: number;
  readonly validationErrors: ValidationErrorItem[] | null;
  readonly problems: string[] | null;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.validationErrors = extractValidationErrors(body);
    this.problems = extractProblems(body);
  }
}

function extractValidationErrors(body: unknown): ValidationErrorItem[] | null {
  if (typeof body !== "object" || body === null) return null;
  const detail = (body as { detail?: unknown }).detail;
  return Array.isArray(detail) ? (detail as ValidationErrorItem[]) : null;
}

function extractProblems(body: unknown): string[] | null {
  if (typeof body !== "object" || body === null) return null;
  const problems = (body as { problems?: unknown }).problems;
  return Array.isArray(problems) ? (problems as string[]) : null;
}

function messageFor(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "The request failed validation.";
    const problems = (body as { problems?: unknown }).problems;
    if (Array.isArray(problems)) return "The policy has problems.";
  }
  return `Request failed with status ${status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      0,
      `No response from the API at ${API_URL}. It may be down, or it may have answered with a server error (check the API log).`,
      null,
    );
  }
  const text = await response.text();
  const body: unknown = text ? safeJson(text) : null;
  if (!response.ok) {
    throw new ApiError(response.status, messageFor(response.status, body), body);
  }
  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const api = {
  applicationFields: () => request<FieldDefinition[]>("/application-fields"),

  listApplications: () => request<Application[]>("/applications"),
  getApplication: (id: string) => request<Application>(`/applications/${id}`),
  createApplication: (draft: ApplicationDraft) =>
    request<Application>("/applications", { method: "POST", ...json(draft) }),
  updateApplication: (id: string, draft: ApplicationDraft) =>
    request<Application>(`/applications/${id}`, { method: "PUT", ...json(draft) }),
  deleteApplication: (id: string) =>
    request<void>(`/applications/${id}`, { method: "DELETE" }),

  startRun: (applicationId: string) =>
    request<MatchRunRecord>(`/applications/${applicationId}/runs`, { method: "POST" }),
  listRuns: (applicationId: string) =>
    request<MatchRunRecord[]>(`/applications/${applicationId}/runs`),
  getRun: (runId: string) => request<MatchRunRecord>(`/runs/${runId}`),
  getResults: (runId: string) => request<LenderResult[]>(`/runs/${runId}/results`),

  listLenders: () => request<Lender[]>("/lenders"),
  getLender: (id: string) => request<Lender>(`/lenders/${id}`),
  checkLender: (draft: LenderDraft) =>
    request<PolicyCheck>("/lenders/check", { method: "POST", ...json(draft) }),
  createLender: (draft: LenderDraft) =>
    request<Lender>("/lenders", { method: "POST", ...json(draft) }),
  replaceLender: (id: string, draft: LenderDraft) =>
    request<Lender>(`/lenders/${id}`, { method: "PUT", ...json(draft) }),
  deleteLender: (id: string) => request<void>(`/lenders/${id}`, { method: "DELETE" }),
};
