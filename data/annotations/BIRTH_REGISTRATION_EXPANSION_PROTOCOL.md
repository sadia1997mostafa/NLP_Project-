# Birth Registration Dataset Expansion Protocol

Owner: Prothom
Service: `BIRTH_REGISTRATION`
Taxonomy version: `0.2.0`

## Starting Point

Pilot v0.1 contains:

- 120 canonical synthetic seed queries
- 30 query-topic labels
- 4 canonical seeds per query topic
- 120 independent query families

Each current seed has its own stable:

`parent_query_id`

Example:

BRQ_0001
→ BRP_0001

BRQ_0002
→ BRP_0002

The current dataset is a reviewed pilot and is not yet the final
training dataset.

---

## Expansion Goal

The next controlled dataset version will contain:

- 30 query topics
- 12 queries per query topic
- 360 total queries
- 120 semantic query families
- 3 members per family

Therefore each existing canonical seed receives exactly two controlled
paraphrases.

Structure:

120 canonical seeds
+
240 controlled paraphrases
=
360 total queries

---

## Query Family Rule

A query family represents ONE underlying citizen information need.

Example canonical seed:

BRP_0001

"নতুন জন্ম নিবন্ধন কীভাবে করব?"

Possible family members:

- "নতুন জন্ম নিবন্ধনের প্রক্রিয়া কী?"
- "new birth registration korbo kivabe?"

These may share:

`parent_query_id = BRP_0001`

because the underlying information need is unchanged.

A semantically different question must receive a different family ID
even if it shares the same classifier label.

---

## Source-Type Rule

Existing canonical seeds:

`source_type = SYNTHETIC`

New controlled variations:

`source_type = PARAPHRASED`

Do not mark generated or rewritten examples as REAL.

REAL examples will only be added from genuine citizen-query collection
or another documented real source.

---

## Expansion Pattern Per Family

Each family should contain three members:

1. canonical seed
2. natural semantic paraphrase
3. language/noise variation

Preferred pattern:

### Member 1 — Canonical

Existing reviewed pilot query.

### Member 2 — Natural paraphrase

Change the wording while preserving exactly the same citizen intent.

### Member 3 — Language/noise variant

Use one appropriate variation such as:

- Banglish
- Bangla-English code mixing
- informal Bangla
- shortened query
- realistic spelling variation
- fragmentary citizen phrasing

Do not mechanically force every family into the same language pattern.

---

## Semantic Preservation Rule

A paraphrase must preserve:

- service
- parent_topic_id
- query_topic_id
- primary information need
- privacy status
- OOD status

It may change:

- wording
- grammar
- formality
- script
- code mixing
- sentence length
- minor spelling/noise

It must NOT introduce a new information need.

---

## Bad Expansion Example

Canonical:

"জন্ম নিবন্ধনের জন্য কী কী কাগজ লাগে?"

Label:

`BR_REGISTRATION_REQUIRED_DOCUMENTS`

Bad paraphrase:

"একটা required document আমার নেই, কী করব?"

This is NOT a paraphrase.

It changes the citizen need from:

"What documents are required?"

to:

"What do I do when a document is missing?"

The second query belongs to:

`BR_REGISTRATION_MISSING_DOCUMENTS`

---

## Contrastive-Example Rule

The current pilot contains deliberately explicit boundary examples such
as:

"certificate না, submitted application form print করতে চাই"

These examples are useful challenge cases.

During expansion:

- retain them;
- do not create many paraphrases using the same "X না, Y" pattern;
- generate more natural wording around the same boundary.

This prevents shortcut learning.

---

## Label Balance

Expansion target:

12 rows per query topic.

With 30 topics:

30 × 12 = 360 rows

Every leaf should remain balanced at this stage.

Parent-level row counts will remain unequal because different parents
contain different numbers of leaf labels.

Leaf-level balance is the important property.

---

## Lower-Evidence Leaves

The following topics require especially careful review during expansion:

- `BR_REGISTRATION_MISSING_DOCUMENTS`
- `BR_REGISTRATION_OTP_VERIFICATION`
- `BR_CORRECTION_PARENT_BRN_MAPPING`
- `BR_APPLICATION_DELAY`
- `BR_APPLICATION_PROCESSING_TIME`
- `BR_VERIFICATION_FAILURE`
- `BR_GENERAL_INFORMATION`

Paraphrases for these topics must be manually inspected before
acceptance.

---

## Processing-Time Rule

`BR_APPLICATION_PROCESSING_TIME` represents the user's question type.

Dataset queries may ask:

"সাধারণত কতদিন লাগে?"

They must NOT state or imply an invented official processing duration.

Factual answers belong in the verified knowledge corpus.

---

## Privacy Rule

Do not add privacy-positive paraphrases during this expansion stage.

Current expected value:

`privacy_present = FALSE`

Partner B's privacy vocabulary must be frozen before intentionally
adding queries containing actual sensitive values.

---

## OOD Rule

Do not add OOD examples to the 360-row in-domain expansion.

OOD and cross-service hard-negative data will be constructed separately
under the shared OOD design.

Current expected value:

`is_ood = FALSE`

---

## Priority Rule

Existing priority labels remain provisional.

Paraphrasing must preserve the priority value of the canonical seed.

Changing emotional wording must not automatically change priority.

---

## Stable IDs

Existing rows remain:

BRQ_0001 ... BRQ_0120

New rows will use:

BRQ_0121 ... BRQ_0360

Existing family IDs remain:

BRP_0001 ... BRP_0120

The two paraphrases generated from each canonical seed inherit that
seed's `parent_query_id`.

Do NOT create new family IDs for those paraphrases.

---

## Train / Validation / Test Rule

Future splitting MUST happen by:

`parent_query_id`

not individual rows.

Therefore:

BRP_0001
├── canonical
├── paraphrase 1
└── paraphrase 2

must all appear in exactly one of:

- train
- validation
- test

Never split members of one family across datasets.

---

## Acceptance Criteria for Expanded v0.2 Dataset

The expanded dataset is acceptable only when:

- total rows = 360
- unique row IDs = 360
- query topics = 30
- rows per query topic = 12
- query families = 120
- rows per family = 3
- every family contains one SYNTHETIC canonical seed
- every family contains two PARAPHRASED rows
- family members share exactly one query-topic label
- no duplicate normalized text exists
- privacy-positive rows = 0
- OOD rows = 0
- all taxonomy parent-child relationships remain valid
- high-risk topics receive manual review

---

## Current Dataset State

Pilot v0.1:

`VALIDATED`

Semantic review:

`PASSED WITH REFINEMENTS`

Query-family methodology:

`CORRECTED`

Expansion protocol:

`DEFINED BY THIS DOCUMENT`

Model-training status:

`NOT READY`

Shared-contract status:

`NOT FROZEN`