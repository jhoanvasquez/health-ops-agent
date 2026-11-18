import type { CaseCreated, CaseDetail, CaseSummary, Patient, Policy, ReviewRequest } from "./types";

// Strip trailing slashes so a VITE_API_URL like "https://host/" never yields "//cases".
const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

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

export function listPolicies(): Promise<Policy[]> {
  return fetch(`${BASE}/policies`).then((r) => asJson<Policy[]>(r));
}

export function listPatients(): Promise<Patient[]> {
  return fetch(`${BASE}/patients`).then((r) => asJson<Patient[]>(r));
}

export function createCase(body: {
  idempotency_key: string;
  policy_id: string;
  patient_ref: string;
}): Promise<CaseCreated> {
  return fetch(`${BASE}/cases`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => asJson<CaseCreated>(r));
}
