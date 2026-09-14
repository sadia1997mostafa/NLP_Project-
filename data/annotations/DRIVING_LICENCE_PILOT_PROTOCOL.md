# Driving Licence Pilot Dataset Protocol

Owner: Prothom / Prothom

Service: `DRIVING_LICENCE`

Taxonomy version: `0.2.0`

Training status: `DO NOT TRAIN YET`

## Purpose

This pilot tests whether the reviewed taxonomy can be applied consistently to
natural citizen queries. It is not a training dataset or a source of current
government facts.

## Structure

- Leaves: 40
- Independent seeds per leaf: 4
- Rows and unique query families: 160
- F01: Formal / Easy
- F02: Informal / Medium
- F03: Mixed / Medium
- F04: Mixed / Hard

Every row follows the canonical 16-column project schema. All initial rows
are `SYNTHETIC`, privacy-negative, and in-domain. A family ID is unique to
each seed; later paraphrases must inherit the seed family and remain in one
data split.

## Quality rules

- Classify the citizen's primary information need.
- Prefer the most specific supported leaf.
- Do not add mutable fees, rates, deadlines, office addresses, or processing
  times to query text.
- Do not manufacture Hard examples with “X না, Y” classifier hints.
- General information is never an OOD or low-confidence fallback.
- Human semantic review is required for every row before any expansion.

## Acceptance

The pilot passes only when its taxonomy, schema, IDs, parent-child relations,
four-row leaf balance, unique texts, unique families, metadata, and completed
review worksheet all pass the repository validator.
