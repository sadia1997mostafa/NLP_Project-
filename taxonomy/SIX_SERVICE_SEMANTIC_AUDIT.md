# Six-Service Semantic Consistency Audit

Result: `PASS`

The reviewed taxonomies contain 49 service-specific parents and 264 unique
query-topic IDs. Repeated concepts such as application, eligibility,
documents, correction, account access, payment, status and replacement are
valid cross-service patterns; their IDs remain owned by the service prefix.

Verified prefixes:

- `NID_`
- `BR_`
- `PASSPORT_`
- `TAX_`
- `POLICE_GD_`
- `DRIVING_LICENCE_`

No stable ID was renamed. General-information leaves remain genuine semantic
intents and are not OOD fallbacks. Mutable government answers are absent from
label IDs. Service context is preserved in the global contract, preventing a
shared concept such as “status” from becoming a cross-service ID collision.

All service-level semantic audits exist. Lower-evidence leaves remain
documented limitations, not structural blockers, because they have complete
boundaries and controlled pilot/core coverage. The six-service label set is
acceptable for a versioned pre-training contract freeze.
