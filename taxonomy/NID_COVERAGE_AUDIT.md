# NID Taxonomy Coverage Audit

Status: Working document  
Owner: Prothom  
Service ID: `NID`

## Purpose

The existing NID query datasheet must not be treated as the final
classification ontology.

The current `problem` column contains five broad labels:

1. NID Information Correction
2. New NID Registration
3. Lost/Stolen NID
4. NID Online Problem
5. Smart ID Card

These labels are useful as coarse categories, but several distinct citizen
intents are currently grouped under the same label.

The final NagorikSheba AI taxonomy will therefore use:

Government Service
    -> Parent Topic
        -> Query Topic / Specific Intent

instead of directly treating the old `problem` column as the final intent.

---

## Existing Working NID Topic Inventory

The wider project planning identified the following working topic inventory:

| No. | Topic |
|---|---|
| 01 | New NID / New Voter Registration |
| 02 | NID Information Correction |
| 03 | Name Change / Name Correction |
| 04 | Father/Mother/Spouse Name Correction |
| 05 | Date of Birth Correction |
| 06 | Address Correction |
| 07 | Voter Area Migration |
| 08 | Lost/Damaged NID / Duplicate |
| 09 | NID Download |
| 10 | NID Online Account / Portal |
| 11 | Smart NID Card |
| 12 | NID Number Retrieval |
| 13 | NID/Voter Registration Status |
| 14 | Vote Center Information |
| 15 | Deceased Voter / Voter Deletion |
| 16 | NID Fees & Payment |
| 17 | NID Validity / Re-registration |
| 18 | Expatriate NID Registration |
| 19 | NID-Document Information Mismatch |
| 20 | General NID Eligibility & Information |

These are working topics, not twenty flat final classes.

---

## Coverage Findings

### 1. New NID Registration

Current dataset coverage: YES

The existing coarse category contains several more specific intents including:

- eligibility
- first-time registration
- application procedure
- required documents
- application delay
- processing time
- fee questions
- payment methods
- application status
- late registration
- missing registration information

Therefore `NID_REGISTRATION` should be treated as a parent rather than one
single final intent.

### 2. NID Information Correction

Current dataset coverage: YES

The category already contains multiple distinct correction intents including:

- own name correction
- father/mother name correction
- date of birth correction
- gender correction
- blood group correction
- marital status correction
- address correction
- voter area transfer
- photo change
- signature change
- document/NID mismatches

Therefore `NID_CORRECTION` should also be a parent topic.

### 3. Lost / Stolen / Damaged / Replacement

Current dataset coverage: YES

The existing `Lost/Stolen NID` category includes topics such as:

- lost card
- stolen card
- damaged card
- replacement/reissue
- required documents
- fees/payment
- Smart NID replacement

This should become a parent topic with more specific query topics beneath it.

### 4. NID Online Account / Portal

Current dataset coverage: YES

The current `NID Online Problem` category should become a parent topic covering
specific online-service intents.

Examples include:

- account registration
- login
- password/reset/recovery
- OTP problems
- verification problems
- portal/service-access problems
- online service usage

### 5. Smart NID Card

Current dataset coverage: YES

The existing Smart ID category should become a parent topic.

Possible leaf intents include:

- eligibility
- registration/application
- status
- collection
- distribution
- delay
- general Smart Card problems

---

## Topics Currently Hidden Inside Broader Labels

The audit found that some topics which should be distinguishable are currently
stored under other coarse labels.

Examples:

- Voter Area Migration -> currently under NID Information Correction
- Registration Status -> currently under New NID Registration
- Fees & Payment -> currently appears inside registration/reissue flows
- NID-document mismatch -> currently mixed into correction examples

The new taxonomy must separate these concepts at the query-topic level where
doing so represents a different citizen information need.

---

## Coverage Requiring Expansion or Separate Review

The following areas from the working project inventory require dedicated
coverage review before the final NID taxonomy is frozen:

- NID Download
- NID Number Retrieval
- Vote Center Information
- Deceased Voter / Voter Deletion
- NID Validity / Re-registration
- Expatriate NID Registration

These topics must not be silently assumed to have sufficient training data.

They will either:

1. receive dedicated pilot examples and become supported query topics, or
2. be explicitly excluded from the first showcase taxonomy.

---

## Important Design Decision

The existing five dataset labels will be retained only as source/provenance
information during migration.

They do NOT define the final model taxonomy.

The target hierarchy will be designed around the actual information need of
the citizen.

Example:

NID
└── NID_CORRECTION
    ├── NID_CORRECTION_NAME
    ├── NID_CORRECTION_PARENT_NAME
    ├── NID_CORRECTION_DOB
    ├── NID_CORRECTION_GENDER
    ├── NID_CORRECTION_BLOOD_GROUP
    ├── NID_CORRECTION_MARITAL_STATUS
    ├── NID_CORRECTION_ADDRESS
    ├── NID_CORRECTION_PHOTO
    └── NID_CORRECTION_SIGNATURE

This is illustrative only. Final IDs will be frozen after the complete
parent/leaf review.

---

## Freeze Rule

No NID parent-topic or query-topic IDs will be copied into
`contracts/labels.yaml` until:

- parent topics are finalized;
- every leaf belongs to exactly one parent;
- neighboring intent overlaps have inclusion/exclusion rules;
- supported versus unsupported NID areas are explicit;
- Partner B can build corpus entries using the same IDs.

Until then, `taxonomy/nid.yaml` remains a working taxonomy document.
