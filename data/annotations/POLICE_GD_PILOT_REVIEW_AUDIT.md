# Police GD Pilot Semantic Review Audit

Service: `POLICE_GD`

Result: `PASS`

## Coverage

- Parents: 8
- Leaves: 32
- Rows reviewed: 128
- Independent families: 128
- STANDARD: 57
- BOUNDARY: 19
- MANDATORY: 52
- PASS: 128
- REWRITE: 0
- RELABEL: 0
- TAXONOMY_REVIEW: 0

Every row was reviewed for naturalness, service context, label specificity,
sibling confusion, language style, priority, difficulty, family independence,
mutable-fact safety, and privacy safety. All Hard/F04 rows were included in
the boundary review. The final text contains no annotation-engineered
contrast patterns detected by the validator.

## Pilot-review leaves

- `POLICE_GD_APPROPRIATE_USE`
- `POLICE_GD_EMERGENCY_ROUTING`
- `POLICE_GD_CASE_VS_GD_GUIDANCE`
- `POLICE_GD_JURISDICTION`
- `POLICE_GD_STOLEN_ITEM`
- `POLICE_GD_OTHER_INCIDENT`
- `POLICE_GD_OTP_PROBLEM`
- `POLICE_GD_IDENTITY_VERIFICATION_PROBLEM`
- `POLICE_GD_ACCOUNT_ACCESS_PROBLEM`
- `POLICE_GD_DELAY`
- `POLICE_GD_STATION_FOLLOWUP`
- `POLICE_GD_REFERENCE_RECOVERY`
- `POLICE_GD_GENERAL_SERVICE_GUIDANCE`

These leaves remain explicit evaluation targets even though their four pilot
seeds were coherent enough to retain.

## Key boundaries checked

- ordinary GD guidance vs emergency/immediate danger
- GD appropriate-use question vs filing process
- lost document vs lost item vs stolen item vs found item
- account registration vs complaint submission
- status vs abnormal delay
- final GD copy vs submission acknowledgement vs reference recovery
- station selection before filing vs follow-up after submission

## Decision

The pilot is structurally and semantically acceptable as a reviewed seed set.
It must not be used to train a model until project-wide approval and later
family-aware expansion/splitting. The global shared contract remains
unfrozen.
