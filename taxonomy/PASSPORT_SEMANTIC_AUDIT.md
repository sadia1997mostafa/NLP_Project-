# Passport Taxonomy Semantic Audit

## NagorikSheba AI

**Service:** PASSPORT  
**Taxonomy file:** `taxonomy/passport.yaml`  
**Taxonomy version reviewed:** `0.1.9`  
**Parent topics:** 8  
**Query-topic leaves:** 56  
**Structural validation:** PASS  
**Semantic audit status:** PASS WITH PILOT-REVIEW FLAGS  
**Shared-contract readiness:** NOT YET  
**Pilot annotation readiness:** YES, after taxonomy metadata is updated

---

# 1. Purpose

This audit reviews the semantic quality of the Passport intent taxonomy after
structural validation.

The purpose is not to verify changing government facts such as fees,
processing durations, office addresses or current payment providers.

The purpose is to determine whether:

1. parent topics represent coherent citizen information needs;
2. individual query-topic leaves represent distinguishable intents;
3. neighboring leaves have sufficiently clear boundaries;
4. broad labels are prevented from becoming classifier fallback classes;
5. the hierarchy is suitable for controlled pilot annotation;
6. uncertain or potentially low-volume leaves are explicitly flagged for
   pilot review rather than silently removed.

The taxonomy reviewed contains:

- 8 parent topics;
- 56 query-topic leaves;
- explicit descriptions;
- inclusion examples;
- exclusion examples;
- evidence-status metadata;
- design rules defining important boundaries.

---

# 2. Audit Decision

## Overall result

**PASS WITH PILOT-REVIEW FLAGS**

The current Passport taxonomy is semantically coherent enough to proceed to
pilot annotation.

No mandatory parent-level restructuring is required before the pilot.

No mandatory leaf merge is required before the pilot.

However, several leaves must be treated as experimental during pilot
annotation because either:

- their expected citizen-query volume is uncertain;
- their wording may overlap with neighboring intents;
- they are deliberately broad operational problem labels;
- their usefulness as separate classifier classes should be confirmed with
  actual query examples.

The pilot must therefore test whether these leaves receive enough naturally
distinguishable examples to justify remaining separate.

The taxonomy must **not** be frozen into the shared contract yet.

---

# 3. Parent-Level Review

## 3.1 PASSPORT_APPLICATION

### Decision

**PASS**

This parent captures new or first-passport application intents.

Current leaves:

1. `PASSPORT_APPLICATION_PROCESS`
2. `PASSPORT_APPLICATION_ONLINE`
3. `PASSPORT_APPLICATION_OFFICE_SELECTION`
4. `PASSPORT_APPLICATION_INFORMATION`
5. `PASSPORT_APPLICATION_PASSPORT_OPTIONS`
6. `PASSPORT_APPLICATION_OVERSEAS`
7. `PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`

### Semantic assessment

The parent is coherent because all leaves concern establishing or preparing a
new passport application rather than maintaining an existing passport.

The most important boundaries are sufficiently explicit.

### Application process vs online application

`PASSPORT_APPLICATION_PROCESS` represents the general end-to-end information
need:

> How do I apply for a passport?

`PASSPORT_APPLICATION_ONLINE` represents the narrower channel-specific intent:

> How do I submit the passport application online?

These should remain separate because citizens may understand that they need a
passport but either ask for the overall process or specifically ask about the
online workflow.

### Application office selection vs enrolment location

`PASSPORT_APPLICATION_OFFICE_SELECTION` is about selecting the responsible
office while setting up the application.

`PASSPORT_ENROLMENT_LOCATION` is about where the applicant must physically go
for enrolment.

The distinction is semantically meaningful and should remain explicit.

### Application information vs documents

`PASSPORT_APPLICATION_INFORMATION` concerns values or information entered in
the application.

`PASSPORT_DOCUMENTS_*` concerns evidence or documents used to support the
application.

Example distinction:

- "What information do I enter?" → application information.
- "What documents do I need?" → documents.

### Passport options vs fees/delivery

`PASSPORT_APPLICATION_PASSPORT_OPTIONS` represents choices such as passport
configuration or available options.

It must not absorb:

- fee questions;
- processing-time questions;
- delivery-category pricing questions.

Those belong under the fee or status/delivery parents.

### Overseas application

`PASSPORT_APPLICATION_OVERSEAS` is correctly modeled as a leaf rather than a
first-level parent.

"Overseas" describes the context in which the application is made, while the
primary intent remains new-passport application.

### Official/diplomatic application

`PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC` is semantically distinguishable
from ordinary application questions, but expected query volume is uncertain.

**Pilot flag:** `QUERY_VOLUME_REVIEW`

The pilot should determine whether this intent has sufficient independent
citizen-query volume to justify a dedicated classifier leaf.

---

# 4. PASSPORT_DOCUMENTS

## Decision

**PASS WITH PILOT-REVIEW FLAG**

Current leaves:

1. `PASSPORT_DOCUMENTS_REQUIRED`
2. `PASSPORT_DOCUMENTS_NID_REQUIREMENT`
3. `PASSPORT_DOCUMENTS_BIRTH_REGISTRATION_REQUIREMENT`
4. `PASSPORT_DOCUMENTS_PREVIOUS_PASSPORT`
5. `PASSPORT_DOCUMENTS_MINOR_APPLICANT`
6. `PASSPORT_DOCUMENTS_ENROLMENT`
7. `PASSPORT_DOCUMENTS_MISSING`
8. `PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`

The parent represents documentary evidence rather than the operational process
of applying, paying, enrolling or collecting.

### General documents vs NID requirement

These are meaningfully different.

- "What documents are required?" → `PASSPORT_DOCUMENTS_REQUIRED`
- "Do I need an NID?" → `PASSPORT_DOCUMENTS_NID_REQUIREMENT`

The explicit named-document intent should take precedence over the general
document label.

### NID vs Birth Registration

The two leaves are justified because citizens frequently refer directly to one
identity document.

They should remain separate at least through the pilot.

### Previous passport

`PASSPORT_DOCUMENTS_PREVIOUS_PASSPORT` is specifically about whether the old
or existing passport must be provided as supporting evidence.

It must remain distinct from the actual re-issue process.

Example:

- "Do I need my old passport?" → documents.
- "How do I reissue my passport?" → reissue.

### Minor applicant documents

This leaf has a clear applicant-category focus and should remain separate from
the generic document list.

### Enrolment documents

`PASSPORT_DOCUMENTS_ENROLMENT` should remain separate from:

- appointment requirements;
- biometric procedure;
- general application document requirements.

The main decision criterion is whether the citizen is asking **which papers to
bring**.

### Missing document

`PASSPORT_DOCUMENTS_MISSING` is semantically useful but broad.

It represents:

> I know or believe a required supporting document is unavailable.

It must not become the label for:

- a lost passport;
- a lost delivery slip;
- an unrelated missing government document.

**Pilot flag:** `BOUNDARY_AND_VOLUME_REVIEW`

The pilot should verify that citizens produce enough examples where the main
need is specifically "required supporting document unavailable."

### Official/diplomatic documents

The distinction from official/diplomatic application process is valid:

- how to apply → application;
- what GO/NOC/supporting evidence is required → documents.

However, query volume remains uncertain.

**Pilot flag:** `QUERY_VOLUME_REVIEW`

---

# 5. PASSPORT_ONLINE_ACCOUNT

## Decision

**PASS WITH PILOT-REVIEW FLAG**

Current leaves:

1. `PASSPORT_ONLINE_ACCOUNT_REGISTRATION`
2. `PASSPORT_ONLINE_ACCOUNT_LOGIN`
3. `PASSPORT_ONLINE_ACCOUNT_PASSWORD_RESET`
4. `PASSPORT_ONLINE_ACCOUNT_ACTIVATION`
5. `PASSPORT_ONLINE_ACCOUNT_ACTIVATION_EMAIL_NOT_RECEIVED`
6. `PASSPORT_ONLINE_ACCOUNT_EMAIL_CHANGE`
7. `PASSPORT_ONLINE_ACCOUNT_MOBILE_CHANGE`
8. `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM`

### Registration vs application

Account creation must remain separate from passport application.

Example:

- "How do I create an account?" → account registration.
- "How do I apply online?" → online application.

### Login vs access failure

These represent different information needs.

Normal login:

> Where/how do I log in?

Access problem:

> I tried to access my account but cannot.

The access-problem label should only be used when no narrower known cause is
stated.

### Password reset

Forgotten password and password reset are correctly grouped because both map to
the same actionable user intent: password recovery.

### Activation vs activation email missing

These should remain separate.

- "How do I activate?" → activation.
- "I never got the activation email." → activation-email-not-received.

### Email change vs mobile change

The two registered-contact fields are sufficiently explicit and should remain
separate.

### General account access problem

`PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM` is intentionally broader than the
other account leaves.

It must not absorb identifiable cases such as:

- forgotten password;
- activation email missing;
- email update;
- mobile update.

**Pilot flag:** `BOUNDARY_REVIEW`

The pilot should test whether generic account-access failures can be reliably
distinguished from the narrower account leaves.

---

# 6. PASSPORT_APPOINTMENT_AND_ENROLMENT

## Decision

**PASS WITH PILOT-REVIEW FLAG**

Current leaves:

1. `PASSPORT_APPOINTMENT_SCHEDULING`
2. `PASSPORT_APPOINTMENT_DATE`
3. `PASSPORT_APPOINTMENT_PROBLEM`
4. `PASSPORT_APPOINTMENT_REQUIREMENTS`
5. `PASSPORT_ENROLMENT_PROCESS`
6. `PASSPORT_ENROLMENT_LOCATION`
7. `PASSPORT_ENROLMENT_BIOMETRICS`

### Scheduling vs appointment date

These should remain separate.

Scheduling:

> How do I obtain/book an appointment?

Date:

> When is the appointment already assigned to me?

### Appointment problem

`PASSPORT_APPOINTMENT_PROBLEM` is a generic problem intent inside a specific
workflow stage.

It is useful only when the problem cannot be expressed using another narrower
appointment label.

It must not absorb:

- account failures;
- application status;
- payment failures;
- enrolment location;
- appointment-date lookup.

**Pilot flag:** `BOUNDARY_AND_VOLUME_REVIEW`

If pilot examples consistently map to more specific labels, this leaf should
later be considered for removal.

### Appointment requirements vs enrolment documents

These are close but distinguishable.

Appointment requirements:

> What do I need to do/prepare before attending?

Enrolment documents:

> Which documents/papers should I bring?

During annotation, document-focused queries must take the document label.

### Enrolment process vs biometrics

General physical workflow:

> What happens during enrolment?

Specific biometric focus:

> What biometrics are taken?

The biometric-specific label should take precedence whenever biometric capture
is the central information need.

### Enrolment location vs office selection

This distinction remains valid:

- office selection → application routing;
- enrolment location → physical attendance location.

---

# 7. PASSPORT_REISSUE

## Decision

**PASS**

Current leaves:

1. `PASSPORT_REISSUE_PROCESS`
2. `PASSPORT_REISSUE_EXPIRY`
3. `PASSPORT_REISSUE_WITH_INFORMATION_CHANGE`
4. `PASSPORT_REISSUE_LOST`
5. `PASSPORT_REISSUE_STOLEN`
6. `PASSPORT_REISSUE_DAMAGED`
7. `PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE`
8. `PASSPORT_REISSUE_OVERSEAS`

### General reissue vs explicit reason

The general reissue leaf should only be used when the user does not give a more
specific reason.

Specific reasons take precedence:

- expiry;
- information change;
- loss;
- theft;
- damage;
- overseas context.

### Expiry

Expiry represents a clear and common reason for reissue and is semantically
distinct from physical loss or damage.

### Information change

This should remain separate because the user's goal includes modifying
passport-record information while obtaining another passport.

It must not absorb changes to:

- portal email;
- portal mobile number;
- unrelated NID/Birth Registration records.

### Lost vs stolen vs damaged

These are sufficiently distinguishable because the condition of the previous
passport differs.

They should remain separate through pilot annotation.

The labels may later be reconsidered if actual query data shows severe class
imbalance, but no semantic merge is currently required.

### Without information change

`PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE` is close to the generic reissue
label but still distinguishable when the user explicitly states that existing
information will remain unchanged.

Rule:

- Explicit "same/no change" semantics → `PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE`
- No stated reason or information-change condition → `PASSPORT_REISSUE_PROCESS`

This boundary must be preserved during annotation.

### Overseas reissue

This remains correctly modeled under reissue.

The user's primary intent is reissue; being outside Bangladesh is the workflow
context.

---

# 8. PASSPORT_FEES_AND_PAYMENT

## Decision

**PASS**

Current leaves:

1. `PASSPORT_FEES_INFORMATION`
2. `PASSPORT_PAYMENT_METHOD`
3. `PASSPORT_PAYMENT_CONFIRMATION`
4. `PASSPORT_PAYMENT_FAILURE`
5. `PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED`
6. `PASSPORT_PAYMENT_REFUND`
7. `PASSPORT_PAYMENT_RECEIPT`
8. `PASSPORT_FEES_DELIVERY_CATEGORY`

### General fee vs delivery-category fee

These should remain separate.

General:

> How much does a passport cost?

Category-specific:

> How much is express service?

Exact monetary values must not be encoded into classifier semantics.

### Payment method

Online and offline payment should remain method variants rather than separate
intent classes unless real query data later demonstrates a meaningful need for
separation.

### Confirmation vs failure

These are distinct:

- confirmation → did the payment succeed?
- failure → the transaction failed.

### Failed vs deducted-but-failed

The narrower label should take precedence whenever the user explicitly says
money was deducted or charged.

### Deducted-but-failed vs refund

These represent different conversational goals.

Initial problem:

> Money was deducted but payment failed.

→ `PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED`

Recovery goal:

> How/when do I get the money back?

→ `PASSPORT_PAYMENT_REFUND`

### Receipt

Proof-of-payment retrieval is semantically distinct from transaction
confirmation.

It must also remain distinct from the passport delivery slip.

---

# 9. PASSPORT_STATUS_AND_DELIVERY

## Decision

**PASS WITH PILOT-REVIEW FLAG**

Current leaves:

1. `PASSPORT_APPLICATION_STATUS`
2. `PASSPORT_APPLICATION_DELAY`
3. `PASSPORT_PROCESSING_TIME`
4. `PASSPORT_DELIVERY_CATEGORY`
5. `PASSPORT_READY_FOR_COLLECTION`
6. `PASSPORT_COLLECTION`
7. `PASSPORT_DELIVERY_SLIP_LOST`

### Status vs delay

Status asks:

> What stage is the application currently in?

Delay states or implies:

> My application is taking unusually long.

These should remain separate.

### Processing time vs delay

Processing time is a general expectation:

> How long does the process normally take?

Delay describes a specific case:

> Mine has been taking too long.

This is an important distinction and should be strongly represented in pilot
examples.

### Application delay

Although semantically valid, this label may overlap with status wording when
citizens say:

> My application is still pending.

Annotation must determine whether the user is simply asking the current status
or explicitly expressing abnormal delay.

**Pilot flag:** `BOUNDARY_REVIEW`

### Delivery category vs category fee

Category:

> What is express service?

Fee:

> How much does express service cost?

These must remain separate.

### Ready for collection vs collection

These represent sequential but different information needs.

Ready:

> Can I collect it yet?

Collection:

> How/where do I collect it?

### Lost delivery slip

The missing object is the collection/delivery slip, not the passport.

This must remain distinct from:

- `PASSPORT_REISSUE_LOST`
- `PASSPORT_PAYMENT_RECEIPT`

---

# 10. PASSPORT_GENERAL_INFORMATION

## Decision

**PASS WITH STRONG PILOT REVIEW**

Current leaves:

1. `PASSPORT_GENERAL_EPASSPORT_INFORMATION`
2. `PASSPORT_GENERAL_NEW_VS_REISSUE`
3. `PASSPORT_GENERAL_SERVICE_GUIDANCE`

General-information intents are the highest-risk part of the taxonomy because
broad labels can become classifier catch-all categories.

They must therefore remain tightly constrained.

### General e-Passport information

This leaf is explanatory rather than transactional.

Appropriate:

> What is an e-Passport?

Not appropriate:

> How do I apply?

The latter belongs to the application parent.

### New vs reissue guidance

This is a legitimate decision-support intent.

It applies only when the citizen is uncertain which workflow applies.

Example:

> I had a passport before. Should I choose new or reissue?

Once the user's workflow is already clear, the specific application or reissue
leaf must take precedence.

### General service guidance

This is the most potentially dangerous fallback label in the taxonomy.

It may only represent genuinely broad orientation queries such as:

> What passport services can you help with?

It must never be assigned merely because:

- the classifier is uncertain;
- the query is unsupported;
- no known leaf scores highly;
- the query concerns another government service.

Those cases must later be handled through confidence and OOD logic.

**Pilot flag:** `STRONG_BOUNDARY_AND_VOLUME_REVIEW`

If real or carefully simulated pilot queries do not establish a coherent class,
this leaf should be removed rather than used as a fallback.

---

# 11. Cross-Parent Confusion Audit

The following neighboring intents require special attention during annotation.

| Intent A | Intent B | Primary distinction | Audit decision |
|---|---|---|---|
| `PASSPORT_APPLICATION_PROCESS` | `PASSPORT_APPLICATION_ONLINE` | General process vs specifically online submission | Keep separate |
| `PASSPORT_APPLICATION_ONLINE` | `PASSPORT_ONLINE_ACCOUNT_REGISTRATION` | Application transaction vs portal account creation | Keep separate |
| `PASSPORT_APPLICATION_INFORMATION` | `PASSPORT_DOCUMENTS_REQUIRED` | Information entered vs evidence supplied | Keep separate |
| `PASSPORT_APPLICATION_OFFICE_SELECTION` | `PASSPORT_ENROLMENT_LOCATION` | Application routing vs physical enrolment attendance | Keep separate |
| `PASSPORT_DOCUMENTS_REQUIRED` | `PASSPORT_DOCUMENTS_ENROLMENT` | General document requirements vs enrolment-day documents | Keep separate |
| `PASSPORT_DOCUMENTS_PREVIOUS_PASSPORT` | `PASSPORT_REISSUE_PROCESS` | Old passport as evidence vs reissue workflow | Keep separate |
| `PASSPORT_ONLINE_ACCOUNT_LOGIN` | `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM` | Normal login instructions vs unsuccessful access | Keep separate; pilot review generic problem leaf |
| `PASSPORT_APPOINTMENT_SCHEDULING` | `PASSPORT_APPOINTMENT_DATE` | Obtain appointment vs inspect assigned appointment | Keep separate |
| `PASSPORT_APPOINTMENT_REQUIREMENTS` | `PASSPORT_DOCUMENTS_ENROLMENT` | Attendance preparation vs paperwork | Keep separate |
| `PASSPORT_ENROLMENT_PROCESS` | `PASSPORT_ENROLMENT_BIOMETRICS` | Overall enrolment vs biometric-specific stage | Keep separate |
| `PASSPORT_REISSUE_PROCESS` | `PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE` | Unspecified general reissue vs explicit unchanged details | Keep separate; monitor pilot |
| `PASSPORT_REISSUE_LOST` | `PASSPORT_DELIVERY_SLIP_LOST` | Passport missing vs collection slip missing | Keep separate |
| `PASSPORT_PAYMENT_CONFIRMATION` | `PASSPORT_PAYMENT_FAILURE` | Uncertain success vs known failure | Keep separate |
| `PASSPORT_PAYMENT_FAILURE` | `PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED` | Generic failure vs failure after deduction | Keep separate |
| `PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED` | `PASSPORT_PAYMENT_REFUND` | Transaction problem vs money-recovery request | Keep separate |
| `PASSPORT_PAYMENT_RECEIPT` | `PASSPORT_DELIVERY_SLIP_LOST` | Payment proof vs collection document | Keep separate |
| `PASSPORT_FEES_INFORMATION` | `PASSPORT_FEES_DELIVERY_CATEGORY` | General fee vs service-category-specific fee | Keep separate |
| `PASSPORT_APPLICATION_STATUS` | `PASSPORT_APPLICATION_DELAY` | Current state vs abnormal-duration complaint | Keep separate; pilot review |
| `PASSPORT_APPLICATION_DELAY` | `PASSPORT_PROCESSING_TIME` | Specific delayed case vs normal expected duration | Keep separate |
| `PASSPORT_DELIVERY_CATEGORY` | `PASSPORT_FEES_DELIVERY_CATEGORY` | Service category vs price of category | Keep separate |
| `PASSPORT_READY_FOR_COLLECTION` | `PASSPORT_COLLECTION` | Whether ready vs how/where to collect | Keep separate |
| `PASSPORT_GENERAL_NEW_VS_REISSUE` | application/reissue leaves | Workflow uncertainty vs already-known workflow | Keep separate |
| `PASSPORT_GENERAL_SERVICE_GUIDANCE` | all operational leaves | Broad orientation vs specific operational intent | Pilot validation required |

---

# 12. Pilot-Review Flags

The following leaves require explicit review during the pilot.

## 12.1 Query-volume review

### `PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`

Reason:

Expected frequency may be substantially lower than ordinary citizen passport
queries.

Action during pilot:

- measure number of plausible distinct seed families;
- verify that examples are not merely ordinary application queries with the
  words "official" or "diplomatic" inserted.

---

### `PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`

Reason:

Potentially low-volume specialized category.

Action during pilot:

- verify independent document-focused queries exist;
- ensure they differ from the official/diplomatic application-process leaf.

---

# 13. Boundary and Volume Review

## `PASSPORT_DOCUMENTS_MISSING`

Check whether "missing supporting document" is a sufficiently common and
coherent citizen information need.

Do not confuse it with a missing passport.

---

## `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM`

Check whether generic account-access failures occur independently of more
specific causes.

If almost every example can be assigned to password, activation or contact
update, this class may be unnecessary.

---

## `PASSPORT_APPOINTMENT_PROBLEM`

Check whether generic appointment problems form a stable class.

If all examples are actually scheduling/date/account issues, consider removing
the generic problem leaf.

---

## `PASSPORT_APPLICATION_DELAY`

Check the distinction between:

- ordinary status inquiry;
- explicit abnormal delay complaint.

---

## `PASSPORT_GENERAL_SERVICE_GUIDANCE`

Strongly review both class coherence and volume.

This leaf must be removed if it behaves as an annotation fallback rather than a
genuine citizen intent.

---

# 14. Annotation Precedence Rules

During pilot annotation, use the most specific supported intent.

Examples:

1. "What papers do I bring for biometrics?"
   → `PASSPORT_DOCUMENTS_ENROLMENT`

2. "What happens during biometrics?"
   → `PASSPORT_ENROLMENT_BIOMETRICS`

3. "How do I book an appointment?"
   → `PASSPORT_APPOINTMENT_SCHEDULING`

4. "When is my appointment?"
   → `PASSPORT_APPOINTMENT_DATE`

5. "How long does passport processing normally take?"
   → `PASSPORT_PROCESSING_TIME`

6. "Mine has been stuck for weeks."
   → `PASSPORT_APPLICATION_DELAY`

7. "Did my payment go through?"
   → `PASSPORT_PAYMENT_CONFIRMATION`

8. "My payment failed."
   → `PASSPORT_PAYMENT_FAILURE`

9. "Money was deducted but it says failed."
   → `PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED`

10. "How do I get that money back?"
    → `PASSPORT_PAYMENT_REFUND`

11. "I lost my passport."
    → `PASSPORT_REISSUE_LOST`

12. "I lost the slip needed to collect my passport."
    → `PASSPORT_DELIVERY_SLIP_LOST`

13. "How do I create a passport portal account?"
    → `PASSPORT_ONLINE_ACCOUNT_REGISTRATION`

14. "How do I apply for my passport online?"
    → `PASSPORT_APPLICATION_ONLINE`

15. "Should I apply as new or reissue?"
    → `PASSPORT_GENERAL_NEW_VS_REISSUE`

---

# 15. General Labels Must Not Be Fallbacks

The following labels are broad by design:

- `PASSPORT_APPLICATION_PROCESS`
- `PASSPORT_DOCUMENTS_REQUIRED`
- `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM`
- `PASSPORT_APPOINTMENT_PROBLEM`
- `PASSPORT_REISSUE_PROCESS`
- `PASSPORT_FEES_INFORMATION`
- `PASSPORT_APPLICATION_STATUS`
- `PASSPORT_GENERAL_EPASSPORT_INFORMATION`
- `PASSPORT_GENERAL_SERVICE_GUIDANCE`

A broad label may only be used when the user's semantic intent genuinely
matches that label.

Broad labels must never be used solely because:

- the query is difficult;
- the annotator is uncertain;
- the classifier is uncertain;
- the query is outside the taxonomy;
- another label is not obvious.

Unsupported cases must later be handled using OOD detection and confidence
thresholds.

---

# 16. Mutable Knowledge Boundary

The Passport taxonomy should classify the citizen's information need.

It should not encode time-sensitive government facts.

The following should remain outside the classifier taxonomy:

- current passport fees;
- exact processing durations;
- payment provider names;
- current bank/payment channels;
- passport office addresses;
- embassy addresses;
- current eligibility rules;
- current service availability;
- current notices;
- current delivery schedules.

These belong in Partner B's verified government-information corpus.

Example:

Query:

> How much is express passport service?

Classifier intent:

`PASSPORT_FEES_DELIVERY_CATEGORY`

The exact current price should be retrieved from verified corpus data rather
than embedded in the taxonomy.

---

# 17. Overseas Context

Overseas service was intentionally not retained as a first-level parent.

The semantic intent remains the primary routing signal.

Examples:

New passport abroad:

`PASSPORT_APPLICATION_OVERSEAS`

Reissue abroad:

`PASSPORT_REISSUE_OVERSEAS`

A future system may separately represent contextual metadata such as
`applicant_location = overseas`, but that context should not replace the
citizen's primary intent.

---

# 18. Official / Diplomatic Context

Official or diplomatic status is also treated as contextual/specialized rather
than its own parent.

Current dedicated leaves are retained provisionally because they represent two
different information needs:

Application workflow:

`PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`

Supporting documentation:

`PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`

Their continued existence depends on pilot query-volume evidence.

---

# 19. OOD Boundary

The taxonomy is intended for Passport-service queries.

Examples that should eventually be handled as OOD rather than forced into
Passport general information include:

- visa application questions;
- foreign immigration questions;
- NID-only problems;
- Birth Registration-only problems;
- tax services;
- Police GD services unrelated to Passport workflow;
- Driving Licence services;
- unrelated conversational queries.

OOD examples should not yet be generated until the project-wide OOD design and
labeling protocol are established.

---

# 20. Privacy Boundary

The taxonomy classifies the information need independently of whether the
query contains private data.

For example:

> My passport number is [value], how do I check my application status?

The semantic intent is still:

`PASSPORT_APPLICATION_STATUS`

Privacy detection is Partner B's responsibility and operates as a separate
pipeline component.

Privacy-positive dataset examples should not be added to the Passport pilot
until the shared privacy-type vocabulary and annotation policy are finalized.

---

# 21. Pilot Dataset Requirements

The Passport pilot should follow the same controlled methodology already used
for Birth Registration.

The pilot should:

1. cover all retained leaves;
2. use multiple independent query families per leaf;
3. assign stable `parent_query_id` values;
4. distinguish independent seeds from controlled paraphrases;
5. preserve Bangla, Banglish and English variation;
6. avoid producing trivial template copies;
7. avoid mutable factual claims in generated query text;
8. include semantic boundary cases for neighboring classes;
9. exclude privacy-positive rows until the privacy contract is ready;
10. exclude formal OOD rows until the project-wide OOD protocol is ready.

The pilot is intended to validate the taxonomy, not to maximize dataset size.

---

# 22. Pilot Review Questions

For every query-topic leaf, review:

### Q1. Is the citizen's information need recognizable without seeing the label?

If no, the class may be artificial.

### Q2. Can at least several independent seed families be created?

If no, query volume may be too low.

### Q3. Can neighboring leaves be distinguished consistently?

If no, merge or redefine them.

### Q4. Are examples semantically different rather than lexical substitutions?

If no, redesign the seed families.

### Q5. Is this really an intent or merely contextual metadata?

If it is mostly context, reconsider whether a separate classifier class is
appropriate.

### Q6. Does the class require mutable factual information to define it?

If yes, move that information into the knowledge corpus rather than the
taxonomy.

---

# 23. Leaves Requiring Mandatory Pilot Attention

The following leaves should be explicitly reported in the pilot-review
document:

1. `PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`
2. `PASSPORT_DOCUMENTS_MISSING`
3. `PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`
4. `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM`
5. `PASSPORT_APPOINTMENT_PROBLEM`
6. `PASSPORT_APPLICATION_DELAY`
7. `PASSPORT_GENERAL_SERVICE_GUIDANCE`

These are not currently rejected.

They are retained as hypotheses to be tested by controlled pilot annotation.

---

# 24. Final Semantic Audit Result

## Parent topics

**PASS**

All 8 parents represent coherent broad information needs.

## Leaf definitions

**PASS WITH PILOT-REVIEW FLAGS**

The 56 current leaves are sufficiently defined to begin pilot annotation.

## Inclusion/exclusion boundaries

**PASS**

Important neighboring intents have explicit boundaries.

## Broad fallback risk

**CONTROLLED BUT REQUIRES PILOT REVIEW**

Generic problem and general-information leaves must be monitored carefully.

## Mutable-fact separation

**PASS**

Current taxonomy design correctly separates classifier semantics from
time-sensitive government facts.

## OOD separation

**PASS AT DESIGN LEVEL**

General-information labels are explicitly prohibited from acting as OOD
fallbacks.

## Shared-contract freeze

**NOT READY**

The taxonomy should not yet be added to the frozen shared parent/query-topic
contract.

## Pilot readiness

**READY AFTER TAXONOMY METADATA UPDATE**

The semantic audit supports moving the Passport taxonomy to controlled pilot
annotation after `semantic_audit_passed` is updated in the taxonomy metadata.

---

# 25. Final Decision

**PASSPORT TAXONOMY SEMANTIC AUDIT: PASS WITH PILOT-REVIEW FLAGS**

No mandatory taxonomy restructuring is required before pilot annotation.

The following sequence should now be followed:

```text
Structural validation
        PASS
          ↓
Semantic audit
 PASS WITH PILOT FLAGS
          ↓
Update taxonomy audit metadata
          ↓
Re-run structural validator
          ↓
Create controlled Passport pilot dataset
          ↓
Validate pilot
          ↓
Human semantic review
          ↓
Resolve flagged leaves
          ↓
Controlled expansion