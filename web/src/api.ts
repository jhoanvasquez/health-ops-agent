import type { CaseDetail, CaseSummary, ReviewRequest } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return (await res.json()) as T;
}

export function listPendingReview(): Promise<CaseSummary[]> {
  return fetch(`${BASE}/cases?pending_review=true`).then((r) => asJson<CaseSummary[]>(r));
}

export function listRecentCases(): Promise<CaseSummary[]> {
  return fetch(`${BASE}/cases`).then((r) => asJson<CaseSummary[]>(r));
}

export function getCase(caseId: string): Promise<CaseDetail> {
  return fetch(`${BASE}/cases/${caseId}`).then((r) => asJson<CaseDetail>(r));
}

export function submitReview(caseId: string, body: ReviewRequest): Promise<CaseDetail> {
  return fetch(`${BASE}/cases/${caseId}/review`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => asJson<CaseDetail>(r));
}
