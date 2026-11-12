import type { CaseDetail, Outcome } from "../types";
import { humanizePolicy, shortId } from "../format";
import ActionBar from "./ActionBar";
import CriterionCard from "./CriterionCard";

const OUTCOME: Record<Outcome, { cls: string; label: string }> = {
  approve: { cls: "appr", label: "Approve" },
  deny: { cls: "deny", label: "Deny" },
  request_info: { cls: "info", label: "Request info" },
};

function flagReason(detail: CaseDetail): string {
  const packet = detail.packet;
  if (!packet) return "Flagged for review.";
  if (packet.outcome === "deny") return "A denial requires clinician sign-off.";
  if (packet.confidence === "low") return "Flagged for review — the agent was not confident.";
  if (packet.criteria.some((c) => c.met === null))
    return "Flagged for review — a criterion could not be determined.";
  return "Flagged for review.";
}

interface Props {
  detail: CaseDetail;
  onReview: (decision: Outcome, note: string) => Promise<void>;
}

export default function CaseView({ detail, onReview }: Props) {
  const packet = detail.packet;
  if (!packet) {
    return (
      <div className="empty">
        <div>
          <div className="big">No decision yet</div>
          <div>The agent has not produced a decision for this case.</div>
        </div>
      </div>
    );
  }

  const outcome = OUTCOME[packet.outcome];
  return (
    <div className="sheet">
      <div className="eyebrow">
        <span>PRIOR AUTH</span>
        <span className="sep">·</span>
        <b>{shortId(detail.case_id)}</b>
      </div>

      <h1>{humanizePolicy(detail.policy_id)}</h1>
      <div className="submeta">
        Patient <span className="m">{detail.patient_ref}</span> &nbsp;·&nbsp; Policy{" "}
        <span className="m">{detail.policy_id}</span>
      </div>

      <div className="flag">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 1.5 14.5 13H1.5L8 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
          <path d="M8 6.2v3.1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          <circle cx="8" cy="11.2" r="0.85" fill="currentColor" />
        </svg>
        {flagReason(detail)}
      </div>

      <section className="reco">
        <div className="reco-top">
          <div className="verdict">
            <span className={`chip-big ${outcome.cls}`}>{outcome.label}</span>
            <span className="confidence">
              <b>{packet.confidence === "high" ? "High" : "Low"}</b> confidence
            </span>
          </div>
          <div className="reco-body">
            <div className="reco-label">Agent recommendation</div>
            <p>{packet.summary}</p>
          </div>
        </div>
      </section>

      <div className="section-head">
        <h2>Criteria &amp; evidence</h2>
        <span className="hint">Every verdict cites the policy it rests on.</span>
      </div>

      {packet.criteria.map((verdict, index) => (
        <CriterionCard key={index} index={index + 1} verdict={verdict} />
      ))}

      <ActionBar reviewed={detail.review_decision} onReview={onReview} />
    </div>
  );
}
