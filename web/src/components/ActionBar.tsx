import { useState } from "react";

import type { Outcome } from "../types";

interface Props {
  reviewed: Outcome | null;
  onReview: (decision: Outcome, note: string) => Promise<void>;
}

const REVIEWED_LABEL: Record<Outcome, string> = {
  approve: "approved",
  deny: "denied",
  request_info: "sent back for information",
};

export default function ActionBar({ reviewed, onReview }: Props) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  if (reviewed) {
    return (
      <div className="actionbar">
        <span className="confidence">
          Reviewed — you <b>{REVIEWED_LABEL[reviewed]}</b> this case.
        </span>
      </div>
    );
  }

  const submit = async (decision: Outcome) => {
    setBusy(true);
    try {
      await onReview(decision, note.trim());
      setNote("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="actionbar">
      <div className="actions">
        <button className="btn primary" disabled={busy} onClick={() => submit("approve")}>
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
            <path
              d="M3 7.8l3 3 6-6.6"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Approve
        </button>
        <button className="btn ghost" disabled={busy} onClick={() => submit("request_info")}>
          Request info
        </button>
        <button className="btn danger" disabled={busy} onClick={() => submit("deny")}>
          Deny
        </button>
      </div>
      <input
        className="note-input"
        placeholder="Add a review note…"
        aria-label="Review note"
        value={note}
        disabled={busy}
        onChange={(event) => setNote(event.target.value)}
      />
    </div>
  );
}
