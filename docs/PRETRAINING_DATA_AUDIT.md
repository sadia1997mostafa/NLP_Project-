# Pre-Training Dataset Report

Generated deterministically by `prepare_pretraining_data.py`.

## In-domain services

| Service | Rows | Parents | Leaves | Families | Min/Max rows per leaf |
|---|---:|---:|---:|---:|---:|
| NID | 876 | 9 | 73 | 292 | 12/12 |
| BIRTH_REGISTRATION | 360 | 8 | 30 | 120 | 12/12 |
| PASSPORT | 672 | 8 | 56 | 224 | 12/12 |
| TAX | 396 | 6 | 33 | 132 | 12/12 |
| POLICE_GD | 384 | 8 | 32 | 128 | 12/12 |
| DRIVING_LICENCE | 480 | 10 | 40 | 160 | 12/12 |

Total in-domain rows: **3168**
Total production intents: **264**

## Provenance

- PARAPHRASED: 2112
- SYNTHETIC: 1056

## OOD

- Rows: 360
- Categories: 12
- All OOD content is synthetic and privacy-negative.

## Integrity

- Exact normalized in-domain duplicates: 0
- Exact normalized OOD duplicates: 0
- Near-duplicate scan: token-set Jaccard >= 0.86
- Near-duplicate cross-family pairs: 0
- Near-duplicate cross-intent pairs requiring attention: 0
- NID historical source rows available in repository: 0
- NID REAL rows claimed: 0
- Split unit: complete `parent_query_id` family
- Split rule for four-family leaves: F01/F02 train, F03 dev, F04 test

## Known limitations

- NID has no historical source artifact in this repository; its balanced core is synthetic.
- Rule-based paraphrases received automated checks, not human review.
- OOD coverage is synthetic and thresholds remain to be calibrated after training.
