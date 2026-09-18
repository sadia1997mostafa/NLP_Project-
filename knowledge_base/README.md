# Guidance corpus

`guidance.json` contains 67 source-backed English records, reviewed on
2026-09-18: six service overviews, five parent-level records, and 56 exact
query-topic records. The expansion covers registration, identity corrections,
documents, verification, tracking, receipts, and emergency routing. It is not
a complete guide to all 264 intents.

`answer_facts.json` contains a bilingual answer plan for each of those 67
records. The response builder combines localized actions and cautions from
that plan instead of displaying the `guidance` paragraph as the answer.
Document lists and official source links still come from `guidance.json`.
This is controlled natural-language generation, not an open-ended language
model: it can vary the response by route and language, but cannot answer
questions outside the curated facts or guarantee that a source has not changed.
Any new fact or translation must be checked against the corresponding official
source and reviewed along with the corpus record.

| Service | Exact Topics | Parent Records | Service Records |
| --- | --- | --- | --- |
| NID | 10 / 73 | 1 | 1 |
| Birth registration | 10 / 30 | 2 | 1 |
| Passport | 11 / 56 | 1 | 1 |
| Tax | 8 / 33 | 0 | 1 |
| Police GD | 8 / 32 | 0 | 1 |
| Driving licence | 9 / 40 | 1 | 1 |

There are 22 official source URLs and 11 records with document/information
lists. Conditional items are not universal requirements. An empty list means
this record supplies no checklist, not that the service requires no documents.
Some exact answers explain a verified portal action rather than an entire
administrative process. Content coverage does not measure classifier accuracy.

Keep changing government facts here, never in the classifier or taxonomy.
Before adding a record, check its official source, keep its claims within what
that page supports, and set `last_verified` to the actual review date. Avoid
fees, deadlines, and document lists unless the exact official page supports
them and there is a process to keep them current. No fixed fee, processing-time
promise, filing deadline or current-year tax obligation is asserted here.

See [source review](SOURCE_REVIEW.md) for evidence access and limitations.
`last_verified` is the date of our source review, not the authority's publication
date or a guarantee that a government page is current. Some source text was
available only through indexed official-page excerpts. `notes` is maintainer
metadata, not displayed advice: essential conditions must remain in `guidance`
or `required_documents`.

Before release, run `python -m scripts.audit_corpus` and recheck the source
pages, especially applicability, documents and changing portal controls.
The audit flags reviews older than 90 days; this is a reminder, not automated
fact verification or a claim of freshness for newer records. Use `--json` to
see all 208 topics without dedicated answers. Fees, deadlines, disputes,
refunds and advanced cases remain candidates for separate source review.

Retrieval uses the frozen IDs, exact topic first, then parent, then service.
Fallback records are never counted as exact coverage. The app checks model
predictions against question text and curated titles before showing an answer;
weak or conflicting evidence yields a general overview or clarification.
Visitors can explicitly choose a curated topic instead. A selection must
exactly match a record; it is never treated as evidence that the model made
the right prediction. Frozen classifiers and thresholds are unchanged.

Run `python -m unittest tests.test_guidance_corpus tests.test_answer_facts`
to validate coverage, schema, and rendered answer invariants. These tests do
not replace human source review or a citizen-facing quality evaluation.
