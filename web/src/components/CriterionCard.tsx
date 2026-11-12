import type { CriterionVerdict } from "../types";

function verdictOf(met: boolean | null): { cls: string; label: string; icon: JSX.Element } {
  if (met === true) {
    return {
      cls: "met",
      label: "Met",
      icon: (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M2.5 6.3l2.4 2.4L9.6 4"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    };
  }
  if (met === false) {
    return {
      cls: "notmet",
      label: "Not met",
      icon: (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M3.3 3.3l5.4 5.4M8.7 3.3l-5.4 5.4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      ),
    };
  }
  return {
    cls: "unknown",
    label: "Can't determine",
    icon: (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <path d="M3 6h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    ),
  };
}

interface Props {
  index: number;
  verdict: CriterionVerdict;
}

export default function CriterionCard({ index, verdict }: Props) {
  const v = verdictOf(verdict.met);
  return (
    <article className="crit">
      <div className="crit-head">
        <span className="num">{String(index).padStart(2, "0")}</span>
        <span className="claim">{verdict.criterion}</span>
        <span className={`verdict-chip ${v.cls}`}>
          {v.icon}
          {v.label}
        </span>
      </div>

      {verdict.evidence.length > 0 ? (
        verdict.evidence.map((citation, i) => (
          <div className="evidence" key={i}>
            <div className="q">&ldquo;{citation.excerpt}&rdquo;</div>
            <div className="cite">
              <span className="doc">{citation.doc_id}</span> · page {citation.page}
            </div>
          </div>
        ))
      ) : (
        <div className="evidence none">
          <div className="q">No supporting evidence was retrieved for this criterion.</div>
        </div>
      )}
    </article>
  );
}
