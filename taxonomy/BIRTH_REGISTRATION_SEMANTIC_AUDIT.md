# Birth Registration Semantic Taxonomy Audit

Owner: Prothom  
Service ID: `BIRTH_REGISTRATION`  
Taxonomy reviewed: `taxonomy/birth_registration.yaml`  
Taxonomy version: `0.1.0`

## Purpose

The structural validator confirms that the Birth Registration taxonomy
has valid YAML, unique IDs, one parent per leaf, required fields,
evidence statuses and inclusion/exclusion examples.

This audit checks a different question:

Can two annotators consistently decide which query topic should receive
a citizen query when neighboring topics are semantically similar?

The audit focuses on high-risk boundaries before pilot dataset
generation.

---

# Current Structure

Parents: 8

Query topics: 30

- BR_REGISTRATION: 13
- BR_CORRECTION: 7
- BR_APPLICATION_MANAGEMENT: 4
- BR_CERTIFICATE_ACCESS: 1
- BR_VERIFICATION: 2
- BR_CANCELLATION: 1
- BR_FEES_AND_PAYMENT: 1
- BR_GENERAL_INFORMATION: 1

---

# Semantic Decision Principle

Classification should represent the citizen's PRIMARY information need.

Words such as:

- online
- document
- fee
- status
- certificate
- correction
- OTP

must not determine the class by themselves.

The full semantic intent of the query determines the label.

When a procedural detail can be answered through retrieval without
requiring a separate stable classifier distinction, avoid unnecessary
label fragmentation.

---

# Boundary Audit

## 1. Registration Process
vs
Online Application

### Topics

- `BR_REGISTRATION_PROCESS`
- `BR_REGISTRATION_ONLINE_APPLICATION`

### Decision

KEEP SEPARATE.

`BR_REGISTRATION_PROCESS` is for general end-to-end registration
questions.

`BR_REGISTRATION_ONLINE_APPLICATION` requires an explicit online,
portal or remote-application focus.

### Examples

"জন্ম নিবন্ধন কীভাবে করব?"
→ `BR_REGISTRATION_PROCESS`

"অনলাইনে জন্ম নিবন্ধনের আবেদন কীভাবে করব?"
→ `BR_REGISTRATION_ONLINE_APPLICATION`

### Annotation rule

The word "application" alone does not imply online application.

Online/portal/home-based submission must be part of the user's actual
information need.

---

## 2. Registration Location Selection
vs
Address Information

### Topics

- `BR_REGISTRATION_LOCATION_SELECTION`
- `BR_REGISTRATION_ADDRESS_INFORMATION`

### Decision

KEEP SEPARATE.

Location selection asks which office, jurisdiction or registration basis
should handle the application.

Address information asks what address data should be entered into the
application.

### Examples

"কোন ইউনিয়ন পরিষদ থেকে জন্ম নিবন্ধন করব?"
→ `BR_REGISTRATION_LOCATION_SELECTION`

"বর্তমান ঠিকানার ঘরে কোন ঠিকানা দেব?"
→ `BR_REGISTRATION_ADDRESS_INFORMATION`

### Annotation rule

Choosing WHERE the application belongs is different from entering WHAT
address should appear in the form.

---

## 3. Domestic Location Selection
vs
Overseas / Embassy Registration

### Topics

- `BR_REGISTRATION_LOCATION_SELECTION`
- `BR_REGISTRATION_OVERSEAS_EMBASSY`

### Decision

KEEP SEPARATE.

Queries explicitly involving living abroad, a Bangladesh embassy,
mission or overseas application route should use the embassy topic.

Ordinary local jurisdiction questions remain location selection.

### Examples

"আমি বিদেশে থাকি, embassy দিয়ে birth registration করা যাবে?"
→ `BR_REGISTRATION_OVERSEAS_EMBASSY`

"আমার স্থায়ী ঠিকানা খুলনা, কোন অফিস থেকে আবেদন করব?"
→ `BR_REGISTRATION_LOCATION_SELECTION`

---

## 4. Registered Person Information
vs
Parent Information

### Topics

- `BR_REGISTRATION_PERSON_INFORMATION`
- `BR_REGISTRATION_PARENT_INFORMATION`

### Decision

KEEP SEPARATE.

The first concerns information about the person whose birth is being
registered.

The second concerns information about the person's father or mother.

### Examples

"শিশুর English name দিতে হবে?"
→ `BR_REGISTRATION_PERSON_INFORMATION`

"বাবার জন্ম নিবন্ধন নম্বর দিতে হবে?"
→ `BR_REGISTRATION_PARENT_INFORMATION`

---

## 5. Parent Information
vs
Applicant / Guardian Relationship

### Topics

- `BR_REGISTRATION_PARENT_INFORMATION`
- `BR_REGISTRATION_APPLICANT_RELATION`

### Decision

KEEP SEPARATE.

Parent information concerns data about father/mother.

Applicant relation concerns WHO is allowed to submit or attest the
application and what relationship should be selected.

### Examples

"মায়ের কী তথ্য দিতে হবে?"
→ `BR_REGISTRATION_PARENT_INFORMATION`

"মামা কি শিশুর হয়ে আবেদন করতে পারবে?"
→ `BR_REGISTRATION_APPLICANT_RELATION`

---

## 6. Required Documents
vs
Missing Documents

### Topics

- `BR_REGISTRATION_REQUIRED_DOCUMENTS`
- `BR_REGISTRATION_MISSING_DOCUMENTS`

### Decision

KEEP PROVISIONALLY SEPARATE.

Required-documents queries ask what evidence is normally required.

Missing-document queries already know or encounter a requirement but
cannot provide one of the documents.

### Examples

"জন্ম নিবন্ধনের জন্য কী কী কাগজ লাগে?"
→ `BR_REGISTRATION_REQUIRED_DOCUMENTS`

"একটা required document আমার নেই, এখন কী করব?"
→ `BR_REGISTRATION_MISSING_DOCUMENTS`

### Risk

`BR_REGISTRATION_MISSING_DOCUMENTS` may prove too sparse for a separate
classifier leaf.

### Pilot requirement

Keep this topic only if reviewed pilot queries show a consistent
semantic pattern distinct from general document requirements.

Status:
`NEEDS_PILOT_VALIDATION`

---

## 7. OTP Not Received
vs
OTP Verification Failure

### Topics

- `BR_REGISTRATION_OTP_NOT_RECEIVED`
- `BR_REGISTRATION_OTP_VERIFICATION`

### Decision

KEEP PROVISIONALLY SEPARATE.

Not received:
the code never arrives.

Verification failure:
the code arrives but is rejected or verification does not complete.

### Examples

"OTP আসে নাই"
→ `BR_REGISTRATION_OTP_NOT_RECEIVED`

"OTP পেয়েছি কিন্তু code accept করছে না"
→ `BR_REGISTRATION_OTP_VERIFICATION`

### Pilot requirement

Generate hard boundary examples because short queries such as
"OTP problem" are genuinely ambiguous.

Status:
`NEEDS_PILOT_VALIDATION`

---

## 8. Submission Rules
vs
Application Status

### Topics

- `BR_REGISTRATION_SUBMISSION_RULES`
- `BR_APPLICATION_STATUS`

### Decision

KEEP SEPARATE, BUT REFINE SUBMISSION-RULE WORDING.

Submission rules should concern:

- final submission;
- whether submitted data can still be edited;
- consequences of confirming/submitting the form.

Application status concerns progress AFTER submission.

### Examples

"submit করার পরে form edit করতে পারব?"
→ `BR_REGISTRATION_SUBMISSION_RULES`

"submit করেছি, application approve হয়েছে?"
→ `BR_APPLICATION_STATUS`

### Required refinement

The current include example:

"What happens after I press submit?"

is too broad and can overlap with application status or processing.

It should be replaced during the post-audit taxonomy cleanup with a
more specific edit/finality example.

Status:
`MINOR_TAXONOMY_REFINEMENT_REQUIRED`

---

## 9. Correction Process
vs
Specific Correction Field

### Topics

- `BR_CORRECTION_PROCESS`
- field-specific correction topics

### Decision

KEEP SEPARATE.

General correction questions without a target field use
`BR_CORRECTION_PROCESS`.

Once the query clearly identifies the incorrect field, classify by the
field.

### Examples

"জন্ম নিবন্ধন সংশোধন করব কীভাবে?"
→ `BR_CORRECTION_PROCESS`

"জন্ম নিবন্ধনে আমার নাম ভুল"
→ `BR_CORRECTION_NAME`

"জন্ম তারিখ ভুল"
→ `BR_CORRECTION_DOB`

### Annotation rule

Specific field beats general correction process.

---

## 10. Own Name Correction
vs
Parent Information Correction

### Topics

- `BR_CORRECTION_NAME`
- `BR_CORRECTION_PARENT_INFORMATION`

### Decision

KEEP SEPARATE.

### Examples

"আমার নামের spelling ভুল"
→ `BR_CORRECTION_NAME`

"আমার বাবার নামের spelling ভুল"
→ `BR_CORRECTION_PARENT_INFORMATION`

Relationship words must be preserved during preprocessing because they
can determine the intent.

---

## 11. Parent Information Correction
vs
Parent BRN Mapping

### Topics

- `BR_CORRECTION_PARENT_INFORMATION`
- `BR_CORRECTION_PARENT_BRN_MAPPING`

### Decision

KEEP PROVISIONALLY SEPARATE.

Parent-information correction means the parent data itself is wrong.

BRN mapping means the relevant parent record exists but the parent's
Birth Registration Number/linkage is missing or not reflected in the
child's record.

### Examples

"আমার মায়ের নাম ভুল"
→ `BR_CORRECTION_PARENT_INFORMATION`

"বাবার BRN আছে কিন্তু আমার birth registration-এর সাথে link করা নেই"
→ `BR_CORRECTION_PARENT_BRN_MAPPING`

### Risk

BRN mapping may prove to be too procedural or too rare to justify a
dedicated classifier leaf.

### Required refinement

Change its effective evidence status to:

`needs_query_pilot`

during post-audit cleanup.

Status:
`MINOR_TAXONOMY_REFINEMENT_REQUIRED`

---

## 12. Registration Address
vs
Correction Address

### Topics

- `BR_REGISTRATION_ADDRESS_INFORMATION`
- `BR_CORRECTION_ADDRESS`

### Decision

KEEP SEPARATE.

The first happens during a new application.

The second changes information already stored in an existing birth
record.

### Examples

"নতুন application-এ permanent address কী দেব?"
→ `BR_REGISTRATION_ADDRESS_INFORMATION`

"আমার certificate-এর permanent address ভুল"
→ `BR_CORRECTION_ADDRESS`

---

## 13. Application Status
vs
Application Delay
vs
Processing Time

### Topics

- `BR_APPLICATION_STATUS`
- `BR_APPLICATION_DELAY`
- `BR_APPLICATION_PROCESSING_TIME`

### Decision

KEEP SEPARATE.

Status asks about the current state of a particular application.

Delay expresses that an existing application has taken longer than
expected.

Processing time asks about the normal expected duration in general.

### Examples

"আমার application status কী?"
→ `BR_APPLICATION_STATUS`

"দুই মাস ধরে pending, কী করব?"
→ `BR_APPLICATION_DELAY`

"সাধারণত birth registration হতে কতদিন লাগে?"
→ `BR_APPLICATION_PROCESSING_TIME`

### Important evidence rule

`BR_APPLICATION_PROCESSING_TIME` may recognize the question even while
the actual official duration remains unverified.

The classifier taxonomy must not contain an invented time value.

Status:
`KEEP_WITH_SOURCE_REVIEW_REQUIRED`

---

## 14. Application Print
vs
Certificate Reprint

### Topics

- `BR_APPLICATION_PRINT`
- `BR_CERTIFICATE_REPRINT`

### Decision

KEEP SEPARATE.

An application print is a copy of the submitted application form.

Certificate reprint is another copy of an already issued birth
registration certificate.

### Examples

"submit করা application form print করব কীভাবে?"
→ `BR_APPLICATION_PRINT`

"certificate-এর আরেকটা copy চাই"
→ `BR_CERTIFICATE_REPRINT`

This boundary is mandatory.

---

## 15. Certificate Reprint
vs
Correction

### Topics

- `BR_CERTIFICATE_REPRINT`
- `BR_CORRECTION_*`

### Decision

KEEP SEPARATE.

If information is wrong and the citizen wants it changed, classify as
correction.

If the information is already correct and another certificate copy is
wanted, classify as reprint.

### Examples

"certificate হারিয়েছে, আরেকটা copy চাই"
→ `BR_CERTIFICATE_REPRINT`

"certificate আছে কিন্তু নাম ভুল"
→ `BR_CORRECTION_NAME`

---

## 16. Verification
vs
Application Status

### Topics

- `BR_VERIFICATION_RECORD`
- `BR_APPLICATION_STATUS`

### Decision

KEEP SEPARATE.

Verification concerns an existing registered record.

Application status concerns an application that is still moving through
the registration process.

### Examples

"BRN দিয়ে record verify করব কীভাবে?"
→ `BR_VERIFICATION_RECORD`

"আমার আবেদন approve হয়েছে?"
→ `BR_APPLICATION_STATUS`

---

## 17. Verification
vs
Verification Failure

### Topics

- `BR_VERIFICATION_RECORD`
- `BR_VERIFICATION_FAILURE`

### Decision

KEEP PROVISIONALLY SEPARATE.

Verification asks how to perform the check.

Verification failure describes an attempted verification that did not
produce the expected record/result.

### Examples

"কীভাবে birth registration verify করব?"
→ `BR_VERIFICATION_RECORD`

"BRN আর DOB দিলেও result আসে না"
→ `BR_VERIFICATION_FAILURE`

### Pilot requirement

Include hard examples such as:

- "verify হচ্ছে না"
- "record পাওয়া যাচ্ছে না"
- "verification error"

Status:
`NEEDS_PILOT_VALIDATION`

---

## 18. Verification Failure
vs
Information Correction

### Decision

KEEP SEPARATE.

A failed lookup is not automatically evidence that the stored record is
incorrect.

### Examples

"record পাওয়া যাচ্ছে না"
→ `BR_VERIFICATION_FAILURE`

"record পাওয়া যাচ্ছে কিন্তু DOB ভুল"
→ `BR_CORRECTION_DOB`

---

## 19. Cancellation
vs
Correction

### Topics

- `BR_CANCELLATION_PROCESS`
- `BR_CORRECTION_*`

### Decision

KEEP SEPARATE.

Correction preserves the registration record and changes information.

Cancellation asks to cancel the certificate/record through the official
cancellation workflow.

### Examples

"তথ্য ভুল, ঠিক করতে চাই"
→ correction topic

"সনদ বাতিলের আবেদন করতে চাই"
→ `BR_CANCELLATION_PROCESS`

### Evidence limitation

No additional cancellation subtopics should be created until official
procedural evidence and pilot citizen-query evidence support them.

---

## 20. Fee Information
vs
Underlying Service Intent

### Topic

`BR_FEES_INFORMATION`

### Decision

Primary information need determines the label.

### Examples

"জন্ম নিবন্ধনের fee কত?"
→ `BR_FEES_INFORMATION`

"জন্ম নিবন্ধনের আবেদন কীভাবে করব?"
→ `BR_REGISTRATION_PROCESS`

"correction করতে কত টাকা লাগে?"
→ `BR_FEES_INFORMATION`

"correction কীভাবে করব?"
→ `BR_CORRECTION_PROCESS`

### Rule

A fee question is classified as fee information even when it names a
specific Birth Registration workflow.

The original query provides the service-specific context that retrieval
can use to find the relevant fee information.

---

## 21. General Information
vs
Registration Process

### Topics

- `BR_GENERAL_INFORMATION`
- `BR_REGISTRATION_PROCESS`

### Decision

KEEP SEPARATE.

General information asks what Birth Registration is, why it matters or
where broad guidance exists.

Registration process asks how to actually register a birth.

### Examples

"জন্ম নিবন্ধন কী?"
→ `BR_GENERAL_INFORMATION`

"জন্ম নিবন্ধন করব কীভাবে?"
→ `BR_REGISTRATION_PROCESS`

---

## 22. General Information
vs
OOD / Low Confidence

### Decision

MANDATORY SEPARATION.

`BR_GENERAL_INFORMATION` is a real semantic topic.

It must never be used as a fallback when the classifier does not
understand the query.

### Examples

"Birth registration কেন দরকার?"
→ `BR_GENERAL_INFORMATION`

"আমার passport renew করতে চাই"
→ not Birth Registration general information

The latter belongs to another service.

A completely unsupported query should be handled through service
classification, confidence thresholds or OOD handling.

---

## 23. Birth Registration
vs
NID

### Decision

CROSS-SERVICE BOUNDARY REQUIRED.

Queries may contain both identity-related concepts.

### Examples

"জন্ম নিবন্ধনের নাম ভুল"
→ Birth Registration correction

"NID-এর নাম ভুল"
→ NID correction

"NID করতে birth certificate লাগবে?"
→ primary service likely NID because the citizen's requested goal is an
NID workflow, while the birth certificate is a requirement/context item.

This type of cross-service query should be included in later hard
evaluation examples.

---

# Topics Requiring Pilot Validation

The following leaves are semantically plausible but require deliberate
pilot evidence before being considered fully stable:

1. `BR_REGISTRATION_MISSING_DOCUMENTS`
2. `BR_REGISTRATION_OTP_VERIFICATION`
3. `BR_CORRECTION_PARENT_BRN_MAPPING`
4. `BR_APPLICATION_DELAY`
5. `BR_VERIFICATION_FAILURE`
6. `BR_GENERAL_INFORMATION`

Additional source review remains required for:

- `BR_APPLICATION_PROCESSING_TIME`

---

# Required Minor Taxonomy Cleanup

Before marking the taxonomy ready, perform these two changes only:

## Change 1

For:

`BR_REGISTRATION_SUBMISSION_RULES`

replace the overly broad include example:

"What happens after I press submit?"

with a submission-finality example such as:

"Does submitting the application make the information final?"

This prevents semantic overlap with application status and processing.

## Change 2

For:

`BR_CORRECTION_PARENT_BRN_MAPPING`

add:

`evidence_status: "needs_query_pilot"`

The workflow itself is supported, but a distinct classifier class still
needs citizen-query evidence.

---

# Labels Not Recommended at This Stage

Do not currently create separate leaves for:

- registration birth-place address
- registration permanent address
- registration present address
- correction birth-place address
- correction permanent address
- correction present address
- certificate reprint documents
- certificate reprint status
- certificate reprint problems
- cancellation eligibility
- cancellation documents
- cancellation status
- payment method
- payment status
- payment receipt
- refund
- search by name
- search by parent
- search by address
- FAQ
- law
- rules
- guideline

These may be retrieval-level details or may require additional evidence.

---

# Dataset Generation Rules Derived From Audit

When the Birth Registration pilot dataset is created:

1. Every leaf should receive reviewed examples.
2. High-risk neighboring leaves must receive contrastive examples.
3. Short ambiguous queries should be included.
4. Formal Bangla should be included.
5. Informal Bangla should be included.
6. Banglish should be included.
7. Bangla-English code-mixed queries should be included.
8. Natural typos/noise should be included.
9. Cross-service hard negatives should be included.
10. OOD examples should be included separately.
11. Query paraphrases must share a `parent_query_id`.
12. Query families must not later be split across train/validation/test.
13. Synthetic examples must never be marked as REAL.
14. Queries containing actual sensitive values must be marked for
    privacy handling.
15. Concept mentions without an actual sensitive value must not
    automatically be marked privacy-positive.

---

# Semantic Audit Result

Result:

`PASS_WITH_MINOR_REFINEMENTS_AND_PILOT_VALIDATION`

Interpretation:

- The eight-parent structure is acceptable.
- The 30-leaf structure is sufficiently coherent to proceed.
- No parent IDs should be renamed.
- No leaf IDs should currently be deleted or renamed.
- Two minor taxonomy edits are required before review-ready status.
- Several low-evidence leaves require reviewed pilot examples.
- Processing-time information requires further source review.
- Large-scale dataset generation must not begin yet.
- The shared six-service contract remains unfrozen.

The next step is to apply the two explicitly identified taxonomy
refinements, rerun the structural validator and mark the Birth
Registration taxonomy as reviewed enough to begin pilot annotation.
