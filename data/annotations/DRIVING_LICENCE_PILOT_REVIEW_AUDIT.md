# Driving Licence Pilot Semantic Review Audit

Service: `DRIVING_LICENCE`

Result: `PASS`

## Coverage

- Parents: 10
- Leaves: 40
- Rows reviewed: 160
- Independent families: 160
- STANDARD: 84
- BOUNDARY: 28
- MANDATORY: 48
- PASS: 160
- REWRITE: 0
- RELABEL: 0
- TAXONOMY_REVIEW: 0

Every row was reviewed for naturalness, service context, label specificity,
sibling confusion, language style, priority, difficulty, family independence,
mutable-fact safety, and privacy safety. All Hard/F04 rows were included in
the boundary review. The final text contains no annotation-engineered
contrast patterns detected by the validator.

## Pilot-review leaves

- `DRIVING_LICENCE_LEARNER_ELIGIBILITY`
- `DRIVING_LICENCE_LEARNER_MEDICAL`
- `DRIVING_LICENCE_TYPE_SELECTION`
- `DRIVING_LICENCE_TEST_RETAKE`
- `DRIVING_LICENCE_ACCOUNT_OTP`
- `DRIVING_LICENCE_ACCOUNT_ACCESS_PROBLEM`
- `DRIVING_LICENCE_APPLICATION_DELAY`
- `DRIVING_LICENCE_VERIFICATION`
- `DRIVING_LICENCE_EXPIRED_RENEWAL`
- `DRIVING_LICENCE_VEHICLE_CLASS_CHANGE`
- `DRIVING_LICENCE_TYPE_CHANGE`
- `DRIVING_LICENCE_GENERAL_GUIDANCE`

These leaves remain explicit evaluation targets even though their four pilot
seeds were coherent enough to retain.

## Key boundaries checked

- learner application vs new full licence
- new-application vehicle class vs class addition on an existing licence
- test schedule vs test result vs licence status
- fee information vs payment method vs verification vs failure
- application status vs delay vs ready for collection
- renewal vs lost/damaged duplicate
- general information correction vs address/type/class change

## Decision

The pilot is structurally and semantically acceptable as a reviewed seed set.
It must not be used to train a model until project-wide approval and later
family-aware expansion/splitting. The global shared contract remains
unfrozen.
