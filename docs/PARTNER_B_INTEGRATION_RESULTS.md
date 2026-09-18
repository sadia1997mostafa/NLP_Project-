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
  when an unanchored model decision has only service-level guidance. The
  classifier and its threshold were not changed.
- In one long-lived HTTP process, the first Police GD request took about
  5.14 seconds on this CPU, and a same-route repeat took about 0.18 seconds.
  These are local observations, not a latency guarantee.
- `python -m scripts.smoke_live` passes with the local model files. The normal
  test suite uses injected predictors so it remains runnable without them.

## Remaining limits

The corpus has 14 verified records, not dedicated answers for all 264 intents.
The privacy detector is pattern-based and cannot identify every personal
detail. Prothom's synthetic-data accuracy and provisional OOD rule do not
establish real-world reliability. A browser-based visual check was unavailable
in this session.
