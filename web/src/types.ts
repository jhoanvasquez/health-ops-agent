export type Outcome = "approve" | "deny" | "request_info";
export type Confidence = "high" | "low";
export type CaseState =
  | "received"
  | "processing"
  | "needs_human"
  | "request_info"
  | "decided"
  | "failed";

export interface Citation {
  doc_id: string;
  page: number;
  excerpt: string;
}

export interface CriterionVerdict {
  criterion: string;
  met: boolean | null;
  evidence: Citation[];
}

export interface DecisionPacket {
  outcome: Outcome;
  confidence: Confidence;
  criteria: CriterionVerdict[];
  summary: string;
}

export interface CaseSummary {
  case_id: string;
  policy_id: string;
  patient_ref: string;
  state: CaseState;
  recommended_outcome: Outcome | null;
  recommended_confidence: Confidence | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface CaseDetail {
  case_id: string;
  state: CaseState;
  packet: DecisionPacket | null;
  review_decision: Outcome | null;
  review_note: string | null;
  reviewed_at: string | null;
}

export interface ReviewRequest {
  decision: Outcome;
  note: string;
}
