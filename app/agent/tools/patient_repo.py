"""Concrete `PatientRepository` reading synthetic FHIR bundles from disk.

Synthetic data only. In a real system this would be a FHIR server behind an
access-controlled boundary; here it reads hand-written or Synthea-generated
bundles from `data/patients/`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any


class FilePatientRepository:
    """Loads `data/patients/{patient_ref}.json` as the patient's FHIR data."""

    def __init__(self, root: Path | str = "data/patients") -> None:
        self._root = Path(root)

    async def get(self, patient_ref: str) -> dict[str, Any] | None:
        path = self._root / f"{patient_ref}.json"
        if not path.is_file():
            return None
        raw = await asyncio.to_thread(path.read_text, "utf-8")
        data: dict[str, Any] = json.loads(raw)
        return data
