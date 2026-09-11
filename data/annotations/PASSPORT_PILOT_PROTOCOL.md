# Passport Pilot Dataset Protocol

## NagorikSheba AI

**Owner:** Prothom / Partner A  
**Service:** PASSPORT  
**Taxonomy version:** 0.2.0  
**Taxonomy parents:** 8  
**Taxonomy leaf intents:** 56  
**Semantic audit:** PASS WITH PILOT-REVIEW FLAGS  
**Pilot dataset version:** 0.1  
**Training status:** DO NOT TRAIN YET  

---

# 1. Purpose

This document defines the controlled annotation protocol for the first
Passport query-classification pilot dataset.

The purpose of the pilot is NOT to build a large training dataset.

The purpose is to test whether the current Passport taxonomy can be applied
consistently to realistic Bangladesh citizen queries before large-scale
dataset generation begins.

The pilot will test:

- semantic clarity of all 56 query-topic leaves;
- confusion between neighboring intents;
- usefulness of broad or generic leaves;
- Bangla and Banglish query coverage;
- priority-label consistency;
- parent/query-topic consistency;
- query-family design;
- whether any leaf should be merged, removed or redefined.

No Passport classifier should be trained from this pilot until the pilot has
received human semantic review.

---

# 2. Pilot Size

The Passport taxonomy contains:

```text
56 query-topic leaves
````

The initial pilot will contain:

```text
4 independent seed queries per leaf
```

Therefore:

```text
56 × 4 = 224 pilot rows
```

Expected pilot size:

```text
224 rows
```

Every leaf must receive exactly four initial seed queries.

---

# 3. Important Family-Design Rule

The four initial rows for a query-topic leaf must represent four independent
query families.

Example:

```text
PASSPORT_PAYMENT_FAILURE_F01
PASSPORT_PAYMENT_FAILURE_F02
PASSPORT_PAYMENT_FAILURE_F03
PASSPORT_PAYMENT_FAILURE_F04
```

Each pilot row therefore receives its own `parent_query_id`.

The pilot must NOT begin by generating several paraphrases of one seed.

Correct:

```text
Seed 1 → F01
Seed 2 → F02
Seed 3 → F03
Seed 4 → F04
```

Incorrect:

```text
Seed 1
 ├── paraphrase
 ├── paraphrase
 └── paraphrase
```

Paraphrases will be generated only after human review.

When controlled paraphrases are later added, they must inherit the
`parent_query_id` of their original seed family.

Example:

```text
Original seed:
PASSPORT_PAYMENT_FAILURE_F02

Later paraphrase 1:
PASSPORT_PAYMENT_FAILURE_F02

Later paraphrase 2:
PASSPORT_PAYMENT_FAILURE_F02
```

This design is required for future leakage-safe splitting.

---

# 4. Canonical Dataset Schema

The Passport pilot must use the project-wide canonical schema:

```text
id
text
service
parent_topic_id
parent_topic
query_topic_id
query_topic
priority
language_style
privacy_present
privacy_types
source_type
parent_query_id
difficulty
is_ood
annotation_notes
```

No Passport-specific replacement schema should be created.

---

# 5. ID Convention

Pilot row IDs use:

```text
PASSQ_0001
PASSQ_0002
...
PASSQ_0224
```

Requirements:

* IDs must be unique.
* IDs must be sequential.
* IDs must not encode mutable factual information.
* IDs must remain stable after review unless the row itself is deleted.

---

# 6. Service Label

Every in-domain Passport pilot row must contain:

```text
service = PASSPORT
```

No other service ID is allowed in this pilot.

Formal OOD rows are intentionally postponed until the project-wide OOD
protocol is defined.

---

# 7. Parent Labels

The only allowed Passport parent-topic IDs are:

```text
PASSPORT_APPLICATION

PASSPORT_DOCUMENTS

PASSPORT_ONLINE_ACCOUNT

PASSPORT_APPOINTMENT_AND_ENROLMENT

PASSPORT_REISSUE

PASSPORT_FEES_AND_PAYMENT

PASSPORT_STATUS_AND_DELIVERY

PASSPORT_GENERAL_INFORMATION
```

The `parent_topic_id` for every row must be derived from the taxonomy rather
than manually invented.

The corresponding `parent_topic` value must use the taxonomy display name.

---

# 8. Query-Topic Labels

Every row must use one of the 56 query-topic IDs defined in:

```text
taxonomy/passport.yaml
```

The corresponding `query_topic` column must use that leaf's taxonomy
`display_name`.

No new query-topic label may be invented during pilot generation.

If a realistic query cannot be represented cleanly by the taxonomy, document
that problem during human review instead of silently creating a new label.

---

# 9. Rows Per Query Topic

Every retained query-topic leaf receives exactly:

```text
4 rows
```

The initial pilot must therefore satisfy:

```text
number of leaves = 56
rows per leaf = 4
total rows = 224
```

No class should receive additional examples during the initial pilot merely
because it appears easier to generate.

Balanced coverage is intentional at this stage.

---

# 10. Language Coverage

The four independent seeds for each leaf should aim for the following
variation.

## Seed family F01

Primarily formal Bangla.

Example style:

```text
আমার পাসপোর্ট আবেদনের বর্তমান অবস্থা কীভাবে যাচাই করব?
```

Typical label:

```text
language_style = Formal
```

---

## Seed family F02

Natural informal Bangla.

Example style:

```text
আমার passport application এখন কোন stage এ আছে?
```

Typical label:

```text
language_style = Informal
```

---

## Seed family F03

Bangla-English code mixing.

Example style:

```text
passport application er status online e check korbo kivabe?
```

Typical label:

```text
language_style = Mixed
```

---

## Seed family F04

Banglish / boundary-aware / less canonical wording.

Example style:

```text
amar passport er kaj koto dur hoise eta kivabe dekhbo?
```

Typical label:

```text
language_style = Mixed
```

These are coverage targets, not mechanical templates.

Naturalness is more important than forcing identical sentence structures
across all classes.

---

# 11. Language-Style Vocabulary

Allowed values are:

```text
Formal
Informal
Mixed
```

Do not create new labels such as:

```text
Banglish
Romanized
English
CodeMixed
```

Banglish and code-mixed text should currently use:

```text
Mixed
```

when appropriate.

---

# 12. Source Provenance

Every initial Passport pilot row is synthetic.

Therefore:

```text
source_type = SYNTHETIC
```

Never label generated queries as:

```text
REAL
```

REAL must remain reserved for genuinely sourced human queries with legitimate
provenance.

---

# 13. Privacy Policy for This Pilot

The Passport pilot is intended to validate semantic intent boundaries.

Therefore:

```text
privacy_present = False
privacy_types =
```

for all initial pilot rows.

Do not insert realistic:

* passport numbers;
* NID numbers;
* phone numbers;
* addresses;
* payment-account details;
* email addresses;
* application identifiers.

Privacy-positive examples will be added only after the project privacy
annotation contract has been finalized with Partner B.

---

# 14. OOD Policy for This Pilot

The initial Passport pilot contains only Passport in-domain queries.

Therefore:

```text
is_ood = False
```

for every initial pilot row.

Do not yet add:

* visa questions;
* NID-only questions;
* tax questions;
* Police GD questions;
* Driving Licence questions;
* unrelated conversation.

Those will later be introduced under the shared OOD protocol.

---

# 15. Priority Policy

Allowed values:

```text
Low
Medium
High
```

Priority represents the urgency or administrative impact of the citizen's
problem, not model confidence.

For the Passport pilot, use the following default policy.

## Low

Use `Low` for routine informational or ordinary procedural queries.

Typical examples:

* how to apply;
* required documents;
* passport options;
* normal login instructions;
* appointment date;
* payment method;
* fee information;
* normal processing time;
* collection procedure;
* general information.

---

## Medium

Use `Medium` when the citizen describes an active administrative problem,
failure or loss that normally requires corrective action.

Typical examples:

* required document unavailable;
* account access failure;
* activation email not received;
* appointment problem;
* application delay;
* payment failure;
* money deducted but payment failed;
* refund request;
* lost passport;
* stolen passport;
* damaged passport;
* lost delivery slip;
* information-change reissue.

---

## High

Do not manufacture `High` examples simply to balance the priority classes.

Use `High` only if a later project-wide priority policy clearly defines a
Passport scenario that warrants the label.

It is acceptable for the initial Passport pilot to contain few or zero High
rows.

---

# 16. Difficulty Policy

Allowed values:

```text
Easy
Medium
Hard
```

Difficulty describes semantic classification difficulty.

It does not describe grammar quality.

Suggested four-row pattern per leaf:

```text
F01 → Easy
F02 → Easy or Medium
F03 → Medium
F04 → Medium or Hard
```

A Hard query should normally represent a realistic boundary case rather than
an intentionally confusing or unnatural sentence.

---

# 17. Easy Queries

Easy queries should state the intent directly.

Example:

```text
আমার পাসপোর্ট হারিয়ে গেছে, নতুনটা কীভাবে পাব?
```

Likely label:

```text
PASSPORT_REISSUE_LOST
```

---

# 18. Medium Queries

Medium queries may contain:

* informal language;
* code mixing;
* shorter wording;
* common ambiguity that remains resolvable;
* indirect phrasing.

Example:

```text
passport ta আর খুঁজে পাচ্ছি না, এখন replacement কীভাবে হবে?
```

---

# 19. Hard / Boundary Queries

Hard queries should intentionally test neighboring intent boundaries while
remaining natural.

Example:

```text
passport হারায়নি, শুধু collection-এর slipটা পাচ্ছি না।
```

Correct label:

```text
PASSPORT_DELIVERY_SLIP_LOST
```

This helps distinguish it from:

```text
PASSPORT_REISSUE_LOST
```

A boundary query should contain enough context for a human annotator to
determine the intended class.

Do not create genuinely ambiguous nonsense simply to produce a Hard example.

---

# 20. Annotation Notes

Every initial row should include:

```text
Passport pilot v0.1 synthetic independent seed; human semantic review required before training.
```

For specially designed boundary rows, an additional short note may be added,
for example:

```text
Boundary case: distinguish application status from application delay.
```

Do not store long explanations in every row.

---

# 21. No Mutable Government Facts

Pilot queries should test intent recognition rather than factual correctness.

Do not encode current factual answers such as:

* exact Passport fee;
* exact processing days;
* current payment provider;
* current passport-office address;
* current embassy address;
* current delivery schedule.

Acceptable:

```text
Express passport-এর fee কত?
```

Avoid:

```text
Express passport-এর fee কি ৮,০৫০ টাকা?
```

The first tests the intent.

The second unnecessarily embeds a potentially changing government fact.

Mutable government facts belong in Partner B's verified corpus.

---

# 22. Annotation Specificity Rule

Use the most specific supported query-topic label.

Example:

```text
আমি passport fee কীভাবে pay করব?
```

Use:

```text
PASSPORT_PAYMENT_METHOD
```

not:

```text
PASSPORT_FEES_INFORMATION
```

---

# 23. Boundary Rule — Application vs Online Account

Query:

```text
e-passport portal e account khulbo kivabe?
```

Label:

```text
PASSPORT_ONLINE_ACCOUNT_REGISTRATION
```

Query:

```text
e-passport application online e submit korbo kivabe?
```

Label:

```text
PASSPORT_APPLICATION_ONLINE
```

The first concerns account creation.

The second concerns the passport application transaction.

---

# 24. Boundary Rule — General Documents vs Named Documents

Query:

```text
passport করতে কী কী documents লাগবে?
```

Label:

```text
PASSPORT_DOCUMENTS_REQUIRED
```

Query:

```text
passport করতে NID লাগবে?
```

Label:

```text
PASSPORT_DOCUMENTS_NID_REQUIREMENT
```

Query:

```text
birth registration দিয়ে passport করা যাবে?
```

Label:

```text
PASSPORT_DOCUMENTS_BIRTH_REGISTRATION_REQUIREMENT
```

Specific document intents take precedence over the general document class.

---

# 25. Boundary Rule — Documents vs Missing Documents

Query:

```text
passport application-এর documents কী কী?
```

Label:

```text
PASSPORT_DOCUMENTS_REQUIRED
```

Query:

```text
required একটা document আমার কাছে নেই, এখন কী করব?
```

Label:

```text
PASSPORT_DOCUMENTS_MISSING
```

The second explicitly describes document unavailability.

---

# 26. Boundary Rule — Appointment vs Enrolment

Query:

```text
passport appointment book করব কীভাবে?
```

Label:

```text
PASSPORT_APPOINTMENT_SCHEDULING
```

Query:

```text
passport enrolment-এর সময় কী হয়?
```

Label:

```text
PASSPORT_ENROLMENT_PROCESS
```

Query:

```text
biometric-এর সময় কী কী নেওয়া হয়?
```

Label:

```text
PASSPORT_ENROLMENT_BIOMETRICS
```

---

# 27. Boundary Rule — Enrolment Documents vs Appointment Requirements

Query:

```text
biometric-এর দিন কোন documents নিয়ে যাব?
```

Label:

```text
PASSPORT_DOCUMENTS_ENROLMENT
```

Query:

```text
appointment-এ যাওয়ার আগে কী প্রস্তুতি নিতে হবে?
```

Label:

```text
PASSPORT_APPOINTMENT_REQUIREMENTS
```

Document-focused questions take the document intent.

---

# 28. Boundary Rule — Reissue General vs Specific Cause

Query:

```text
passport reissue করার process কী?
```

Label:

```text
PASSPORT_REISSUE_PROCESS
```

But:

```text
passport expire হয়ে গেছে, reissue করব কীভাবে?
```

Label:

```text
PASSPORT_REISSUE_EXPIRY
```

And:

```text
passport হারিয়ে গেছে, replacement কীভাবে পাব?
```

Label:

```text
PASSPORT_REISSUE_LOST
```

A stated cause takes precedence over the generic reissue label.

---

# 29. Boundary Rule — Lost vs Stolen vs Damaged

These remain distinct pilot classes.

```text
হারিয়ে গেছে
→ PASSPORT_REISSUE_LOST
```

```text
চুরি হয়েছে
→ PASSPORT_REISSUE_STOLEN
```

```text
নষ্ট / ছিঁড়ে গেছে
→ PASSPORT_REISSUE_DAMAGED
```

The pilot must test whether citizens express these differences clearly enough
for stable annotation.

---

# 30. Boundary Rule — General Reissue vs No Information Change

Query:

```text
passport reissue করতে চাই।
```

Label:

```text
PASSPORT_REISSUE_PROCESS
```

Query:

```text
সব information একই থাকবে, শুধু passport reissue করব।
```

Label:

```text
PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE
```

Explicit unchanged-information wording is required for the second class.

---

# 31. Boundary Rule — Payment Failure

Query:

```text
passport payment fail করছে।
```

Label:

```text
PASSPORT_PAYMENT_FAILURE
```

Query:

```text
টাকা কেটে নিয়েছে কিন্তু payment failed দেখাচ্ছে।
```

Label:

```text
PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED
```

Query:

```text
failed payment-এর টাকা refund পাব কীভাবে?
```

Label:

```text
PASSPORT_PAYMENT_REFUND
```

The immediate citizen goal determines the label.

---

# 32. Boundary Rule — Payment Receipt vs Delivery Slip

Query:

```text
passport fee payment receipt কোথায় পাব?
```

Label:

```text
PASSPORT_PAYMENT_RECEIPT
```

Query:

```text
passport collect করার delivery slip হারিয়ে গেছে।
```

Label:

```text
PASSPORT_DELIVERY_SLIP_LOST
```

These documents must never share a label.

---

# 33. Boundary Rule — Status vs Delay vs Processing Time

Query:

```text
আমার passport application এখন কোন stage-এ?
```

Label:

```text
PASSPORT_APPLICATION_STATUS
```

Query:

```text
আমার passport application অনেকদিন ধরে stuck।
```

Label:

```text
PASSPORT_APPLICATION_DELAY
```

Query:

```text
সাধারণত passport হতে কতদিন লাগে?
```

Label:

```text
PASSPORT_PROCESSING_TIME
```

The key distinction is:

```text
current state
vs
abnormal delay
vs
normal expected duration
```

---

# 34. Boundary Rule — Delivery Category vs Delivery Fee

Query:

```text
regular আর express passport service-এর difference কী?
```

Label:

```text
PASSPORT_DELIVERY_CATEGORY
```

Query:

```text
express passport-এর fee কত?
```

Label:

```text
PASSPORT_FEES_DELIVERY_CATEGORY
```

The presence of a service-category name alone does not determine the class.

The citizen's requested information determines the class.

---

# 35. Boundary Rule — Ready vs Collection

Query:

```text
আমার passport collect করার জন্য ready হয়েছে?
```

Label:

```text
PASSPORT_READY_FOR_COLLECTION
```

Query:

```text
passport ready হয়েছে, এখন কোথা থেকে collect করব?
```

Label:

```text
PASSPORT_COLLECTION
```

---

# 36. Boundary Rule — Lost Passport vs Lost Delivery Slip

Query:

```text
passport হারিয়ে গেছে।
```

Label:

```text
PASSPORT_REISSUE_LOST
```

Query:

```text
passport না, collection slipটা হারিয়েছে।
```

Label:

```text
PASSPORT_DELIVERY_SLIP_LOST
```

Hard pilot examples should explicitly test this distinction.

---

# 37. Boundary Rule — General Information

General-information classes must never become fallback labels.

Query:

```text
e-Passport কী?
```

Label:

```text
PASSPORT_GENERAL_EPASSPORT_INFORMATION
```

Query:

```text
আগে passport ছিল, এখন new নাকি reissue select করব?
```

Label:

```text
PASSPORT_GENERAL_NEW_VS_REISSUE
```

Query:

```text
passport-এর কী কী service নিয়ে এখানে help পাওয়া যায়?
```

Label:

```text
PASSPORT_GENERAL_SERVICE_GUIDANCE
```

But a low-confidence or unsupported query must NOT automatically receive a
general-information label.

---

# 38. Mandatory Pilot-Review Leaves

The semantic audit identified seven leaves requiring explicit pilot review.

They are:

```text
PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC

PASSPORT_DOCUMENTS_MISSING

PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC

PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM

PASSPORT_APPOINTMENT_PROBLEM

PASSPORT_APPLICATION_DELAY

PASSPORT_GENERAL_SERVICE_GUIDANCE
```

These leaves remain provisional.

---

# 39. Review Rule for Official / Diplomatic Application

For:

```text
PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC
```

the pilot must determine whether realistic application-process queries form a
distinct class.

Do not create ordinary passport queries and simply insert the word
"official."

The semantic information need must genuinely involve the official or
diplomatic passport workflow.

---

# 40. Review Rule for Official / Diplomatic Documents

For:

```text
PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC
```

examples must genuinely ask about supporting documentation.

Examples should distinguish:

```text
How do I apply?
```

from:

```text
What GO/NOC/supporting papers are required?
```

If this distinction cannot be maintained consistently, the leaves should be
reconsidered after pilot review.

---

# 41. Review Rule for Missing Documents

For:

```text
PASSPORT_DOCUMENTS_MISSING
```

examples must indicate that a supporting document required for Passport
processing is unavailable.

Do not confuse:

```text
required document missing
```

with:

```text
passport itself missing
```

---

# 42. Review Rule for Account Access Problem

For:

```text
PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM
```

the pilot must include examples where:

* the account exists;
* access fails;
* no more specific known cause is stated.

Do not use this class when the query clearly specifies:

* forgotten password;
* activation issue;
* missing activation email;
* email update;
* mobile update.

---

# 43. Review Rule for Appointment Problem

For:

```text
PASSPORT_APPOINTMENT_PROBLEM
```

generate natural generic appointment-problem queries.

If every plausible example instead belongs to:

* scheduling;
* appointment date;
* account access;
* enrolment location;

the class may be removed after review.

---

# 44. Review Rule for Application Delay

For:

```text
PASSPORT_APPLICATION_DELAY
```

at least one pilot query should clearly contrast delay with ordinary status.

Example:

```text
status শুধু জানতে চাই না; application অনেকদিন ধরে একই জায়গায় আটকে আছে।
```

This tests the semantic boundary against:

```text
PASSPORT_APPLICATION_STATUS
```

---

# 45. Review Rule for General Service Guidance

For:

```text
PASSPORT_GENERAL_SERVICE_GUIDANCE
```

the pilot should test whether broad orientation questions form a genuine,
coherent intent.

It must not become a catch-all label.

If the pilot cannot generate four natural independent families without
forcing artificial wording, the leaf should be considered for removal.

---

# 46. Independent Seed Requirement

Each of the four rows for a leaf must express a meaningfully different query
situation or wording strategy.

Do not generate four trivial lexical substitutions such as:

```text
How do I check passport status?
How can I check passport status?
Where do I check passport status?
Tell me how to check passport status.
```

These do not provide sufficient semantic variety.

Prefer differences such as:

```text
direct procedural question
informal citizen phrasing
Banglish wording
boundary-aware wording
```

---

# 47. Paraphrase Policy

The initial pilot contains independent seeds.

After human review, controlled paraphrases may be added.

A paraphrase must:

* preserve the same intent;
* preserve the same `parent_query_id`;
* vary natural surface form;
* not introduce another dominant intent;
* not introduce false government facts.

Example:

```text
Seed:
আমার passport application অনেকদিন ধরে pending।

parent_query_id:
PASSPORT_APPLICATION_DELAY_F02
```

Later paraphrases may share:

```text
PASSPORT_APPLICATION_DELAY_F02
```

This family must remain within one dataset split.

---

# 48. Leakage Prevention

Future train/validation/test splitting must operate at the query-family level.

Never allow:

```text
original seed → train
paraphrase of same seed → validation
```

or:

```text
original seed → train
paraphrase of same seed → test
```

Instead:

```text
entire family → exactly one split
```

The initial four independent families per leaf are intended to make this
possible later.

---

# 49. Duplicate Prevention

The pilot validator must check:

* exact duplicate text;
* normalized duplicate text;
* duplicate row IDs;
* duplicate `(query_topic_id, parent_query_id)` where each pilot family is
  expected to contain only one seed;
* incorrect parent/query-topic relationships.

Near-duplicates should additionally be reviewed manually.

---

# 50. Human Review Questions

For every pilot row, the reviewer should answer:

1. Is the query natural?
2. Is the Passport context clear?
3. Is the service label correct?
4. Is the parent topic correct?
5. Is the query-topic label correct?
6. Is a more specific leaf available?
7. Could a neighboring leaf reasonably receive the query?
8. Is the language-style label reasonable?
9. Is the priority reasonable?
10. Is the difficulty reasonable?
11. Is the query independent from the other seed families?
12. Does the row contain unnecessary mutable factual claims?
13. Does it accidentally contain private information?
14. Should the leaf itself be retained?

---

# 51. Pilot Acceptance Criteria

The pilot can pass initial structural validation only if all of the following
hold:

```text
Rows = 224

Services = PASSPORT only

Parents represented = 8

Query-topic leaves represented = 56

Rows per leaf = 4

Independent parent_query_id families per leaf = 4

Unique parent_query_id values = 224

Unique row IDs = 224

source_type = SYNTHETIC for all rows

privacy_present = False for all rows

is_ood = False for all rows

No exact duplicate text

No normalized duplicate text

Every parent/query-topic relationship matches taxonomy/passport.yaml
```

---

# 52. Pilot Semantic Acceptance Criteria

Structural validity alone is not sufficient.

After human review:

* all 56 leaves must be reviewed;
* all seven mandatory pilot-review leaves must receive explicit decisions;
* confusing neighboring classes must be documented;
* artificial or incoherent queries must be rewritten or removed;
* query families must be corrected before expansion;
* any taxonomy change must happen before large-scale paraphrase generation.

---

# 53. What Happens After Pilot Review

If the pilot passes semantic review:

```text
Pilot seed set
       ↓
Human semantic review
       ↓
Taxonomy fixes if required
       ↓
Freeze reviewed seed families
       ↓
Controlled paraphrase expansion
       ↓
Expanded dataset validation
       ↓
Family-aware train/dev/test split
       ↓
Model training
```

Do not skip directly from pilot generation to model training.

---

# 54. Expected Expansion Strategy

The intended later target is approximately:

```text
4 independent families per leaf
×
3 members per family
=
12 rows per leaf
```

With 56 retained Passport leaves:

```text
56 × 12 = 672 rows
```

This is only a target.

The final size may change if pilot review:

* removes leaves;
* merges leaves;
* adds needed leaves;
* identifies low-quality families.

The taxonomy review takes precedence over a fixed row-count target.

---

# 55. Pilot Dataset Status

At protocol creation time:

```text
taxonomy semantic audit = PASSED

pilot protocol = DEFINED

pilot dataset = NOT YET CREATED

pilot human review = NOT STARTED

dataset expansion = NOT STARTED

shared contract = NOT FROZEN
```

The next implementation step is to create the controlled 224-row Passport
pilot dataset according to this protocol.
