# Birth Registration Expanded v0.2 — Semantic Quality Audit

Owner: Prothom
Service: `BIRTH_REGISTRATION`
Taxonomy version: `0.2.0`
Dataset: `birth_registration_expanded_v0_2.csv`

## Dataset State

Expanded v0.2 contains:

360 total rows
120 canonical SYNTHETIC seeds
240 PARAPHRASED rows
120 semantic query families
30 query-topic labels
12 rows per query topic
3 rows per family

The structural validator passes.

Result:

`PASS_WITH_TARGETED_QUERY_REFINEMENT_REQUIRED`

---

## 1. Semantic-Preservation Review

The 240 generated paraphrases were reviewed against:

- their canonical seed;
- `parent_query_id`;
- `parent_topic_id`;
- `query_topic_id`;
- neighboring classifier labels.

No systematic query-topic drift was found.

The major taxonomy boundaries remain represented correctly, including:

registration process / online application

required documents / missing documents

OTP not received / OTP verification failure

general correction / field-specific correction

own-name correction / parent-information correction

parent-information correction / parent-BRN mapping

application status / application delay / processing time

submitted-application print / issued-certificate reprint

verification / verification failure

correction / cancellation

service workflow / fee information

Therefore the 30-label taxonomy does not currently require a merge or
split because of the v0.2 paraphrases.

---

## 2. Standalone Service-Classification Risk

A separate problem was found.

Some paraphrases preserve the correct query-topic meaning when viewed
inside their Birth Registration family, but contain too little service
context when viewed as standalone citizen queries.

This matters because NagorikSheba must first predict the government
service before predicting the detailed query topic.

For example:

`otp sms ashche na, ki kori?`

correctly expresses an OTP-not-received problem, but the same query
could refer to NID, Passport, Tax, or another online government service.

Therefore semantic-family correctness alone is not sufficient.

A training query intended for standalone service classification should
normally contain enough evidence to associate it with its service,
unless it is deliberately being used as an ambiguity/OOD/confidence
example.

---

## 3. Priority Rows for Repair

The following generated rows are particularly context-poor and should
be revised before model training:

BRQ_0136
`office niye na, online apply process ta ki?`

BRQ_0144
`address field na, office selection ta kivabe korbo?`

BRQ_0152
`local office na, embassy diye apply korte chai`

BRQ_0182
`applicant relation option e konta select korbo?`

BRQ_0190
`required kagojpotro gula ki ki?`

BRQ_0204
`otp sms ashche na, ki kori?`

BRQ_0208
`code receive kori nai, etai problem`

BRQ_0212
`code diyeo accept kortese na keno?`

BRQ_0214
`otp ase but verification fail hocche`

BRQ_0220
`submit dile data final hoye jabe?`

BRQ_0236
`name spelling vul, correct korbo kivabe?`

BRQ_0246
`DOB ta correct korte hobe`

BRQ_0254
`gender info ta change korte chai`

BRQ_0260
`mother name spelling thik korbo kivabe?`

BRQ_0276
`present address ta correct korte chai`

BRQ_0284
`application approve hoise kina check korbo kivabe?`

BRQ_0292
`onek din holo application update nai`

BRQ_0304
`amar application na, normal time limit ta ki?`

BRQ_0308
`submitted application form er copy chai`

BRQ_0316
`certificate abar print korte chai`

BRQ_0332
`verify korle no result ase`

BRQ_0342
`cancel application kothay submit korbo?`

BRQ_0350
`certificate reprint fee koto?`

BRQ_0352
`correction process na, fee amount jante chai`

These rows are not necessarily assigned to the wrong query-topic label.

The issue is that the text alone gives insufficient evidence for
`service = BIRTH_REGISTRATION`.

---

## 4. Repair Principle

Do not solve this by making every query unnaturally verbose.

The goal is to preserve realistic short citizen language while adding
the minimum amount of service evidence required.

Example:

Current:

`otp sms ashche na, ki kori?`

Preferred:

`birth registration er otp sms ashche na, ki kori?`

Current:

`DOB ta correct korte hobe`

Preferred:

`birth registration er DOB ta correct korte hobe`

Current:

`certificate reprint fee koto?`

Preferred:

`birth certificate reprint fee koto?`

The detailed query-topic intent must remain unchanged.

---

## 5. Context-Dependent Queries

Very short context-dependent queries are still useful research data.

However, they should not silently be mixed into ordinary standalone
service-classification supervision.

In a later research stage they can be used for:

conversation-context experiments,
low-confidence examples,
ambiguity analysis,
or OOD/hard-negative evaluation.

The current implementation does not yet contain a separate
conversation-context field, so these examples should be repaired for
the current standalone system.

---

## 6. Synthetic-Language Review

The expanded dataset contains useful variation across:

formal Bangla,
informal Bangla,
Banglish,
Bangla-English code mixing,
short queries,
and longer queries.

The generated paraphrases are sufficiently varied for the current
development stage.

However, synthetic language must not become the only source of model
supervision.

Later dataset versions should introduce genuinely collected and
reviewed citizen-language examples.

Generated examples must continue to be labeled truthfully as:

`PARAPHRASED`

and never as:

`REAL`

---

## 7. Contrastive Wording

A number of queries intentionally contain expressions such as:

`X না, Y`

These remain useful boundary examples.

They should be retained in moderation because they test distinctions
between neighboring labels.

They should not dominate later expansion because a classifier could
learn the explicit contrastive wording rather than the underlying
intent.

---

## 8. Lower-Evidence Topics

Extra care remains required for:

BR_REGISTRATION_MISSING_DOCUMENTS
BR_REGISTRATION_OTP_VERIFICATION
BR_CORRECTION_PARENT_BRN_MAPPING
BR_APPLICATION_DELAY
BR_APPLICATION_PROCESSING_TIME
BR_VERIFICATION_FAILURE
BR_GENERAL_INFORMATION

The v0.2 paraphrases do not currently provide sufficient reason to
remove these labels, but these topics should remain under review until
more natural examples are available.

---

## 9. Current Decision

Structural validation:

`PASSED`

Query-family integrity:

`PASSED`

Paraphrase label preservation:

`PASSED`

Standalone service-context quality:

`TARGETED REPAIR REQUIRED`

Birth Registration taxonomy redesign:

`NOT REQUIRED`

Ready for unrestricted model training:

`NO`

Ready for targeted dataset repair:

`YES`

Shared contract freeze:

`NO`