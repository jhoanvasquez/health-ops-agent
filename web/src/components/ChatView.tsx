import { useCallback, useEffect, useRef, useState } from "react";

import { createCase, getCase, listPatients, listPolicies } from "../api";
import type { CaseDetail, CaseState, ChatMessage, Patient, Policy } from "../types";
import ChatComposer from "./ChatComposer";
import ChatMessageView from "./ChatMessage";

const TERMINAL: ReadonlySet<CaseState> = new Set<CaseState>([
  "decided",
  "needs_human",
  "request_info",
  "failed",
]);
const POLL_MS = 1500;
const POLL_CAP_MS = 60_000; // free-tier services can take ~30–50s to wake

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function pollUntilTerminal(caseId: string): Promise<CaseDetail | null> {
  const start = Date.now();
  while (Date.now() - start < POLL_CAP_MS) {
    const detail = await getCase(caseId);
    if (TERMINAL.has(detail.state)) return detail;
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }
  return null;
}

interface Props {
  onOpenReview: (caseId: string) => void;
}

export default function ChatView({ onOpenReview }: Props) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    Promise.all([listPolicies(), listPatients()])
      .then(([pol, pat]) => {
        setPolicies(pol);
        setPatients(pat);
      })
      .catch((e: unknown) => setLoadError(String(e)));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const push = useCallback((m: ChatMessage) => setMessages((prev) => [...prev, m]), []);
  const replaceLast = useCallback(
    (m: ChatMessage) => setMessages((prev) => [...prev.slice(0, -1), m]),
    [],
  );

  const onOpen = useCallback(
    async (policyId: string, patientRef: string) => {
      setBusy(true);
      push({ id: newId(), kind: "user", policyId, patientRef });
      push({ id: newId(), kind: "status", text: "Opening the case and handing it to the agent…" });
      try {
        const created = await createCase({
          idempotency_key: `chat-${newId()}`,
          policy_id: policyId,
          patient_ref: patientRef,
        });
        replaceLast({
          id: newId(),
          kind: "status",
          text: "The agent is evaluating the policy against the patient…",
        });
        const detail = await pollUntilTerminal(created.case_id);
        if (detail === null) {
          replaceLast({
            id: newId(),
            kind: "error",
            text: "Still processing — the free-tier service may be waking up. Check the review queue in a moment.",
          });
        } else {
          replaceLast({
            id: newId(),
            kind: "decision",
            caseId: detail.case_id,
            state: detail.state,
            packet: detail.packet,
          });
        }
      } catch (e: unknown) {
        replaceLast({ id: newId(), kind: "error", text: `Could not open the case: ${String(e)}` });
      } finally {
        setBusy(false);
      }
    },
    [push, replaceLast],
  );

  return (
    <div className="chat">
      <div className="chat-log">
        {messages.length === 0 ? (
          <div className="chat-hello">
            <div className="big">Open a prior-auth case</div>
            <p>
              Pick a policy and a patient. The agent evaluates each criterion and drafts a
              decision — every claim backed by a cited policy passage.
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <ChatMessageView key={m.id} message={m} onOpenReview={onOpenReview} />
          ))
        )}
        <div ref={endRef} />
      </div>

      {loadError ? <div className="chat-loaderr">Couldn&rsquo;t load options: {loadError}</div> : null}

      <ChatComposer policies={policies} patients={patients} disabled={busy} onOpen={onOpen} />
    </div>
  );
}
