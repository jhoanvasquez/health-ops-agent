import { humanizePolicy } from "../format";
import type { ChatMessage, Outcome } from "../types";
import CriterionCard from "./CriterionCard";

const OUTCOME_CLASS: Record<Outcome, string> = {
  approve: "appr",
  deny: "deny",
  request_info: "info",
};
const OUTCOME_LABEL: Record<Outcome, string> = {
  approve: "Approve",
  deny: "Deny",
  request_info: "Request info",
};

interface Props {
  message: ChatMessage;
  onOpenReview: (caseId: string) => void;
}

export default function ChatMessageView({ message, onOpenReview }: Props) {
  if (message.kind === "user") {
    return (
      <div className="bubble-row right">
        <div className="bubble user">
          Open a case — <b>{humanizePolicy(message.policyId)}</b> for <b>{message.patientRef}</b>
        </div>
      </div>
    );
  }

  if (message.kind === "status") {
    return (
      <div className="bubble-row">
        <div className="bubble agent status">
          <span className="pulse" />
          {message.text}
        </div>
      </div>
    );
  }

  if (message.kind === "error") {
    return (
      <div className="bubble-row">
        <div className="bubble agent error">{message.text}</div>
      </div>
    );
  }

  const { packet, state, caseId } = message;
  return (
    <div className="bubble-row">
      <div className="bubble agent decision">
        {packet ? (
          <>
            <div className="decision-head">
              <span className={`chip-big ${OUTCOME_CLASS[packet.outcome]}`}>
                {OUTCOME_LABEL[packet.outcome]}
              </span>
              <span className="confidence">
                <b>{packet.confidence}</b> confidence
              </span>
            </div>
            <p className="decision-summary">{packet.summary}</p>
            <div className="decision-crits">
              {packet.criteria.map((verdict, i) => (
                <CriterionCard key={i} index={i + 1} verdict={verdict} />
              ))}
            </div>
          </>
        ) : (
          <p className="decision-summary">
            The case ended <b>{state}</b> without a decision packet.
          </p>
        )}

        {state === "needs_human" || state === "request_info" ? (
          <button className="btn ghost review-jump" onClick={() => onOpenReview(caseId)}>
            {state === "request_info" ? "Open in the queue →" : "Review this case →"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
