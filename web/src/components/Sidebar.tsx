import type { CaseSummary, Outcome } from "../types";
import { formatTime, humanizePolicy, shortId } from "../format";

const RECO_CLASS: Record<Outcome, string> = {
  approve: "appr",
  deny: "deny",
  request_info: "info",
};
const RECO_LABEL: Record<Outcome, string> = {
  approve: "Approve",
  deny: "Deny",
  request_info: "Needs info",
};

interface QueueItemProps {
  summary: CaseSummary;
  active: boolean;
  done: boolean;
  onSelect: (caseId: string) => void;
}

function QueueItem({ summary, active, done, onSelect }: QueueItemProps) {
  const reco = summary.recommended_outcome;
  return (
    <button
      className={`case${active ? " active" : ""}`}
      aria-current={active || undefined}
      onClick={() => onSelect(summary.case_id)}
    >
      <span className={`dot ${done ? "done" : "review"}`} />
      <span>
        <span className="proc">{humanizePolicy(summary.policy_id)}</span>
        <span className="line2">
          {reco ? (
            <span className={`rec ${RECO_CLASS[reco]}`}>{done ? "Reviewed" : RECO_LABEL[reco]}</span>
          ) : null}
          <span className="id">{shortId(summary.case_id)}</span>
          <span className="time">{formatTime(done ? (summary.reviewed_at ?? summary.created_at) : summary.created_at)}</span>
        </span>
      </span>
    </button>
  );
}

interface SidebarProps {
  pending: CaseSummary[];
  decided: CaseSummary[];
  selectedId: string | null;
  onSelect: (caseId: string) => void;
}

export default function Sidebar({ pending, decided, selectedId, onSelect }: SidebarProps) {
  return (
    <aside className="side">
      <div className="brand">
        <div className="mark">A</div>
        <div>
          <div className="name">Attest</div>
          <div className="sub">Prior-auth review</div>
        </div>
      </div>

      <nav className="queue" aria-label="Review queue">
        <div className="group-label">
          Needs your review <span className="count">{pending.length}</span>
        </div>
        {pending.length === 0 ? (
          <div className="queue-empty">Nothing waiting — nice work.</div>
        ) : (
          pending.map((summary) => (
            <QueueItem
              key={summary.case_id}
              summary={summary}
              active={summary.case_id === selectedId}
              done={false}
              onSelect={onSelect}
            />
          ))
        )}

        {decided.length > 0 ? <div className="group-label">Recently decided</div> : null}
        {decided.map((summary) => (
          <QueueItem
            key={summary.case_id}
            summary={summary}
            active={summary.case_id === selectedId}
            done
            onSelect={onSelect}
          />
        ))}
      </nav>

      <div className="reviewer">
        <div className="avatar">MR</div>
        <div>
          <div className="who">M. Restrepo, RN</div>
          <div className="role">Medical reviewer</div>
        </div>
      </div>
    </aside>
  );
}
