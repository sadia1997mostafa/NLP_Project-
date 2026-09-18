# Partner B live integration check

Date: 2026-09-18. This is a manually written, showcase-oriented smoke check,
not a new evaluation on Prothom's held-out TEST data.

## Artifacts and environment

- Prothom runtime freeze: `38a343d`; official results: `f2f4e3e`.
- The uploaded `final/` folder was placed at `models/final/` and remains Git
  ignored. Prothom's verifier loaded all 13 active neural classifiers and
  confirmed their label counts. The historical priority model remains inactive.
- Local smoke environment: Python 3.14.3, CPU-only PyTorch 2.11.0,
  Transformers 5.15.1. The documented app dependency range targets
  Transformers 4, so repeat the smoke test in the chosen deployment environment.

## Observed behavior

- The real HTTP API accepted all six manually written service questions and
  retrieved guidance from the matching service namespace.
- A query containing an NID number returned a privacy warning and masked
  output; the raw number was absent from the HTTP response.
- An unrelated weather question was falsely accepted by Prothom's provisional
  OOD classifier. Partner B's response controller now asks for clarification
  for any unanchored model decision, including exact and parent matches. The
  classifier and its threshold were not changed.
- In one long-lived HTTP process, the first Police GD request took about
  5.14 seconds on this CPU, and a same-route repeat took about 0.18 seconds.
  These are local observations, not a latency guarantee.
- `python -m scripts.smoke_live` passes with the local model files. The normal
  test suite uses injected predictors so it remains runnable without them.

## Remaining limits

The initial corpus had 14 records. After the source-reviewed expansion it has
67 records, including exact guidance for 56 of 264 intents; see the
[corpus review](../knowledge_base/SOURCE_REVIEW.md).
The privacy detector is pattern-based and cannot identify every personal
detail. Prothom's synthetic-data accuracy and provisional OOD rule do not
establish real-world reliability. A browser-based visual check was unavailable
in this session.

## Corpus expansion verification

- `python -m scripts.audit_corpus`: 67 records, 56 exact topics, 22 source
  URLs, 11 document lists; no review older than 90 days on 2026-09-18.
- Python suite: 43 passing tests; Node checklist-state suite: four passing tests.
  Every exact corpus route is checked against retrieval, independently of models.
- The original six live smoke queries still produced service-level fallbacks.
  Corpus expansion alone did not fix their specific-topic classification.
- Two additional manually authored Banglish queries correctly reached
  `NID_CORRECTION_DOB` and `BR_VERIFICATION_RECORD` with exact cited answers.
- A separate manual passport-status query was misclassified as
  `PASSPORT_GENERAL_NEW_VS_REISSUE` and fell back to service guidance.
  A learner-documents query was misclassified as learner eligibility and
  received that exact record. This demonstrates why exact retrieval is not
  proof of correct understanding; classifier evaluation remains separate work.
- The weather regression still asks for clarification even though its predicted
  NID date-of-birth topic now has an exact record. No model, taxonomy, priority
  mapping or OOD threshold was changed, and held-out TEST was not rerun.
- No connected browser was available for screenshots. Checklist rendering,
  text-only insertion and clearing between states were tested with Node DOM
  doubles; these are not a substitute for browser visual QA.
