# Phase 1 Task 4 — Five-Class Intent Definition Audit

## 1. Objective

Challenge-set construction needs explicit, reviewable boundaries for the five frozen coarse labels. This audit defines what each class includes and excludes, distinguishes weak lexical hints from semantic criteria, states when a query must be clarified, and records source-label inconsistencies without changing any label or source row.

Status: **COMPLETE — ONTOLOGY FROZEN (`FROZEN_V1`)**.

## 2. Frozen label inventory

| ID | Frozen label | Rows |
|---:|---|---:|
| 0 | NID Information Correction | 267 |
| 1 | New NID Registration | 448 |
| 2 | Lost/Stolen NID | 236 |
| 3 | NID Online Problem | 305 |
| 4 | Smart ID Card | 198 |
|  | **Total** | **1,454** |

No label was renamed, added, removed, or reassigned.

## 3. Evidence basis

The audit used three distinct evidence sources:

1. A deterministic private evidence set of 185 source rows: 27 Correction, 48 Registration, 41 Lost/Stolen, 26 Online Problem, and 43 Smart ID Card. Selection deliberately included systematic coverage, short/underspecified rows, long-form rows, multiple recorded language styles, cross-label candidate pairs, and all label-conflict families. Its SHA-256 is `7975080514ecd00ba24e7e4ebe202b9085b2a79745338c6e5e03ec25343ba2cd`.
2. The frozen Phase 1 family map and 99 final candidate-pair relations, including the three cross-label equivalent pairs.
3. `taxonomy/nid.yaml` as supporting evidence. Its five relevant fine parents map to the source labels, but the fine taxonomy was not treated as automatic authority over coarse boundaries.

Raw evidence remains in the approved private sibling directory and is not committed.

## 4. Label definitions

### 0 — NID Information Correction

Existing-record information changes: personal fields, address/voter area, photo/signature, and the associated correction procedure, evidence, fee, or status. Its main exclusion is first-time enrolment. Portal failure is Online Problem; online submission of a correction is not enough to change the underlying class.

Common but nonbinding evidence includes correction/change wording, a wrong field, or mismatch with another document. The lifecycle stage is essential when an error could be in either a pending application or an established record.

### 1 — New NID Registration

First-time NID/voter enrolment and its application lifecycle: eligibility, documents, submission, appointments, biometrics, payment, status, delay, and initial collection. Existing-record correction, post-loss replacement, and online-account access are excluded.

The key ambiguities are “registration online” (first-time application versus portal-account registration) and card collection (new-registration completion versus Smart Card distribution). Two frozen source pairs demonstrate the latter inconsistency.

### 2 — Lost/Stolen NID

Reporting, replacing, duplicating, or reissuing an issued NID after loss, theft, or damage, including documents, payment, status, and replacement collection. The requested replacement action controls even when the object is a Smart NID, consistent with the repository taxonomy; however, one frozen source conflict assigns equivalent damaged-Smart-NID needs to Lost/Stolen and Smart ID Card.

Generic “new/another card” or reissue wording without the triggering lifecycle context may require clarification.

### 3 — NID Online Problem

NID online-services account creation/access, login, password recovery, OTP, face/biometric verification, portal availability, online-copy access, and explicit technical failure. Online as a channel does not override a clearly identified registration, correction, replacement, or Smart Card lifecycle.

The principal ambiguity is an unspecified “online registration” or “online status” query whose target process is missing.

### 4 — Smart ID Card

Smart NID eligibility, application, issuance, readiness, distribution, status, collection, delay, and other specifically Smart lifecycle needs. Smart wording is an entity cue rather than a complete rule: explicit loss/damage replacement belongs semantically with Lost/Stolen under the action-based contract, and record correction remains Correction.

This label participates in every known cross-label equivalence conflict. Targeted human review resolved routine Smart collection to Smart ID Card and damage-driven Smart replacement to Lost/Stolen NID without changing the six historical source rows.

## 5. Pairwise decision boundaries

| Pair | Risk | Primary boundary | Clarification condition |
|---|---|---|---|
| Correction / Registration | High | established-record change vs first-time/pending enrolment | record/application stage missing |
| Correction / Lost-Stolen | Moderate | change record content vs replace/reissue after loss/theft/damage | generic reissue without cause |
| Correction / Online | High | authoritative-record change vs account/portal/verification failure | “online information” without record target |
| Correction / Smart | Moderate | recorded-information change vs Smart issuance/distribution | Smart entity named but action unclear |
| Registration / Lost-Stolen | Moderate | first issuance vs replacement of a prior card | “new/another card” without prior-card context |
| Registration / Online | High | first-time NID enrolment vs online-account registration/failure | “online registration” without object |
| Registration / Smart | High | general first enrolment vs Smart-specific lifecycle | collection/application context missing; two source conflicts |
| Lost-Stolen / Online | Moderate | replacement lifecycle vs technical portal failure | online payment/status wording without actual problem |
| Lost-Stolen / Smart | High | loss/damage replacement vs routine Smart issuance/distribution | Smart unavailable without loss/delay context; one source conflict |
| Online / Smart | Moderate | portal/account malfunction vs Smart lifecycle status | online Smart status vs portal failure unclear |

All ten unordered label pairs are represented in the machine-readable neighbor matrix.

## 6. High-risk confusions

Four relationships are especially important:

- Correction versus Registration, where a form/application error must be separated from an established-record correction.
- Correction versus Online Problem, where the online channel must not replace the underlying requested action.
- Registration versus Smart ID Card, where two cross-label equivalent collection pairs show direct source inconsistency.
- Lost/Stolen versus Smart ID Card, where one cross-label equivalent damaged-card pair conflicts despite a defensible action-based rule.

The Git-safe conflict register contains three pairs and six affected sample IDs. It records two exact-normalized-text cross-label conflicts and one semantic-equivalence cross-label conflict. Source labels were not changed.

## 7. Known source-label conflicts

| Conflict | Pair | Samples | Frozen labels | Status |
|---|---|---|---|---|
| NID5-SC-0001 | NID5-ND-000048 | NID5-V1-000592 / NID5-V1-001355 | Registration / Smart | future relabel review required |
| NID5-SC-0002 | NID5-ND-000050 | NID5-V1-000602 / NID5-V1-001371 | Registration / Smart | future relabel review required |
| NID5-SC-0003 | NID5-ND-000071 | NID5-V1-000894 / NID5-V1-001449 | Lost-Stolen / Smart | future relabel review required |

No raw query text appears in this report or the conflict register.

## 8. Clarification criteria

A query is `CLASSIFIABLE` when explicit information supports one coarse intent and competing labels would require adding an unstated event or lifecycle stage.

A query is `CLARIFY_REQUIRED` when multiple labels remain materially plausible, the requested action is absent, only an entity/channel is named, or a decision would require assuming first issuance versus existing record, ordinary Smart distribution versus replacement, or lifecycle tracking versus portal failure.

`CLARIFY_REQUIRED` is an evaluation/annotation state for future challenge construction. It is not a sixth training label.

## 9. Ontology limitations

The five classes compress several lifecycle stages and mix process categories with a card subtype. Consequently, Smart ID Card overlaps structurally with registration, replacement, and online status. The current source also contains three directly observed cross-label equivalence conflicts. The contract can state a coherent action-based policy, but it cannot retroactively make the frozen source internally consistent.

The private evidence sample is broad but not an independent dual annotation of all 1,454 rows. Common cues are descriptive, not exhaustive or deterministic.

## 10. Human Boundary Adjudication

Targeted human review resolved all three semantic conflict cases:

| Pair | Human-confirmed canonical label |
|---|---|
| NID5-ND-000048 | Smart ID Card |
| NID5-ND-000050 | Smart ID Card |
| NID5-ND-000071 | Lost/Stolen NID |

The resulting frozen principles are:

- routine Smart-specific collection belongs to Smart ID Card;
- damage-driven replacement belongs to Lost/Stolen NID, even when the object is a Smart NID;
- requested action and lifecycle stage take precedence over the word “Smart”;
- historical label disagreement does not itself mean that the query is ambiguous; and
- historical source labels remain unchanged and auditable.

The original private queue SHA-256 is `11d88b5dc0a5450f252ea5d46f6bb9a893cd8d054e9e715d8b6e01393a6dfda0`. The resolved private review SHA-256 is `4c87b5e97821bb7c363a852211a6a7e5d56b744757f296520a5aac9c0f7d357c`.

## 11. Implication for challenge-set design

The `FROZEN_V1` contract and annotation policy are ready to govern challenge-set design. Future annotations must use the requested-action rule, keep frozen paraphrase families together, record `CLARIFY_REQUIRED` only when the query itself is insufficient, and preserve source provenance separately from canonical benchmark labels. No challenge examples or splits were created in this task.
