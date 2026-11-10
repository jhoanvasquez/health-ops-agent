# Data

**Synthetic data only. Never place real patient data (PHI) here.**

## Patients (`data/patients/`)

`get_patient` reads a patient as `data/patients/{patient_ref}.json` — a FHIR
resource or Bundle. Generate synthetic patients with
[Synthea](https://github.com/synthetichealth/synthea) and copy the bundles here,
or hand-write small fixtures for focused tests.

```bash
# example: generate synthetic patients with Synthea, then copy bundles in
./run_synthea -p 10
```

A patient reference is the file stem, e.g. `data/patients/patient-001.json` is
addressed as `patient-001`.

## Policies

Payer policy PDFs are ingested by `app/ingestion/policy_pdf.py`: parsed with page
references, chunked, embedded (Voyage, see ADR 003), and stored in `policy_chunks`.
Keep source PDFs out of version control.

## Ignored paths

`data/generated/` and `data/synthea/` are gitignored. Keep bulk generated output
there so it never lands in the repo.
