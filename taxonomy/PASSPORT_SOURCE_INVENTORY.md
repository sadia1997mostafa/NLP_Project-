# NagorikSheba AI — Passport Source and Query Inventory

Owner: Prothom
Service ID: `PASSPORT`
Status: `SOURCE_INVENTORY_DRAFT`

## 1. Purpose

This document defines the evidence base and initial citizen-query coverage
for the Passport service before creating `taxonomy/passport.yaml`.

The objective is NOT to freeze Passport labels yet.

The objective is to identify:

1. officially supported passport workflows;
2. common citizen query areas;
3. likely parent-topic boundaries;
4. topics that need additional source review;
5. topics that should not yet become classifier labels.

---

# 2. Primary Official Sources

## Source P1 — Bangladesh e-Passport Portal

URL:

https://www.epassport.gov.bd/home

Authority:

Bangladesh e-Passport Online Registration Portal /
Department of Immigration and Passports.

Evidence available:

- new e-Passport application;
- e-Passport re-issue;
- application steps;
- urgent applications;
- instructions;
- passport fees;
- payment information;
- FAQs;
- passport-related notices.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

---

## Source P2 — e-Passport Application Instructions

URL:

https://www.epassport.gov.bd/instructions/instructions

Evidence available:

- online application;
- NID/Birth Registration based application information;
- documents;
- applicant information;
- minors;
- relevant supporting documents;
- application from Bangladesh Missions;
- delivery categories;
- enrolment requirements.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

Important:

Mutable operational details such as exact processing duration,
specific document requirements, or fees should not be encoded as
taxonomy semantics.

Those facts belong in Partner B's knowledge corpus.

---

## Source P3 — e-Passport Fees and Payment

URL:

https://www.epassport.gov.bd/instructions/passport-fees

Evidence available:

- passport fee information;
- payment channels;
- payment receipts/slips;
- delivery categories associated with payment.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

Important:

Exact fee amounts must remain knowledge-corpus facts rather than
classifier labels.

---

## Source P4 — e-Passport FAQ

URL:

https://www.epassport.gov.bd/landing/faqs

Evidence categories include:

- Account & Account Settings
- Appointments
- Payment
- Application
- General Queries
- Other passport problems

Examples of supported question types include:

- forgotten account password;
- registered mobile-number changes;
- registered email changes;
- activation email not received;
- application status;
- payment problems;
- enrolment questions.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

---

## Source P5 — Passport Office Selection / Onboarding

URL:

https://www.epassport.gov.bd/onboarding

Evidence available:

- applying from Bangladesh versus abroad;
- present-address district;
- police-station selection;
- responsible Regional Passport Office.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

---

## Source P6 — Enrolment Document Checklist

URL:

https://www.epassport.gov.bd/landing/notices/160

Evidence available:

- application form;
- application summary;
- identity documents;
- previous passport;
- payment slip where applicable;
- additional documents where applicable;
- documents required for correction/change cases.

Evidence status:

`PRIMARY_OFFICIAL_SOURCE`

---

# 3. Scope Decision

The initial NagorikSheba Passport implementation will focus primarily on:

`Bangladesh e-Passport citizen services`

The following should NOT automatically be mixed into the core taxonomy:

- foreign-country passport services;
- visa services;
- immigration clearance;
- airport immigration;
- e-gate troubleshooting;
- citizenship applications;
- travel permits unrelated to normal passport service;
- historical MRP-only procedures.

These may later become:

- separate services;
- legacy-query labels;
- OOD examples;
- or additional supported topics after source review.

---

# 4. Initial Passport Query Inventory

The following areas should be investigated as candidate classifier topics.

## A. New Passport / First Application

Citizen queries may include:

- how to apply for a new passport;
- first-time passport application;
- online application process;
- where to start the application;
- application form;
- required information;
- eligibility;
- NID/Birth Registration requirement;
- passport type;
- passport validity choice;
- number of pages;
- delivery type.

Candidate parent:

`PASSPORT_APPLICATION`

---

## B. Passport Office / Application Location

Citizen queries may include:

- which passport office to select;
- office based on present address;
- district selection;
- police-station selection;
- Regional Passport Office;
- applying from a Bangladesh Mission;
- applying while living abroad.

Candidate parent:

`PASSPORT_APPLICATION_LOCATION`

Possible alternative:

Keep this under `PASSPORT_APPLICATION` if the leaf hierarchy remains clean.

---

## C. Required Documents

Citizen queries may include:

- documents required for passport application;
- NID requirement;
- Birth Registration requirement;
- previous passport requirement;
- documents for minors;
- supporting documents;
- documents to carry for enrolment;
- missing/unavailable documents.

Candidate parent:

`PASSPORT_DOCUMENTS`

Important boundary:

`What documents are required?`

is different from:

`One required document is unavailable; what should I do?`

Do not merge these automatically.

---

## D. Online Account

Citizen queries may include:

- creating an online account;
- login;
- forgotten password;
- password reset;
- account activation;
- activation email not received;
- email change;
- mobile-number change;
- account-access problems.

Candidate parent:

`PASSPORT_ONLINE_ACCOUNT`

---

## E. Appointment and Enrolment

Citizen queries may include:

- passport appointment;
- appointment scheduling;
- appointment date;
- appointment problems;
- what to take to appointment;
- enrolment procedure;
- biometric enrolment;
- enrolment location.

Candidate parent:

`PASSPORT_APPOINTMENT_AND_ENROLMENT`

Do not create detailed biometric-problem labels without sufficient
official/query evidence.

---

## F. Passport Re-Issue

Citizen queries may include:

- passport re-issue;
- expired passport;
- expiring passport;
- re-issue without information change;
- re-issue with information change;
- previous passport information;
- reason for re-issue.

Candidate parent:

`PASSPORT_REISSUE`

---

## G. Lost / Stolen / Damaged Passport

Citizen queries may include:

- passport lost;
- passport stolen;
- damaged passport;
- replacement after loss;
- re-issue after loss;
- what to do after losing passport.

Candidate parent:

Potentially:

`PASSPORT_REPLACEMENT`

or these may become leaves under:

`PASSPORT_REISSUE`

Decision must be made only after semantic-boundary review.

---

## H. Information Change / Correction

Potential citizen queries include:

- name information changed;
- address changed;
- profession changed;
- marital information changed;
- other information changed compared with previous passport;
- incorrect application information.

Candidate parent:

Potentially:

`PASSPORT_INFORMATION_CHANGE`

However:

Application-form correction and passport re-issue with changed
information may represent different workflows.

Do not merge them until source/query evidence is reviewed.

---

## I. Passport Fees and Payment

Citizen queries may include:

- passport fee;
- payment method;
- online payment;
- offline payment;
- payment failed;
- money deducted but payment failed;
- payment receipt;
- payment slip;
- urgent-delivery fee.

Candidate parent:

`PASSPORT_FEES_AND_PAYMENT`

Exact monetary amounts belong in the retrieval corpus.

---

## J. Application Status

Citizen queries may include:

- application status;
- current processing stage;
- whether passport is approved;
- status checking;
- application pending;
- application delayed.

Candidate parent:

`PASSPORT_STATUS_AND_DELIVERY`

Important semantic boundary:

Application status:

`What stage is my application in?`

Application delay:

`My application has been pending unusually long.`

These should not automatically be treated as the same intent.

---

## K. Processing Time / Delivery Type

Citizen queries may include:

- normal processing time;
- regular delivery;
- express delivery;
- super-express / urgent delivery;
- when passport will be ready.

Potential parent:

`PASSPORT_STATUS_AND_DELIVERY`

Important:

The classifier should detect the type of question.

It should NOT memorize exact delivery durations as taxonomy semantics.

---

## L. Passport Collection

Citizen queries may include:

- where to collect passport;
- passport ready for collection;
- collection process;
- delivery slip;
- lost delivery slip;
- documents needed for collection.

Potential parent:

`PASSPORT_STATUS_AND_DELIVERY`

or:

`PASSPORT_COLLECTION`

depending on query volume and semantic separability.

---

## M. Overseas / Bangladesh Mission

Citizen queries may include:

- applying from abroad;
- Bangladesh Mission application;
- responsible embassy/mission;
- re-issue from abroad;
- passport service while overseas.

Potential parent:

`PASSPORT_OVERSEAS_SERVICE`

Alternatively, overseas workflow may be represented as leaves inside
application/reissue if a separate parent would be too sparse.

Requires review.

---

## N. Official / Diplomatic Passport

Official sources mention special requirements for official and
diplomatic passport cases.

Potential citizen queries:

- official passport;
- diplomatic passport;
- GO/NOC;
- government employee passport requirements.

Potential parent:

`PASSPORT_SPECIAL_CATEGORY`

Status:

`NEEDS_QUERY_VOLUME_REVIEW`

Do not create a large hierarchy unless realistic citizen-query demand
supports it.

---

## O. General Passport Information

Citizen queries may include:

- what is an e-Passport;
- difference between new passport and re-issue;
- general passport-service information.

Potential parent:

`PASSPORT_GENERAL_INFORMATION`

Keep this label narrow so it does not become a catch-all class.

---

# 5. Candidate Parent Topics

Initial candidates only:

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

Potential separate parents still under review:

- `PASSPORT_APPLICATION_LOCATION`
- `PASSPORT_REPLACEMENT`
- `PASSPORT_INFORMATION_CHANGE`
- `PASSPORT_COLLECTION`

They should become parents only if they contain enough semantically
distinct query topics.

---

# 6. High-Risk Semantic Boundaries

The Passport taxonomy must explicitly examine:

### New application vs re-issue

First passport application is not the same intent as renewal/re-issue.

### Re-issue vs information change

A user can ask about re-issue generally or specifically because
information changed.

### Required documents vs missing documents

Knowing required documents is different from being unable to supply one.

### Application status vs application delay

Status asks where the application currently is.

Delay expresses abnormal waiting or lack of progress.

### Processing time vs application delay

General expected duration is not the same as a user's delayed case.

### Application form print vs passport collection

Printing paperwork is not collecting an issued passport.

### Payment information vs payment failure

General fee/payment guidance is different from a failed transaction.

### Account activation problem vs appointment problem

Both happen on the portal but represent different workflows.

### Passport office selection vs address information

Selecting the responsible office is different from entering address
information in an application.

### Lost passport vs lost delivery slip

These are entirely different objects and must never share one label.

---

# 7. Data-Generation Rules

Do not mass-generate Passport queries yet.

Required sequence:

source inventory
→ parent-topic draft
→ query-topic definitions
→ structural validator
→ semantic audit
→ small pilot dataset
→ human review
→ controlled expansion
→ family-aware validation

Every synthetic query must remain explicitly labeled:

`SYNTHETIC`

Generated paraphrases must later be labeled:

`PARAPHRASED`

Never mark generated text as:

`REAL`

---

# 8. Privacy Boundary

Passport-related citizen queries may naturally contain:

- passport number;
- NID number;
- Birth Registration number;
- phone number;
- email address;
- address;
- application identifiers.

The current Passport taxonomy should describe the citizen intent
without requiring real personal identifiers.

Privacy-positive dataset construction will be coordinated later with
Partner B's privacy contract.

Do not invent the privacy vocabulary independently.

---

# 9. Knowledge-vs-Taxonomy Boundary

Prothom's classifier taxonomy should identify questions such as:

- passport fee information;
- required documents;
- application status;
- processing time;
- urgent delivery;
- application location.

It should not hard-code answers such as:

- exact fee amounts;
- exact current processing durations;
- current office addresses;
- current payment providers;
- current administrative rules.

Those mutable facts belong in Partner B's verified knowledge corpus.

---

# 10. Current Decision

Official source coverage:

`SUFFICIENT_TO_BEGIN TAXONOMY DESIGN`

Parent taxonomy:

`NOT YET REVIEWED`

Query-topic taxonomy:

`NOT YET DEFINED`

Pilot dataset:

`NOT CREATED`

Semantic audit:

`NOT PERFORMED`

Shared contract:

`NOT FROZEN`