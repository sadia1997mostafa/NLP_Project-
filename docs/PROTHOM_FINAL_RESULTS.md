# Prothom Final NLP Results

## Status

Prothom's hierarchical query-understanding implementation is frozen and has completed its single official held-out TEST evaluation.

- Frozen runtime commit: `38a343d`
- Frozen TEST protocol commit: `f4fa8ea`
- No model, routing rule, taxonomy, threshold, or dataset change is permitted based on TEST results.
- TEST rows: 792
- `test_data_used`: true

## Final Runtime Architecture

```text
User query
   |
   v
Unique lexical service anchor
   |-- if unavailable --> XLM-R service classifier
   |
   v
Service-conditioned parent-topic classifier
   |
   v
Selected hybrid service-level intent classifier
   |
   v
Parent-conditioned intent masking / deterministic single-leaf routing
   |
   v
Frozen intent -> priority contract
   |
   v
Structured predict_understanding() output
```

The active runtime contains 13 neural classifiers:

- 1 service classifier
- 6 service-specific parent classifiers
- 6 service-specific intent classifiers

Priority is not a neural classifier in the active runtime. It is derived deterministically from the predicted intent using `configs/priority_by_intent.json`, containing 264 intent mappings.

## Official Held-out TEST Results

| Metric                           |    DEV |   TEST |
| -------------------------------- | -----: | -----: |
| Service accuracy                 | 0.9823 | 0.8699 |
| Service Macro F1                 | 0.9824 | 0.8389 |
| Parent accuracy                  | 0.7184 | 0.6010 |
| Parent Macro F1                  | 0.6725 | 0.5182 |
| Intent accuracy                  | 0.4179 | 0.4091 |
| Intent Macro F1                  | 0.3537 | 0.3561 |
| Priority accuracy                | 0.8422 | 0.8295 |
| Priority Macro F1                | 0.7970 | 0.7095 |
| Service -> Parent path           | 0.7184 | 0.6010 |
| Service -> Parent -> Intent path | 0.4179 | 0.4091 |
| Exact understanding              | 0.4179 | 0.4091 |

### TEST oracle-routing diagnostics

- Parent accuracy with gold service routing: 0.6881
- Parent Macro F1 with gold service routing: 0.6150
- Intent accuracy with gold service + parent routing: 0.5909
- Intent Macro F1 with gold service + parent routing: 0.5207

These oracle results are diagnostic ceilings for the frozen component models, not production-path scores.

## Service Anchors

- TEST rows receiving a unique service anchor: 295
- DEV rows receiving a unique service anchor: 518

The anchor-enhanced service router performed much better on DEV than TEST. This indicates that the DEV-selected lexical anchors did not generalize equally across the held-out family split. No anchor was added, removed, or modified after observing TEST.

## Priority

Priority is deterministically derived from predicted `query_topic_id`.

TEST:

- Priority accuracy: 0.8295
- Priority Macro F1: 0.7095

Because priority is deterministic given the predicted intent under the current annotation contract, exact-understanding accuracy equals the Service -> Parent -> Intent path accuracy:

- Path accuracy: 0.4091
- Exact understanding: 0.4091

This deterministic relationship is a property of the present dataset contract and should not be generalized to all future government-service datasets.

## OOD / Confidence

Frozen method: `anchor_aware_service_routing_confidence`

- DEV-selected confidence threshold: 0.95
- Trusted-anchor TEST rows: 253
- In-domain TEST acceptance rate: 0.9268
- In-domain TEST false-rejection rate: 0.0732

The official hierarchical TEST evaluation contains in-domain TEST rows. Therefore these values measure false rejection / acceptance of known in-domain queries. They do not constitute held-out OOD detection performance.

OOD calibration remains provisional and synthetic-DEV-based.

## Key Interpretation

The final system achieved 40.91% exact hierarchical understanding accuracy on the held-out TEST split.

Intent-level performance remained stable between DEV and TEST, while service and parent routing showed a larger generalization gap. This identifies routing robustness, particularly parent-topic prediction and service-anchor generalization, as the principal future modeling target.

The system is suitable as the implementation baseline for the NagorikSheba project, but the present results must not be described as production-ready or real-world validated.

## Dataset Limitations

The current supervised corpus is synthetic/paraphrased rather than a corpus of verified real citizen queries.

Consequently:

- results demonstrate implementation feasibility under the current controlled dataset;
- they do not establish real-world citizen-query performance;
- future work should collect and annotate genuine Bangla/Banglish citizen queries;
- real-world validation should be performed without modifying this held-out TEST result retrospectively.

## Frozen-result Rule

The held-out TEST set was evaluated once after the runtime and TEST protocol were committed.

No subsequent model selection, hyperparameter tuning, lexical-anchor editing, threshold tuning, taxonomy editing, data repair, or architecture selection may use these TEST results.

Future improvements must return to TRAIN/DEV or use a newly defined evaluation protocol.
