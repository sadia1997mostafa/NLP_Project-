# Provisional Paraphrase Adjudication Protocol V1

## Scope and provenance

This protocol converts the 99 lexical candidates from Phase 1 Task 1 into
provisional semantic pair decisions. Every decision has
`adjudication_source = codex_provisional`. These are machine-assisted research
annotations, not human gold labels. Source text, labels, and Phase 0 splits are
immutable in this task.

Similarity scores nominate pairs for review but never determine semantic
equivalence by themselves. The primary criterion is whether both citizen
queries seek the same information or action and could receive materially the
same correct response.

## Pair decisions

- `SAME_MEANING`: the citizen intent/information need is clearly equivalent
  despite spelling, script, word order, or minor slot variation.
- `SAME_TEMPLATE_DIFFERENT_MEANING`: the sentence frame is shared but a slot
  changes the requested action or information.
- `RELATED_NOT_PARAPHRASE`: the concepts are close, yet correct routing or a
  correct answer could differ.
- `LABEL_CONFLICT_SAME_MEANING`: meanings are equivalent while frozen source
  labels differ. No label is repaired.
- `AMBIGUOUS_REVIEW_REQUIRED`: available wording is insufficient for a reliable
  equivalence decision.
- `NOT_PARAPHRASE`: lexical overlap is high but meanings materially differ.

## Confidence

- `HIGH`: semantic equivalence or non-equivalence is clear from both queries.
- `MEDIUM`: the decision is likely, but a meaningful ambiguity remains.
- `LOW`: human confirmation is required before benchmark grouping.

## Reason codes

Allowed codes are `EXACT_EQUIVALENCE`, `SPELLING_VARIANT`, `SCRIPT_VARIANT`,
`WORD_ORDER_VARIANT`, `SLOT_VARIANT_SAME_INTENT`,
`SAME_FRAME_DIFFERENT_SLOT_MEANING`, `DIFFERENT_SERVICE_ACTION`,
`BROADER_VS_NARROWER`, `RELATED_CONCEPT`, `SOURCE_LABEL_CONFLICT`,
`INSUFFICIENT_CONTEXT`, `LEXICAL_FALSE_POSITIVE`, and `OTHER`.

## Family construction

Only `SAME_MEANING` and `LABEL_CONFLICT_SAME_MEANING` create graph edges.
Connected components receive deterministic family IDs. Components larger than
two members require an all-member consistency check; unsafe implied
transitivity results in `HUMAN_REVIEW_REQUIRED`. All unlinked samples receive
deterministic singleton IDs. Cross-label equivalence components retain their
original labels and receive `LABEL_CONFLICT` status.

## Human review

Low/medium-confidence decisions, ambiguous decisions, label-conflict
equivalences, risky cross-label equivalences, unsafe components, and unresolved
high-similarity cross-split pairs enter the private human-review queue. Final
benchmark-grade family membership remains pending human confirmation.
