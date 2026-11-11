"""Generate a synthetic payer policy PDF for local testing (no PHI).

The criteria intentionally match the `patient-001` fixture (knee MRI after a
failed course of physical therapy) so the agent can reach a cited decision.

Usage:
    python data/make_sample_policy.py            # -> data/policies/sample-policy.pdf
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

OUTPUT = Path("data/policies/sample-policy.pdf")

POLICY_TEXT = """\
PAYER MEDICAL POLICY — ADVANCED IMAGING
Policy ID: sample-policy
Subject: Magnetic Resonance Imaging (MRI) of the Knee

1. SCOPE
This policy defines the medical necessity criteria for non-emergent MRI of the
knee for members presenting with chronic knee pain.

2. CRITERIA FOR APPROVAL
MRI of the knee is considered medically necessary when ALL of the following
criteria are met:

  (a) The member has a documented diagnosis of a chronic knee condition, such as
      osteoarthritis, persisting for at least 6 weeks.

  (b) The member has completed and failed a minimum of 6 weeks of conservative
      therapy, including a supervised course of physical therapy, without
      sustained improvement in pain or function.

  (c) A current pain or functional assessment documents ongoing limitation
      (for example, a pain score of 4 or higher on a 0-10 scale).

3. REQUEST FOR MORE INFORMATION
If documentation of the conservative therapy trial or its outcome is missing,
the request should be returned for additional information rather than denied.

4. EXCLUSIONS
This policy does not apply to acute trauma, suspected septic arthritis, or
post-operative imaging, which follow separate pathways.
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(56, 56, page.rect.width - 56, page.rect.height - 56)
    page.insert_textbox(rect, POLICY_TEXT, fontsize=11, fontname="helv")
    doc.save(OUTPUT)
    doc.close()
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
