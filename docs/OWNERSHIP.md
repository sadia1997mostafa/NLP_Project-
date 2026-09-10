# NagorikSheba AI Repository Ownership

This repository is developed in parallel by two contributors.

## Prothom — Partner A

Primary responsibility: citizen-query understanding.

Owned areas:

- `taxonomy/`
- `data/annotations/`
- `data/splits/`
- `src/preprocessing/`
- `src/classification/`
- `src/evaluation/`
- `models/`

Main deliverable:

`predict_understanding(text)` producing the frozen UnderstandingResult contract.

## Partner B

Primary responsibility: privacy-safe information retrieval and interface.

Owned areas:

- `data/privacy/`
- `src/privacy/`
- `knowledge_base/`
- `src/retrieval/`
- `src/response/`
- `src/pipeline/`
- `app/`

## Shared Areas

- `contracts/`
- root configuration files
- shared integration tests
- final `README.md`

Changes to shared contracts must be agreed upon before either side depends on them.

## Merge Rules

1. Stable service/topic IDs are defined in `contracts/`.
2. Neither contributor imports the other contributor's internal model classes.
3. Integration occurs through public functions and shared schemas.
4. No hard-coded local machine paths.
5. Feature work remains on separate branches.
6. Merge at defined checkpoints rather than waiting until the end.
7. Contract changes require coordination between both contributors.
