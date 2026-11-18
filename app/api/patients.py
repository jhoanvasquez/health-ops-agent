"""Patient catalog endpoint.

Lists the synthetic patients a case can be opened for, so the chat UI can offer
them as choices. Read-only; synthetic / non-PHI fixtures only.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent.tools.patient_repo import FilePatientRepository
from app.api.schemas import PatientSummary

router = APIRouter(prefix="/patients", tags=["patients"])


def get_patients() -> FilePatientRepository:
    """The synthetic patient repository. Overridden in tests."""
    return FilePatientRepository()


@router.get("", response_model=list[PatientSummary])
async def list_available_patients(
    patients: Annotated[FilePatientRepository, Depends(get_patients)],
) -> list[PatientSummary]:
    """List the synthetic patients a case can be opened for.

    Returns `{ patient_ref, display_name }` per fixture; an empty list if none exist.
    """
    return [
        PatientSummary(patient_ref=ref, display_name=name)
        for ref, name in await patients.list_refs()
    ]
