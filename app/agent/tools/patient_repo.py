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

    async def list_refs(self) -> list[tuple[str, str]]:
        """Return `(patient_ref, display_name)` for every fixture, sorted by ref.

        `display_name` is the Patient resource's name when present, else the ref.
        Returns an empty list if the directory is missing.
        """
        if not self._root.is_dir():
            return []
        refs: list[tuple[str, str]] = []
        for path in sorted(self._root.glob("*.json")):
            ref = path.stem
            bundle = await self.get(ref)
            refs.append((ref, _display_name(bundle) or ref))
        return refs


def _display_name(bundle: dict[str, Any] | None) -> str | None:
    """Best-effort human name from a FHIR bundle's Patient resource."""
    if bundle is None:
        return None
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Patient":
            continue
        names = resource.get("name") or []
        if not names:
            return None
        name = names[0]
        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        full = f"{given} {family}".strip()
        return full or None
    return None
