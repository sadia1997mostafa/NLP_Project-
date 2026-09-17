# Guidance corpus

`guidance.json` contains 14 small, source-backed English records: one general
pointer for each supported service, two parent-topic records, and six exact
query-topic records. It is deliberately not a complete guide to all 264
intents. All source links point to the relevant Bangladesh government service
site. Records were reviewed on 2026-09-18.

Keep changing government facts here, never in the classifier or taxonomy.
Before adding a record, check its official source, keep its claims within what
that page supports, and set `last_verified` to the actual review date. Avoid
fees, deadlines, and document lists unless the exact official page supports
them and there is a process to keep them current.

Run `python -m unittest tests.test_guidance_corpus` to validate the corpus.
