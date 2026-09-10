# Birth Registration Pilot v0.1 — Human Quality Review

Owner: Prothom
Service: `BIRTH_REGISTRATION`
Taxonomy version: `0.2.0`
Dataset: `birth_registration_pilot_v0_1.csv`

## Review Scope

The pilot contains:

- 120 synthetic queries
- 8 parent topics
- 30 query topics
- 4 seed queries per leaf

The structural dataset validator passed.

This review checks semantic quality rather than file/schema validity.

---

## Overall Result

Result:

`PASS_WITH_DATASET_REFINEMENTS_REQUIRED`

The current 30-leaf Birth Registration taxonomy remains provisionally
acceptable.

No parent or query-topic ID should currently be removed or renamed.

The pilot is suitable for identifying label boundaries, but it should
NOT yet be used as the final training dataset.

---

## 1. Query-to-Label Review

The reviewed examples are generally consistent with their assigned
query-topic labels.

Major boundaries represented successfully include:

- registration process vs online application
- registration office vs address information
- parent information vs applicant/guardian relationship
- required documents vs unavailable documents
- OTP not received vs OTP verification failure
- correction process vs field-specific correction
- own-name correction vs parent-information correction
- parent-information correction vs parent BRN mapping
- application status vs delay vs normal processing time
- application print vs certificate reprint
- verification vs verification failure
- correction vs cancellation
- service workflow vs fee information
- general information vs registration process

No obvious systematic cross-label error was found in the seed batch.

---

## 2. Keep All 30 Labels Provisionally

At this stage, do not merge any label solely because it has only four
examples.

The following lower-evidence leaves should remain provisional until
additional reviewed examples are collected:

- `BR_REGISTRATION_MISSING_DOCUMENTS`
- `BR_REGISTRATION_OTP_VERIFICATION`
- `BR_CORRECTION_PARENT_BRN_MAPPING`
- `BR_APPLICATION_DELAY`
- `BR_APPLICATION_PROCESSING_TIME`
- `BR_VERIFICATION_FAILURE`
- `BR_GENERAL_INFORMATION`

These require additional evidence before final taxonomy freeze.

---

## 3. Important Family-ID Problem

The current pilot uses 60 `parent_query_id` values, normally assigning
two rows to each family.

This was useful as an initial structural placeholder, but the rule is
too weak for leakage-safe dataset construction.

A `parent_query_id` must mean:

"These rows express the same underlying citizen query and differ mainly
as paraphrases or surface-language variants."

It must NOT mean:

"These rows belong to the same classifier label."

Two queries can have the same `query_topic_id` while still representing
different underlying query families.

Example:

"What is the birth registration fee?"

and

"Is there a fee for correction?"

may both map to:

`BR_FEES_INFORMATION`

but they are not necessarily paraphrases of the same underlying query.

Therefore their family IDs should not automatically be identical.

### Decision

Before dataset expansion, rebuild family IDs using a strict
query-family definition.

Safest rule for the existing seed batch:

Each independently authored semantic seed begins as its own family.

Controlled paraphrases generated from that seed later inherit that
seed's `parent_query_id`.

Example:

Canonical seed:

`BRP_0001`
"জন্ম নিবন্ধনের জন্য কী কী কাগজ লাগে?"

Possible later family members:

- "birth registration er documents ki ki?"
- "জন্ম নিবন্ধন করতে কোন কাগজপত্র দরকার?"
- "What documents do I need for birth registration?"

All of these may share:

`parent_query_id = BRP_0001`

A different information need such as:

"একটা required document আমার নেই"

must receive another family ID even though it belongs to a related
document topic.

---

## 4. Contrastive Synthetic Language

Several pilot examples deliberately contain explicit contrastive
phrasing such as:

- "X না, Y জানতে চাই"
- "status জানতে চাই না..."
- "certificate না..."
- "নিজের নাম না..."
- "normal processing time জানতে চাই না..."

These are useful for testing semantic boundaries.

However, they are somewhat artificial and must not become a dominant
training pattern.

Otherwise a classifier could learn shortcuts such as:

"না" + neighboring-topic keyword

instead of learning the actual citizen intent.

### Decision

Keep these examples as challenge/boundary examples.

When expanding the dataset, add more natural ambiguous examples without
explicitly naming the competing label.

---

## 5. Language Coverage

Current pilot coverage includes:

- formal Bangla
- informal Bangla
- Romanized/Banglish examples
- Bangla-English code mixing
- short queries
- longer contrastive queries

This is sufficient for the seed pilot but not sufficient for final
training.

Expansion should add:

- more natural conversational Bangla
- spelling variation
- Romanized Bangla spelling variation
- incomplete/fragmentary queries
- realistic short queries
- longer citizen complaints
- less templated sentence structures

---

## 6. Source Provenance

All 120 current rows correctly use:

`source_type = SYNTHETIC`

This must remain truthful.

Future rows should distinguish:

- `REAL`
- `SYNTHETIC`
- `PARAPHRASED`

A generated query must never be relabeled as REAL.

---

## 7. Priority Labels

Current priority values are provisional.

The pilot may retain the current values for now, but priority should
not be treated as finalized training supervision until a project-wide
priority annotation guideline is defined.

The system must not infer urgency merely from emotional wording.

---

## 8. Privacy and OOD

Current pilot:

- privacy-positive rows: 0
- OOD rows: 0

This is intentional.

Privacy examples should be added only after the shared privacy
vocabulary with Partner B is frozen.

OOD/cross-service examples should be added under the shared OOD design
rather than improvised inside this pilot.

---

## 9. Processing-Time Evidence

`BR_APPLICATION_PROCESSING_TIME` is a valid citizen question type.

However, recognizing that intent does not establish any factual number
of processing days.

Actual processing-time information must come from a verified source in
the knowledge corpus.

The classifier dataset should contain the question intent, not an
invented government answer.

---

## 10. Pilot Acceptance Decision

The pilot demonstrates that the 30-label taxonomy is sufficiently
coherent to continue development.

However, before larger-scale query generation:

1. correct `parent_query_id` semantics;
2. update the dataset validator accordingly;
3. preserve contrastive examples as challenge-style cases;
4. expand each leaf using true query families;
5. conduct additional review of low-evidence leaves.

Current status:

`PILOT_STRUCTURE_VALID`

`PILOT_SEMANTICS_PROVISIONALLY_VALID`

`QUERY_FAMILY_ASSIGNMENTS_REQUIRE_REFINEMENT`

`NOT_READY_FOR_MODEL_TRAINING`

`NOT_READY_FOR_SHARED_CONTRACT_FREEZE`