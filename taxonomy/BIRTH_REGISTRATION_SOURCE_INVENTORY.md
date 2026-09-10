# Birth Registration Source and Query-Topic Inventory

Owner: Prothom
Service ID: `BIRTH_REGISTRATION`
Status: Pre-taxonomy evidence inventory

## Purpose

Unlike NID, the project does not currently have a prepared citizen-query
dataset for Birth Registration.

Therefore, the Birth Registration taxonomy must first be derived from
the actual service capabilities exposed by Bangladesh's official Birth
and Death Registration Information System (BDRIS).

This document records the official service areas and converts them into
candidate citizen information needs.

These are NOT frozen taxonomy IDs yet.

---

# Official Service Scope

The official BDRIS Birth Registration service exposes the following
major functions:

1. New Birth Registration Application
2. Birth Registration Application Status
3. Birth Registration Certificate Reprint
4. Birth Registration Certificate Cancellation
5. Birth Registration Information Search / Verification
6. Birth Registration Information Correction
7. Birth Registration Application Form Print
8. Birth and Death Registration Fee Information

The online Birth Registration application workflow also contains
several important sub-procedures:

- selecting the registration office/location;
- applying based on birth place;
- applying based on permanent address;
- applying through a Bangladesh embassy/mission;
- entering the registered person's information;
- entering father information;
- entering mother information;
- entering birth-place address;
- entering permanent address;
- entering present address;
- identifying the applicant's relationship to the person;
- guardian/authorized-person handling;
- supporting-document attachment;
- mobile/email OTP verification.

The correction workflow additionally indicates correction of personal,
parent and address information.

---

# Candidate Citizen Query Areas

## A. New Birth Registration

Candidate citizen needs include:

- Who is eligible for birth registration?
- Is there an age limit for registration?
- How do I apply for birth registration?
- Can birth registration be completed online?
- Where should the application be submitted?
- Which registration office should be selected?
- Can Bangladeshis abroad apply through an embassy?
- What information is required?
- What documents are required?
- What if some required documents are missing?
- Who can submit an application for a child?
- Can a parent submit the application?
- Can a guardian submit the application?
- What information about the father is required?
- What information about the mother is required?
- How should birth-place address be entered?
- How should permanent address be entered?
- How should present address be entered?
- How does OTP verification work?
- OTP not received during application.
- How do I print my submitted application?
- What happens after submitting the application?
- How long does registration normally take?

Evidence status:
`official_workflow_supported`

---

## B. Birth Registration Application Status

Candidate citizen needs include:

- How can I check my birth-registration application status?
- Is my application approved?
- Is my application still pending?
- What stage is my application currently in?
- Can application status be checked online?
- Why is my birth-registration application delayed?
- What should I do if the application remains pending?

Evidence status:
`official_service_supported`

Important future distinction:

Normal processing time and an already delayed application should not
automatically become the same intent.

---

## C. Birth Registration Information Correction

Candidate citizen needs include:

- How can I correct information on a birth certificate?
- Name correction
- Name spelling correction
- Date-of-birth correction
- Gender-information correction
- Father-name correction
- Mother-name correction
- Parent-information correction
- Birth-place address correction
- Permanent-address correction
- Present-address correction
- Correction supporting documents
- Correction application procedure
- Correction OTP/contact requirements
- Correction application status
- Reprinting the certificate after correction

Evidence status:
`official_workflow_supported`

Important future distinction:

The taxonomy should primarily represent WHICH information is being
corrected rather than creating duplicate classes for every possible
combination of:

- online;
- documents;
- procedure;
- fee;
- processing time.

---

## D. Birth Certificate Reprint

Candidate citizen needs include:

- How can I reprint my birth certificate?
- Can I obtain another copy of the certificate?
- Where can I request a reprint?
- Can the certificate be reprinted online?
- What information is needed for reprinting?
- What should I do if I need another printed certificate?

Evidence status:
`official_service_supported`

Potential overlap requiring later semantic review:

Reprint is not necessarily the same as correction.

A citizen may have completely correct birth information and simply
need another certificate copy.

---

## E. Birth Record Verification / Information Search

Candidate citizen needs include:

- How can I verify a birth registration?
- How can I check whether a birth record exists?
- How can I verify a birth certificate online?
- What information is needed to verify a record?
- Birth registration number verification
- Birth registration number and DOB verification
- Birth record cannot be found
- Verification fails even though information appears correct

Evidence status:
`official_service_supported`

Important privacy boundary:

Mentioning or asking how to find a Birth Registration Number is
different from actually providing a sensitive identifier value.

---

## F. Birth Registration Application Form / Print

Candidate citizen needs include:

- How can I print my birth-registration application?
- Where is the application-print option?
- What information is required to retrieve the application for print?
- I submitted an application but need another printed copy.

Evidence status:
`official_service_supported`

This may later become either:

1. a dedicated query topic; or
2. part of application/status access.

The semantic audit will decide.

---

## G. Birth Certificate Cancellation

Candidate citizen needs include:

- Can a birth certificate or birth record be cancelled?
- How do I request certificate cancellation?
- When is cancellation appropriate?
- What documents are required for cancellation?
- Where is a cancellation request submitted?
- How can I check a cancellation request?

Evidence status:
`official_service_supported_but_needs_query_pilot`

This official service exists, but the project currently has no citizen
query dataset demonstrating the different cancellation question forms.

---

## H. Birth Registration Fees and Payment

Candidate citizen needs include:

- Is birth registration free?
- What is the birth-registration fee?
- Does late registration have a fee?
- Is there a correction fee?
- Is there a certificate-reprint fee?
- How should a registration-related fee be paid?
- Where can official fee information be found?
- Payment status / receipt questions if supported by the actual process.

Evidence status:
`official_fee_service_exists_needs_detailed_source_review`

Do not invent specific fee amounts at taxonomy-design time.

Fee values belong in Partner B's verified government corpus, not in
Prothom's intent taxonomy.

---

# Preliminary Parent-Topic Hypothesis

The evidence suggests that the eventual Birth Registration hierarchy
may require parent areas similar to:

Birth Registration
|
|-- Registration / Application
|-- Information Correction
|-- Status and Application Tracking
|-- Certificate Access / Reprint
|-- Record Verification / Search
|-- Certificate Cancellation
|-- Fees and Payment
`-- General Information

This is a hypothesis only.

Parent IDs and query-topic IDs must NOT be frozen from this list until
the source inventory and boundary review are complete.

---

# Important Boundary Questions for Taxonomy Design

The next taxonomy stage must explicitly resolve:

Registration process
vs
online application

Registration processing time
vs
application status
vs
application delay

Certificate reprint
vs
application-form print

Record verification
vs
certificate reprint

Name correction
vs
parent-name correction

Birth-place address correction
vs
permanent-address correction
vs
present-address correction

General registration eligibility
vs
age-specific eligibility

Domestic registration
vs
embassy/overseas registration

Fee amount
vs
payment method
vs
payment status

Application OTP failure
vs
general application failure

---

# Current Evidence Assessment

Strong official workflow evidence:

- new registration;
- correction;
- registration-office selection;
- overseas/embassy application;
- applicant/guardian relationship;
- parent information;
- addresses;
- attachments;
- OTP verification;
- application status;
- certificate reprint;
- information verification/search;
- application printing.

Official service exists but requires additional query-level analysis:

- certificate cancellation;
- fee/payment questions;
- failure/error scenarios;
- delayed application behavior.

---

# Dataset Decision

No large synthetic Birth Registration dataset will be generated yet.

First:

1. freeze the parent taxonomy;
2. define query-topic boundaries;
3. create a small reviewed pilot across every leaf;
4. resolve ambiguous labels;
5. only then expand the dataset.

This prevents the project from generating thousands of examples around
an incorrect taxonomy.

---

# Shared Contract Decision

`contracts/labels.yaml` must NOT be changed during this inventory stage.

Partner B must not yet build Birth Registration corpus entries against
unreviewed topic IDs.

Only the already frozen service ID is currently shared:

`BIRTH_REGISTRATION`
