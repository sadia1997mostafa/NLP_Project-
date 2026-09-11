# NagorikSheba AI — Passport Parent-Topic Semantic Review

Owner: Prothom
Service: `PASSPORT`
Taxonomy version reviewed: `0.1.0`
Source taxonomy: `taxonomy/passport.yaml`

Review result:

`PASS_WITH_PARENT_REFINEMENT_REQUIRED`

---

# 1. Purpose

This review evaluates whether the drafted Passport parent topics form a
clean first-level classification layer before specific query-topic IDs
are created.

A parent topic should represent the citizen's primary information need.

Good parent topics should be:

- semantically coherent;
- reasonably distinguishable from neighboring parents;
- useful for hierarchical classification;
- broad enough to contain multiple specific intents;
- not merely contextual attributes such as location or applicant type.

The current draft contains 10 parent topics.

---

# 2. Current Parent Topics

Current draft:

1. `PASSPORT_APPLICATION`
2. `PASSPORT_DOCUMENTS`
3. `PASSPORT_ONLINE_ACCOUNT`
4. `PASSPORT_APPOINTMENT_AND_ENROLMENT`
5. `PASSPORT_REISSUE`
6. `PASSPORT_FEES_AND_PAYMENT`
7. `PASSPORT_STATUS_AND_DELIVERY`
8. `PASSPORT_OVERSEAS_SERVICE`
9. `PASSPORT_SPECIAL_CATEGORY`
10. `PASSPORT_GENERAL_INFORMATION`

After semantic review, eight are suitable as first-level intent parents.

Two require restructuring.

---

# 3. Parent Topics Recommended to Keep

## 3.1 PASSPORT_APPLICATION

Decision:

`KEEP`

This parent represents questions about obtaining a new passport when the
citizen does not already have a passport being re-issued.

Suitable child intents may later include:

- general new-passport process;
- online application;
- first-time application;
- passport office selection;
- application information;
- passport type / validity / page choice;
- application from abroad.

### Boundary

Do not include:

- re-issue of an existing passport;
- document-only questions;
- payment-only questions;
- submitted-application status.

### Office selection

Passport-office selection should remain under application for now.

It represents routing of the application rather than a sufficiently
large independent citizen-service family.

---

## 3.2 PASSPORT_DOCUMENTS

Decision:

`KEEP`

Questions specifically asking what documents, certificates or supporting
evidence are required form a coherent citizen information need.

Possible children may later distinguish:

- general required documents;
- NID / Birth Registration requirements;
- minor applicant documents;
- previous-passport requirement;
- missing document;
- special-category supporting documents.

### Boundary

A question such as:

"What documents are required for a new passport?"

belongs here rather than under `PASSPORT_APPLICATION` because the
citizen's immediate information need is documentation.

---

## 3.3 PASSPORT_ONLINE_ACCOUNT

Decision:

`KEEP`

The online account has a sufficiently distinct workflow and failure
space.

Potential children:

- account registration;
- login;
- forgotten password;
- password reset;
- account activation;
- activation email not received;
- registered contact-information changes;
- account-access failure.

### Boundary

Portal account problems should not be merged with:

- online passport application;
- appointment problems;
- application status.

The portal may host all of these, but the citizen intent is different.

---

## 3.4 PASSPORT_APPOINTMENT_AND_ENROLMENT

Decision:

`KEEP`

Appointment and enrolment represent a coherent operational stage after
application preparation.

Potential children:

- appointment scheduling;
- appointment problem;
- appointment requirements;
- enrolment process;
- enrolment location;
- enrolment preparation.

### Biometric caution

Do not create highly specific biometric-failure labels unless sufficient
official and citizen-query evidence exists.

---

## 3.5 PASSPORT_REISSUE

Decision:

`KEEP`

Re-issue is fundamentally different from first-time passport application
because the citizen already has or previously had a passport.

Potential children may later include:

- general re-issue;
- expired / expiring passport;
- re-issue without information change;
- re-issue with information change;
- lost passport;
- stolen passport;
- damaged passport;
- overseas re-issue.

### Lost / stolen / damaged

These remain under `PASSPORT_REISSUE`.

They should probably become separate leaf intents because their wording
and supporting workflows can differ, but they do not currently justify
separate parent topics.

---

## 3.6 PASSPORT_FEES_AND_PAYMENT

Decision:

`KEEP`

Payment questions form a strong independent information need.

Potential children:

- fee information;
- payment method;
- payment confirmation;
- payment failure;
- deducted money but unsuccessful payment;
- payment receipt / slip.

### Important boundary

General fee information and payment failure must not become the same
specific intent.

Exact fee amounts remain Partner B knowledge-corpus facts.

---

## 3.7 PASSPORT_STATUS_AND_DELIVERY

Decision:

`KEEP`

This parent covers the post-submission lifecycle of the passport.

Potential children:

- application status;
- application delay;
- expected processing time;
- delivery type;
- passport readiness;
- passport collection;
- delivery-slip problem.

These concepts are related by application lifecycle but must remain
separate at the leaf level.

### Important boundaries

Status:

"What stage is my application currently in?"

Delay:

"My application has been stuck for a long time."

Processing time:

"Normally how long does passport processing take?"

Collection:

"My passport is ready; how do I collect it?"

These should become different specific intents.

### Lost delivery slip

A lost delivery slip must never be confused with a lost passport.

---

## 3.8 PASSPORT_GENERAL_INFORMATION

Decision:

`KEEP_WITH_NARROW_SCOPE`

This parent is useful only for genuinely broad informational questions.

Examples:

- What is an e-Passport?
- What is passport re-issue?
- I want general information about Bangladesh passport services.

It must not become a fallback label.

Unsupported, ambiguous or unrelated queries must later be handled by
confidence/OOD logic rather than automatically classified as general
information.

---

# 4. Parent Topic Requiring Removal:
# PASSPORT_OVERSEAS_SERVICE

Decision:

`REMOVE_AS_FIRST_LEVEL_PARENT`

Reason:

"Overseas" describes the context/location of the applicant rather than
one unique information need.

For example:

"How do I apply for a new passport from abroad?"

Primary intent:

`PASSPORT_APPLICATION`

Context:

`overseas`

But:

"How do I reissue my passport from abroad?"

Primary intent:

`PASSPORT_REISSUE`

Context:

`overseas`

If `PASSPORT_OVERSEAS_SERVICE` remains a parent, the second query could
correctly belong to both:

`PASSPORT_REISSUE`

and:

`PASSPORT_OVERSEAS_SERVICE`

This creates parent-label ambiguity.

---

## Recommended treatment of overseas queries

Represent overseas workflow at the leaf level where necessary.

Possible future leaves:

Under `PASSPORT_APPLICATION`:

`PASSPORT_APPLICATION_OVERSEAS`

Under `PASSPORT_REISSUE`:

`PASSPORT_REISSUE_OVERSEAS`

Potential overseas document questions should remain under
`PASSPORT_DOCUMENTS`.

Therefore overseas location remains useful information without becoming
an overlapping top-level class.

---

# 5. Parent Topic Requiring Removal:
# PASSPORT_SPECIAL_CATEGORY

Decision:

`REMOVE_AS_FIRST_LEVEL_PARENT`

Reason:

Official or diplomatic status describes a passport/application category
rather than one consistent information need.

For example:

"How do I apply for an official passport?"

Primary intent:

`PASSPORT_APPLICATION`

But:

"What documents are required for an official passport?"

Primary intent:

`PASSPORT_DOCUMENTS`

A single `PASSPORT_SPECIAL_CATEGORY` parent would compete with both.

---

## Recommended treatment

Possible application leaf:

`PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`

Possible document leaf, if query volume justifies it:

`PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`

GO/NOC questions primarily concerning document requirements should
normally remain under `PASSPORT_DOCUMENTS`.

Do not create these leaves until query-volume and evidence review.

---

# 6. Cross-Cutting Attributes vs Intent Labels

The taxonomy must distinguish:

PRIMARY INTENT

from:

CONTEXTUAL ATTRIBUTE

Examples of primary intent:

- application;
- documents;
- payment;
- re-issue;
- status;
- account access.

Examples of contextual attributes:

- applying from abroad;
- official/diplomatic applicant;
- minor applicant;
- urgent delivery category.

Context may influence which detailed leaf is appropriate, but it should
not automatically become a competing parent class.

This principle will reduce hierarchical label ambiguity.

---

# 7. Recommended Revised Parent Structure

The Passport parent taxonomy should therefore use eight first-level
parents:

1. `PASSPORT_APPLICATION`
2. `PASSPORT_DOCUMENTS`
3. `PASSPORT_ONLINE_ACCOUNT`
4. `PASSPORT_APPOINTMENT_AND_ENROLMENT`
5. `PASSPORT_REISSUE`
6. `PASSPORT_FEES_AND_PAYMENT`
7. `PASSPORT_STATUS_AND_DELIVERY`
8. `PASSPORT_GENERAL_INFORMATION`

Remove as first-level parents:

`PASSPORT_OVERSEAS_SERVICE`

`PASSPORT_SPECIAL_CATEGORY`

Their useful concepts should later appear as specific query topics or
context inside the appropriate intent parent.

---

# 8. High-Risk Boundaries for Leaf Design

The leaf taxonomy must explicitly distinguish:

## Application vs re-issue

No previous passport / first passport:

`PASSPORT_APPLICATION`

Previously issued passport:

`PASSPORT_REISSUE`

---

## Application vs documents

"How do I apply?"

Application intent.

"What documents do I need?"

Document intent.

---

## Required documents vs missing documents

"What documents are required?"

is different from:

"I cannot provide one required document."

---

## Online application vs online account

"How do I apply online?"

is different from:

"I cannot log into my account."

---

## Account problem vs appointment problem

Both may occur on the same portal but represent different user goals.

---

## Re-issue vs changed information

Changed information may become a specific re-issue leaf.

Do not automatically create a separate parent.

---

## Application status vs delay

Checking current state is different from reporting abnormal waiting.

---

## Delay vs processing time

A delayed personal case is different from asking the normal expected
duration.

---

## Payment information vs payment failure

A general payment question is different from a transaction failure.

---

## Passport collection vs application-form printing

Collecting an issued passport is different from printing application
paperwork.

---

## Lost passport vs lost delivery slip

These represent different objects, different workflow stages and
different classifier intents.

---

# 9. Parent-Level Decision

Current 10-parent draft:

`STRUCTURALLY VALID`

Semantic parent separation:

`REFINEMENT REQUIRED`

Recommended parent count:

`8`

Parents retained:

`8`

Parents removed/reassigned:

`2`

Query-topic definition:

`NOT YET STARTED`

Parent review complete:

`YES, PENDING YAML REFINEMENT`

Shared contract:

`NOT FROZEN`

---

# 10. Next Action

Modify `taxonomy/passport.yaml` so that:

- `PASSPORT_OVERSEAS_SERVICE` is no longer a first-level parent;
- `PASSPORT_SPECIAL_CATEGORY` is no longer a first-level parent;
- useful overseas and special-category concepts are retained in
  descriptions/design rules for later leaf-topic consideration;
- the taxonomy records eight reviewed first-level parents.

Only after this refinement should Passport query-topic IDs be defined.