"""Generate additional synthetic payer policy PDFs for testing (no PHI).

These are hand-written, realistic prior-authorization policies — advanced imaging,
a specialty biologic with step therapy, and durable medical equipment. Each is
paired with patient fixtures (`data/patients/`) so the agent can reach a cited
decision. Synthetic documents only.

Usage:
    python data/make_policies.py        # -> data/policies/<policy_id>.pdf (one each)
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

OUT_DIR = Path("data/policies")

POLICIES: dict[str, str] = {
    "lumbar-mri": """\
PAYER MEDICAL POLICY — ADVANCED IMAGING
Policy ID: lumbar-mri
Subject: Magnetic Resonance Imaging (MRI) of the Lumbar Spine

1. SCOPE
Medical necessity criteria for non-emergent MRI of the lumbar spine in members
with low back pain, with or without radicular symptoms.

2. CRITERIA FOR APPROVAL
MRI of the lumbar spine is considered medically necessary when ALL of the
following are met:

  (a) Low back pain, with or without radicular symptoms, persisting for at
      least 6 weeks.

  (b) The member has completed and failed at least 6 weeks of conservative
      management, including both analgesic/anti-inflammatory medication AND a
      supervised course of physical therapy, without sustained improvement.

  (c) A documented neurologic finding or functional limitation is present
      (for example, radiculopathy, a positive straight-leg-raise test, or a
      pain score of 4 or higher on a 0-10 scale).

  (d) No MRI of the same region of the lumbar spine has been performed within
      the prior 12 months.

3. RED-FLAG EXCEPTION
Suspected cauda equina syndrome, malignancy, infection, or significant acute
trauma follow a separate expedited pathway and are not subject to (a)-(d).

4. REQUEST FOR MORE INFORMATION
If the dates or outcome of the conservative therapy trial are not documented,
return the request for additional information rather than denying it.
""",
    "adalimumab-ra": """\
PAYER PHARMACY POLICY — SPECIALTY BIOLOGICS
Policy ID: adalimumab-ra
Subject: Adalimumab for Rheumatoid Arthritis

1. SCOPE
Medical necessity and step-therapy criteria for adalimumab (a TNF-alpha
inhibitor) in the treatment of rheumatoid arthritis (RA).

2. CRITERIA FOR APPROVAL
Adalimumab is considered medically necessary when ALL of the following are met:

  (a) A diagnosis of moderate-to-severe rheumatoid arthritis, documented by or
      in consultation with a rheumatologist.

  (b) Inadequate response to, or intolerance of, at least TWO conventional
      disease-modifying antirheumatic drugs (DMARDs) — for example methotrexate,
      leflunomide, or sulfasalazine — each tried for at least 3 months.

  (c) A negative tuberculosis screening (an interferon-gamma release assay or a
      tuberculin skin test) within the 12 months before initiation.

  (d) No active, serious infection at the time of the request.

3. REQUEST FOR MORE INFORMATION
If the tuberculosis screening result is not documented, return the request for
additional information rather than denying it.
""",
    "cpap-osa": """\
PAYER MEDICAL POLICY — DURABLE MEDICAL EQUIPMENT
Policy ID: cpap-osa
Subject: Continuous Positive Airway Pressure (CPAP) for Obstructive Sleep Apnea

1. SCOPE
Medical necessity criteria for a CPAP device in members with suspected or
diagnosed obstructive sleep apnea (OSA).

2. CRITERIA FOR APPROVAL
A CPAP device is considered medically necessary when ALL of the following are
met:

  (a) A diagnostic sleep study (in-laboratory polysomnography or a home sleep
      apnea test) documents an Apnea-Hypopnea Index (AHI) of 15 or more events
      per hour; OR an AHI of 5 to 14 together with documented symptoms or a
      relevant comorbidity.

  (b) Documented symptoms of OSA (for example excessive daytime sleepiness,
      loud habitual snoring, or witnessed apneas), or a qualifying comorbidity
      such as hypertension or cardiovascular disease.

  (c) The member has been counseled on CPAP use and agrees to adherence
      monitoring.

3. REQUEST FOR MORE INFORMATION
If the sleep-study report is not available, return the request for additional
information rather than denying it.
""",
}


def _write_pdf(policy_id: str, text: str) -> Path:
    path = OUT_DIR / f"{policy_id}.pdf"
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(56, 56, page.rect.width - 56, page.rect.height - 56)
    # insert_textbox returns remaining vertical space (>= 0) or a negative value if
    # the text overflowed the box. Keep each policy to one page; fail loudly if not.
    leftover = page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    if leftover < 0:
        raise ValueError(f"policy '{policy_id}' overflowed one page; shorten it")
    doc.save(path)
    doc.close()
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for policy_id, text in POLICIES.items():
        path = _write_pdf(policy_id, text)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
