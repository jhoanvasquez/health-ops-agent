import { useState } from "react";

import { humanizePolicy } from "../format";
import type { Patient, Policy } from "../types";

interface Props {
  policies: Policy[];
  patients: Patient[];
  disabled: boolean;
  onOpen: (policyId: string, patientRef: string) => void;
}

export default function ChatComposer({ policies, patients, disabled, onOpen }: Props) {
  const [policyId, setPolicyId] = useState("");
  const [patientRef, setPatientRef] = useState("");
  const ready = policyId !== "" && patientRef !== "" && !disabled;

  return (
    <form
      className="chat-composer"
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) onOpen(policyId, patientRef);
      }}
    >
      <select
        className="chat-select"
        value={policyId}
        onChange={(e) => setPolicyId(e.target.value)}
        aria-label="Policy"
      >
        <option value="">Select a policy…</option>
        {policies.map((p) => (
          <option key={p.policy_id} value={p.policy_id}>
            {humanizePolicy(p.policy_id)} · {p.chunks} chunks
          </option>
        ))}
      </select>

      <select
        className="chat-select"
        value={patientRef}
        onChange={(e) => setPatientRef(e.target.value)}
        aria-label="Patient"
      >
        <option value="">Select a patient…</option>
        {patients.map((p) => (
          <option key={p.patient_ref} value={p.patient_ref}>
            {p.display_name} · {p.patient_ref}
          </option>
        ))}
      </select>

      <button className="btn primary" type="submit" disabled={!ready}>
        Open case
      </button>
    </form>
  );
}
