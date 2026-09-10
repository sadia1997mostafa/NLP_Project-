# NID Semantic Freeze Audit

Owner: Prothom  
Service: `NID`  
Taxonomy version reviewed: `0.3.0`  
Parent topics: 9  
Query topics: 73  
Status: Semantic review in progress

---

## Purpose

The structural validator confirms that the NID taxonomy is syntactically
and structurally valid.

This audit checks a different question:

> Do neighboring labels represent sufficiently different citizen
> information needs that a human annotator and a classifier can
> distinguish them consistently?

The taxonomy must not be frozen only because its YAML structure is valid.

---

# Semantic Routing Principle

NagorikSheba AI classifies the citizen's primary information need.

It should not create a new intent merely because the user mentions:

- online
- fee
- documents
- office
- application
- status
- card
- portal

The complete meaning of the query determines the route.

Where a query contains multiple needs, annotation rules will later define
the primary intent or mark the example as ambiguous.

---

# High-Risk Boundary Audit

## 1. Registration Process vs Online Registration Application

### Labels

`NID_REGISTRATION_PROCESS`

vs

`NID_REGISTRATION_ONLINE_APPLICATION`

### Decision

KEEP SEPARATE.

### Routing rule

Use `NID_REGISTRATION_PROCESS` when the citizen asks about the general
first-time NID/voter registration procedure.

Use `NID_REGISTRATION_ONLINE_APPLICATION` when the question specifically
concerns beginning or submitting that registration online.

### Examples

"How do I register for NID for the first time?"

-> `NID_REGISTRATION_PROCESS`

"Can I apply for my first NID online?"

-> `NID_REGISTRATION_ONLINE_APPLICATION`

### Semantic audit

PASS.

---

## 2. Online Registration Application vs NID Online Account Registration

### Labels

`NID_REGISTRATION_ONLINE_APPLICATION`

vs

`NID_ONLINE_ACCOUNT_REGISTRATION`

### Decision

KEEP SEPARATE.

### Routing rule

`NID_REGISTRATION_ONLINE_APPLICATION` means applying to become a new
NID holder/voter.

`NID_ONLINE_ACCOUNT_REGISTRATION` means a citizen who has an NID is
creating an account for NID online services.

### Examples

"I don't have an NID. How can I apply online?"

-> `NID_REGISTRATION_ONLINE_APPLICATION`

"I already have an NID. How can I create an online account?"

-> `NID_ONLINE_ACCOUNT_REGISTRATION`

### Semantic audit

PASS — critical boundary.

---

## 3. Registration Eligibility vs Registration Age Eligibility

### Labels

`NID_REGISTRATION_ELIGIBILITY`

vs

`NID_REGISTRATION_AGE_ELIGIBILITY`

### Decision

KEEP SEPARATE.

### Routing rule

Use age eligibility only when age/minimum-age eligibility is the explicit
information need.

Other citizenship or general qualification questions belong to general
registration eligibility.

### Examples

"Who is eligible for a new NID?"

-> `NID_REGISTRATION_ELIGIBILITY`

"Can someone under 18 register?"

-> `NID_REGISTRATION_AGE_ELIGIBILITY`

### Semantic audit

PASS.

---

## 4. Registration Processing Time vs Registration Status vs Registration Delay

### Labels

`NID_REGISTRATION_PROCESSING_TIME`

`NID_STATUS_REGISTRATION_APPLICATION`

`NID_STATUS_REGISTRATION_DELAY`

### Decision

KEEP ALL THREE.

### Routing rule

Processing time:
citizen asks about the normal expected duration.

Status:
citizen asks what stage an existing application is currently in.

Delay:
citizen indicates that an existing application is taking unusually long
or is stuck.

### Examples

"How many days does NID registration normally take?"

-> `NID_REGISTRATION_PROCESSING_TIME`

"How can I check my NID application status?"

-> `NID_STATUS_REGISTRATION_APPLICATION`

"My NID application has been pending for a long time."

-> `NID_STATUS_REGISTRATION_DELAY`

### Semantic audit

PASS — critical boundary.

---

## 5. Registration Address Fields vs Registration Area Selection

### Labels

`NID_REGISTRATION_ADDRESS_FIELDS`

vs

`NID_REGISTRATION_AREA_SELECTION`

### Decision

KEEP SEPARATE.

### Routing rule

Address fields concern what address information is entered into the
registration form.

Area selection concerns which voter geographic area the citizen should
be registered under.

### Examples

"What should I write as my permanent address?"

-> `NID_REGISTRATION_ADDRESS_FIELDS`

"My present and permanent addresses are different. Which voter area
should I register under?"

-> `NID_REGISTRATION_AREA_SELECTION`

### Semantic audit

PASS.

---

## 6. Address Correction vs Voter Area Transfer

### Labels

`NID_CORRECTION_ADDRESS`

vs

`NID_VOTER_AREA_TRANSFER`

### Decision

KEEP SEPARATE.

### Routing rule

Address correction changes incorrect or outdated address information.

Voter-area transfer changes the electoral area under which an already
registered voter belongs.

Moving residence alone does not automatically determine the label.

The requested action determines the label.

### Examples

"My address is wrong on my NID."

-> `NID_CORRECTION_ADDRESS`

"I moved and want to transfer my voter area."

-> `NID_VOTER_AREA_TRANSFER`

### Semantic audit

PASS — critical boundary.

---

## 7. Marital Status Correction vs Spouse Name Correction

### Labels

`NID_CORRECTION_MARITAL_STATUS`

vs

`NID_CORRECTION_SPOUSE_NAME`

### Decision

KEEP SEPARATE.

### Routing rule

Marital status concerns values such as married/unmarried.

Spouse-name correction concerns the actual recorded husband/wife
information.

### Examples

"I am married but my NID still says unmarried."

-> `NID_CORRECTION_MARITAL_STATUS`

"My husband's name is wrong on my NID."

-> `NID_CORRECTION_SPOUSE_NAME`

### Semantic audit

PASS.

---

## 8. Login vs Login Problem vs Password Reset vs Account Recovery

### Labels

`NID_ONLINE_LOGIN`

`NID_ONLINE_LOGIN_PROBLEM`

`NID_ONLINE_PASSWORD_RESET`

`NID_ONLINE_ACCOUNT_RECOVERY`

### Decision

KEEP ALL FOUR.

### Routing rule

Login:
asks how or where to log in.

Login problem:
credentials/account are known but normal login fails.

Password reset:
password is forgotten or must be reset.

Account recovery:
broader account access or account information has been lost.

### Examples

"Where do I log in?"

-> `NID_ONLINE_LOGIN`

"My correct login details aren't working."

-> `NID_ONLINE_LOGIN_PROBLEM`

"I forgot my password."

-> `NID_ONLINE_PASSWORD_RESET`

"I lost access to my old NID account and don't know the account
information."

-> `NID_ONLINE_ACCOUNT_RECOVERY`

### Semantic audit

PASS — annotation guideline required.

---

## 9. OTP Not Received vs OTP Verification Problem

### Labels

`NID_ONLINE_OTP_NOT_RECEIVED`

vs

`NID_ONLINE_OTP_VERIFICATION`

### Decision

KEEP SEPARATE.

### Routing rule

Not received:
no OTP arrives.

Verification:
an OTP arrives but cannot successfully be accepted or verified.

### Examples

"I requested the code but no SMS came."

-> `NID_ONLINE_OTP_NOT_RECEIVED`

"I entered the OTP but it says invalid."

-> `NID_ONLINE_OTP_VERIFICATION`

### Semantic audit

PASS.

---

## 10. Face Verification vs Biometric Verification

### Labels

`NID_ONLINE_FACE_VERIFICATION`

vs

`NID_ONLINE_BIOMETRIC_VERIFICATION`

### Decision

KEEP SEPARATE FOR CURRENT TAXONOMY.

### Routing rule

Explicit face/image verification problems use
`NID_ONLINE_FACE_VERIFICATION`.

Fingerprint or explicitly non-face biometric problems use
`NID_ONLINE_BIOMETRIC_VERIFICATION`.

A vague "verification problem" must not automatically be assigned to
either leaf without sufficient evidence.

### Semantic audit

PASS WITH ANNOTATION CAUTION.

---

## 11. Portal Unavailable vs General Online Problem

### Labels

`NID_ONLINE_PORTAL_UNAVAILABLE`

vs

`NID_ONLINE_GENERAL_PROBLEM`

### Decision

KEEP SEPARATE.

### Routing rule

Portal unavailable:
website/system itself does not load, appears down or returns a
system-level availability error.

General problem:
user identifies an NID online-service problem but does not provide
enough information for a more specific online leaf.

### Semantic audit

PASS WITH CAUTION.

`NID_ONLINE_GENERAL_PROBLEM` must not become a default fallback for
low-confidence classification.

---

## 12. Smart NID Status vs Distribution Date vs Delay

### Labels

`NID_SMART_STATUS`

`NID_SMART_DISTRIBUTION_DATE`

`NID_SMART_DELAY`

### Decision

KEEP ALL THREE.

### Routing rule

Status:
is this citizen's Smart NID ready/issued/produced?

Distribution date:
when will Smart NID distribution occur generally or in an area?

Delay:
the citizen expected the card but it has not arrived or progressed
as expected.

### Examples

"Is my Smart NID ready?"

-> `NID_SMART_STATUS`

"When will Smart NID distribution start in my area?"

-> `NID_SMART_DISTRIBUTION_DATE`

"Distribution started but I still haven't received my card."

-> `NID_SMART_DELAY`

### Semantic audit

PASS — critical boundary.

---

## 13. Smart NID Replacement vs Smart NID Service

### Labels

Replacement leaves under `NID_REPLACEMENT`

vs

leaves under `NID_SMART_CARD`

### Decision

LOST/STOLEN/DAMAGED SMART NID BELONGS TO REPLACEMENT.

### Routing rule

If the primary need is obtaining another card because the Smart NID
was lost, stolen or damaged, route through `NID_REPLACEMENT`.

Do not route it to general Smart NID application.

### Example

"My Smart NID was lost. How do I get another one?"

-> `NID_REPLACEMENT_PROCESS`

### Semantic audit

PASS.

---

## 14. Replacement Process vs Replacement Eligibility

### Labels

`NID_REPLACEMENT_PROCESS`

vs

`NID_REPLACEMENT_ELIGIBILITY`

### Decision

KEEP SEPARATE.

### Routing rule

Eligibility asks whether replacement/reissue is allowed.

Process asks how to complete it.

### Examples

"Can a damaged NID be replaced?"

-> `NID_REPLACEMENT_ELIGIBILITY`

"How do I replace my damaged NID?"

-> `NID_REPLACEMENT_PROCESS`

### Semantic audit

PASS.

---

## 15. Replacement Processing Time vs Replacement Status

### Labels

`NID_REPLACEMENT_PROCESSING_TIME`

vs

`NID_STATUS_REPLACEMENT_APPLICATION`

### Decision

KEEP SEPARATE.

### Routing rule

Processing time:
normal expected duration.

Status:
tracking an already submitted application.

### Examples

"How long does NID reissue normally take?"

-> `NID_REPLACEMENT_PROCESSING_TIME`

"How can I track my reissue application?"

-> `NID_STATUS_REPLACEMENT_APPLICATION`

### Semantic audit

PASS.

---

## 16. Fee Amount vs Payment Method vs Payment Status

### Labels

`NID_FEES_SERVICE_SPECIFIC`

`NID_PAYMENT_METHOD`

`NID_PAYMENT_STATUS`

### Decision

KEEP SEPARATE.

### Routing rule

Fee:
asks how much must be paid or whether payment is required.

Method:
asks how or through which channel payment is made.

Status:
asks whether an already attempted payment succeeded.

### Examples

"How much does NID reissue cost?"

-> `NID_FEES_SERVICE_SPECIFIC`

"Can I pay the reissue fee using mobile banking?"

-> `NID_PAYMENT_METHOD`

"I already paid but it still shows unpaid."

-> `NID_PAYMENT_STATUS`

### Semantic audit

PASS — critical boundary.

---

## 17. NID Number Retrieval vs Registration Reference Recovery

### Labels

`NID_ACCESS_NUMBER_RETRIEVAL`

vs

`NID_REGISTRATION_REFERENCE_RECOVERY`

### Decision

KEEP SEPARATE.

### Routing rule

NID number retrieval:
recover the citizen's existing National Identity Number.

Registration reference recovery:
recover an application ID, slip, tracking number or registration
reference.

### Examples

"I forgot my NID number."

-> `NID_ACCESS_NUMBER_RETRIEVAL`

"I lost my NID application slip and reference number."

-> `NID_REGISTRATION_REFERENCE_RECOVERY`

### Semantic audit

PASS — critical boundary.

---

## 18. Late Registration vs Validity / Re-registration

### Labels

`NID_REGISTRATION_LATE_REGISTRATION`

vs

`NID_GENERAL_VALIDITY_REREGISTRATION`

### Decision

KEEP SEPARATE.

### Routing rule

Late registration:
citizen has never registered and wants to register later than usual.

Validity/re-registration:
citizen already has or previously had an NID and asks whether it
remains valid or whether registration must be repeated.

### Examples

"I am 30 and never registered for NID. What should I do?"

-> `NID_REGISTRATION_LATE_REGISTRATION`

"I already have an old NID. Do I need to register again?"

-> `NID_GENERAL_VALIDITY_REREGISTRATION`

### Semantic audit

PASS.

---

## 19. Physical First NID Collection vs Smart NID Collection

### Labels

`NID_REGISTRATION_PHYSICAL_CARD_COLLECTION`

vs

`NID_SMART_COLLECTION_LOCATION`

### Decision

KEEP SEPARATE.

### Routing rule

First-card collection belongs to the first-time registration lifecycle.

Smart collection refers specifically to distribution/collection of a
Smart NID.

### Semantic audit

PASS.

---

# Cross-Cutting Annotation Rule

Some user queries contain more than one possible intent.

Example:

"আমার নাম correction করতে কত টাকা লাগবে এবং কীভাবে pay করব?"

This query asks both:

- service-specific fee amount
- payment method

Such examples should NOT be silently assigned based on whichever keyword
appears first.

During dataset annotation, they should be handled using the project's
future multi-intent/primary-intent annotation rule or rewritten into
single-intent training examples where appropriate.

The first showcase classifier is primarily designed around one
query-topic output per query.

---

# Semantic Audit Result

The reviewed high-risk neighboring intent groups have distinguishable
semantic boundaries.

Result:

`PASS_WITH_DATASET_MIGRATION_REQUIRED`

No query-topic IDs are removed or renamed by this audit.

However, the current legacy NID dataset cannot be trained directly using
its existing `problem` column because many rows must be migrated into the
new hierarchy.

Examples include:

- fee queries currently stored under registration/replacement
- status queries currently stored under registration
- voter-area transfer stored under information correction
- Smart NID replacement stored under lost/stolen NID
- online-copy/download queries stored under online-service categories

Therefore:

1. NID taxonomy structure is semantically acceptable.
2. Existing rows still require re-annotation/migration.
3. `needs_pilot_expansion` leaves require reviewed examples.
4. NID taxonomy may be marked internally as taxonomy-ready only after
   this audit is committed.
5. The global shared contract must NOT yet be frozen because Passport,
   Tax, Police GD, Driving Licence and Birth Registration taxonomies
   still have to be developed and jointly reviewed.
