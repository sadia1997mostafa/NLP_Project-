# NagorikSheba Partner A Codex Handoff

## 1. Repository State

- Repository: `D:\Files\Academic\4-1\NLP\NLP Project\NLP_Project-`
- Branch: `partner-a/c1-contract-freeze`
- HEAD: `811c6fc21185d7966532df24cb4df4f416ddb4af` (`Record Driving Licence parent evaluation`)
- This automation deliberately made no commit and no push.
- `docs/OWNERSHIP.md` was already modified when this automation began. It is user-owned unrelated work and was not read for editing, modified, staged, restored, deleted, or overwritten by Codex.
- Compact model directories under `models/final/` are ignored local artifacts and therefore do not appear in ordinary Git status.
- Historical service artifact `models/final/service_pre_police_boundary_repair/` was preserved.
- Historical evaluation artifacts were preserved. No TEST artifact was opened or overwritten during this continuation.

Tracked files modified by Partner A automation, excluding the pre-existing ownership change:

- `models/evaluation/training_run_summary.json`
- `src/models/dataset.py`
- `src/models/inference.py`
- `src/models/train_classifier.py`
- `src/preprocessing/task_views.py`
- `tests/test_pretraining_readiness.py`

New source/config/document files:

- `configs/classifier_intent_small_balanced.yaml`
- `configs/classifier_priority_balanced.yaml`
- `configs/classifier_priority_unweighted.yaml`
- `src/models/benchmark_inference.py`
- `src/models/build_intent_inventory.py`
- `src/models/calibrate_ood.py`
- `src/models/checkpoint_selection.py`
- `src/models/evaluate_checkpoint.py`
- `src/models/evaluate_hierarchy_dev.py`
- `src/models/hierarchy.py`
- `src/models/run_intent_hierarchy.py`
- `src/models/run_priority_experiments.py`
- `src/models/summarize_hierarchy_dev.py`
- `src/models/validate_inference_api.py`
- `src/models/verify_final_models.py`
- `docs/PARTNER_A_CODEX_HANDOFF.md`

New evaluation artifacts are listed in Section 12.

## 2. Dataset Contract

- Services: `NID`, `BIRTH_REGISTRATION`, `PASSPORT`, `TAX`, `POLICE_GD`, and `DRIVING_LICENCE`.
- In-domain rows: 3,168.
- Parent topics: 49.
- Query-topic/intent leaves: 264.
- OOD rows: 360.
- Canonical split sizes: train 1,584; DEV 792; TEST 792.
- Family-safe split rule: F01/F02 to train, F03 to DEV, F04 to TEST. Query families are not split across partitions.
- Dataset provenance is synthetic/paraphrased. No generated row is represented as REAL.
- This continuation used `data/splits/dev.csv` and `data/splits/ood_dev.csv` only for evaluation/calibration.
- `data/splits/test.csv` and `data/splits/ood_test.csv` were not read, evaluated, or used for model/threshold selection.

## 3. Final Architecture

The implemented Partner A flow is:

```text
query
  -> balanced six-class service model
  -> service-specific parent model
  -> service-level parent-conditioned intent model
     (logits masked to leaves of the routed parent)
  -> independent priority model
  -> provisional service-MSP OOD/confidence decision
  -> predict_understanding()
```

There are six service-level intent models, not one backbone per parent. This avoids duplicating 44 full XLM-R backbones. Of the 49 parents, five have exactly one intent and route deterministically; 44 have multiple leaves and use their service intent model with a frozen parent-specific mask. All 264 frozen intent IDs are covered.

Partner B privacy, retrieval, response control, backend, and UI work are not implemented here.

## 4. Final Model Inventory

Every compact directory contains `config.json`, `model.safetensors`, and `selection.json`. `python -m src.models.verify_final_models` load-tested all 14 classifiers and confirmed expected label counts. All selection metadata uses `dev_macro_f1`; none records a new TEST selection.

| Path | Task | Labels | Selected DEV Macro F1 | Status |
|---|---:|---:|---:|---|
| `models/final/service/` | service | 6 | 0.903593 | selected post-repair |
| `models/final/parent/NID/` | parent | 9 | 0.667306 | selected |
| `models/final/parent/BIRTH_REGISTRATION/` | parent | 8 | 0.580561 | selected |
| `models/final/parent/PASSPORT/` | parent | 8 | 0.838707 | selected |
| `models/final/parent/TAX/` | parent | 6 | 0.717245 | selected |
| `models/final/parent/POLICE_GD/` | parent | 8 | 0.610902 | selected post-boundary repair |
| `models/final/parent/DRIVING_LICENCE/` | parent | 10 | 0.680617 | selected |
| `models/final/intent/NID/` | service intent | 73 | 0.513681 | selected research baseline |
| `models/final/intent/BIRTH_REGISTRATION/` | service intent | 30 | 0.382717 | selected research baseline |
| `models/final/intent/PASSPORT/` | service intent | 56 | 0.562276 | selected research baseline |
| `models/final/intent/TAX/` | service intent | 33 | 0.305188 | selected research baseline |
| `models/final/intent/POLICE_GD/` | service intent | 32 | 0.290997 | selected research baseline |
| `models/final/intent/DRIVING_LICENCE/` | service intent | 40 | 0.301672 | selected research baseline |
| `models/final/priority/` | priority | 3 | 0.543622 | selected, manual review required |

The service intent scores in this table are the unmasked service-wide selection scores. Oracle-parent masked results are in Section 7.

## 5. Service Model

- Final path: `models/final/service/`.
- Source checkpoint: `models/checkpoints/service_balanced/checkpoint-297` (temporary directory removed only after compact-model verification).
- Best epoch: 3.
- DEV accuracy: 0.9128787878787878.
- DEV Macro F1: 0.9035931903363533.
- DEV weighted F1: 0.9111166377320565.
- Major DEV confusions: `POLICE_GD -> NID` 18, `DRIVING_LICENCE -> TAX` 15, `DRIVING_LICENCE -> NID` 12, and `TAX -> NID` 5.
- Historical pre-Police-boundary model: `models/final/service_pre_police_boundary_repair/`.

The corrected service model was evaluated only on DEV during this continuation. Historical TEST files remain in the repository but were not accessed for this work.

## 6. Parent Models

Selected service-specific parent DEV Macro F1 values:

- NID: 0.667306471064641.
- Birth Registration: 0.5805607522877136.
- Passport: 0.8387069372587665.
- Tax: 0.7172454451866216.
- Police GD: 0.6109016865278136.
- Driving Licence: 0.6806167262689001.

All six load successfully. They were not retrained in this continuation.

## 7. Intent Models

Architecture: six service-level XLM-R models trained with service/parent context. At evaluation and inference, logits are restricted to the frozen intent leaves belonging to the routed parent. Five single-leaf parents bypass intent inference deterministically.

| Service | Leaves | Best epoch | Unmasked DEV acc/F1 | Oracle-parent routed DEV acc/F1 |
|---|---:|---:|---:|---:|
| Birth Registration | 30 | 12 | 0.433333 / 0.382717 | 0.466667 / 0.427161 |
| Driving Licence | 40 | 10 | 0.350000 / 0.301672 | 0.450000 / 0.372684 |
| NID | 73 | 12 | 0.575342 / 0.513681 | 0.611872 / 0.537879 |
| Passport | 56 | 10 | 0.625000 / 0.562276 | 0.636905 / 0.574706 |
| Police GD | 32 | 9 | 0.364583 / 0.290997 | 0.468750 / 0.415037 |
| Tax | 33 | 11 | 0.383838 / 0.305188 | 0.454545 / 0.374830 |

Across all 792 DEV rows with gold service and parent routing, intent accuracy is 0.539141 and Macro F1 is 0.472809. Twenty-four parent topics have DEV Macro F1 below 0.5. The authoritative complete per-parent list is `models/evaluation/intent_training_summary.json`; the low-scoring parents are:

- `NID_REGISTRATION`, `NID_REPLACEMENT`, `NID_SMART_CARD`, `NID_FEES_AND_PAYMENT`, `NID_GENERAL_INFORMATION`.
- `BR_REGISTRATION`, `BR_CORRECTION`.
- `PASSPORT_APPOINTMENT_AND_ENROLMENT`, `PASSPORT_REISSUE`, `PASSPORT_FEES_AND_PAYMENT`.
- `TAX_TIN_REGISTRATION`, `TAX_RETURN_FILING`, `TAX_ONLINE_ACCOUNT`, `TAX_STATUS_AND_DOCUMENTS`.
- `POLICE_GD_INCIDENT_TYPE`, `POLICE_GD_ONLINE_ACCOUNT`, `POLICE_GD_STATUS_FOLLOWUP`, `POLICE_GD_COPY_REFERENCE`.
- `DRIVING_LICENCE_LEARNER`, `DRIVING_LICENCE_TEST`, `DRIVING_LICENCE_PAYMENT`, `DRIVING_LICENCE_STATUS_DELIVERY`, `DRIVING_LICENCE_RENEWAL`, `DRIVING_LICENCE_REPLACEMENT`.

The very small support per intent (six train and three DEV examples in the current family split) and generic augmentation wrappers are known limitations. No DEV examples were rewritten and no semantic dataset changes were made to improve these scores.

## 8. Priority

Train distribution: Low 1,164; Medium 414; High 6. DEV distribution: Low 582; Medium 207; High 3. High occurs only in Police GD training data.

- Unweighted DEV accuracy/Macro F1: 0.8686868686868687 / 0.5436215552012863.
- Balanced DEV accuracy/Macro F1: 0.8623737373737373 / 0.5407780327162831.
- Selected: unweighted, `models/final/priority/`, source checkpoint 297, epoch 3.
- Selected confusion matrix order: High, Low, Medium.
- Selected confusion matrix: `[[0, 2, 1], [0, 560, 22], [0, 79, 128]]`.

Neither fixed experiment correctly predicted any of the three DEV High examples. This requires manual product/scientific review; annotations were not altered and no claim of reliable urgency detection is justified.

## 9. OOD Calibration

- Method: maximum softmax probability from the corrected service classifier.
- Calibration material: 792 in-domain DEV rows plus 180 OOD DEV rows only.
- Provisional threshold: 0.95; a prediction below it is rejected.
- Balanced accuracy: 0.6613636363636364.
- OOD F1: 0.4444444444444444.
- In-domain acceptance: 0.8560606060606061.
- OOD rejection: 0.4666666666666667.
- False rejection: 0.14393939393939395.
- False acceptance: 0.5333333333333333.
- AUROC: 0.7634645061728395.
- AUPR: 0.4257113313719999.
- FPR95: 0.6616161616161617.
- Status: `provisional_synthetic_dev_only`.

This is a simple auditable baseline, not a safety guarantee. Neither TEST nor OOD TEST was used.

## 10. End-to-End DEV Evaluation

The completed evaluation used all 792 in-domain DEV rows and no TEST data.

Oracle routing (gold service for parent; gold service and parent for intent):

- Parent accuracy/Macro F1: 0.727273 / 0.680750.
- Intent accuracy/Macro F1: 0.539141 / 0.472809.

Predicted routing:

- Service accuracy/Macro F1: 0.912879 / 0.903593.
- Parent accuracy/Macro F1: 0.665404 / 0.611958.
- Intent accuracy/Macro F1: 0.363636 / 0.305268.
- Priority accuracy/Macro F1: 0.868687 / 0.543622.
- Service-to-parent exact path accuracy: 0.665404.
- Service-to-parent-to-intent exact path accuracy: 0.363636.
- Exact service/parent/intent/priority accuracy: 0.316919.
- Full exact match additionally requiring acceptance as in-domain: 0.295455.

Error propagation counts:

- Service routing errors: 69.
- Parent errors with oracle service: 216.
- Parent errors after a correct predicted service: 196.
- Intent errors with oracle service and parent: 365.
- Intent errors after correct predicted service and parent: 239.
- Priority errors: 104.
- In-domain DEV false OOD rejections: 114.

These results are diagnostic. No retraining or data repair was performed in response.

## 11. Inference API

- Public module/function: `src.models.inference.predict_understanding(text)`.
- Main result fields: normalized `text`, `service`, `service_confidence`, `parent_topic_id`, `parent_topic`, `parent_confidence`, `query_topic_id`, `query_topic`, `intent_confidence`, `intent_routing`, `priority`, `priority_confidence`, `is_ood`, `ood_score`, `overall_confidence`, `calibration_status`, `warnings`, and per-component `alternatives`.
- A shared local XLM-R tokenizer is cached once.
- A bounded LRU holds at most four classifier models, enough for service + routed parent + routed intent + priority. A route change evicts old route models to CPU; it does not load all 14 models onto the GPU.
- CPU fallback remains available when CUDA is unavailable.

Measured on this Windows machine with RTX 3060 using manually written safe queries:

- Framework dependency import: 3.10 seconds inside the benchmark.
- Tokenizer load: 2.98 seconds.
- Representative GPU model load/move: service 7.05s, NID parent 10.62s, NID intent 6.58s, priority 9.41s.
- First complete call after cache clear: 36.89 seconds in the isolated benchmark; 59.76 seconds in a separate fresh API smoke process.
- Same-route warm call: 0.34 seconds.
- Different-service route: 19.80 to 20.02 seconds.
- Four-model steady allocation: approximately 4.25 GiB.
- Observed peak allocation during route change: approximately 5.31 GiB.

The API smoke validation passed frozen parent/intent membership, confidence bounds, OOD consistency, priority vocabulary, deterministic routing, and cache reuse. Two deterministic Birth Registration routes were exercised. A manual Birth Registration cancellation query was predicted as Birth Registration application status; this is a model-quality limitation. A separate manual NID replacement query in the benchmark was misrouted to Driving Licence and rejected as OOD. These examples were not used to tune or rewrite data.

Cold and route-change latency remains too high for an interactive production claim. Warm same-route inference is fast, but Partner B should integrate a long-lived worker/process rather than launching Python for every request.

## 12. Evaluation Artifact Inventory

Corrected service DEV:

- `models/evaluation/service_balanced_post_police_repair_dev_metrics.json`
- `models/evaluation/service_balanced_post_police_repair_dev_predictions.csv`

Existing parent predictions/metrics located in the repository:

- `models/evaluation/birth_parent_dev_metrics.json`
- `models/evaluation/birth_parent_dev_predictions.csv`
- `models/evaluation/driving_licence_parent_dev_predictions.csv`
- `models/evaluation/police_gd_parent_dev_predictions.csv`
- `models/evaluation/police_gd_parent_dev_predictions_pre_boundary_repair.csv`
- Selection metadata for every parent is also in its `models/final/parent/<SERVICE>/selection.json` and in `models/evaluation/training_run_summary.json`.

Intent:

- `models/evaluation/intent_parent_inventory.csv`
- `models/evaluation/intent_parent_inventory.json`
- `models/evaluation/intent_training_summary.csv`
- `models/evaluation/intent_training_summary.json`
- `models/evaluation/intent/<SERVICE>_dev_metrics.json`
- `models/evaluation/intent/<SERVICE>_dev_predictions.csv`

Priority:

- `models/evaluation/priority_unweighted_dev_metrics.json`
- `models/evaluation/priority_unweighted_dev_predictions.csv`
- `models/evaluation/priority_balanced_dev_metrics.json`
- `models/evaluation/priority_balanced_dev_predictions.csv`
- `models/evaluation/priority_training_summary.json`

OOD:

- `models/evaluation/ood_dev_calibration.json`
- `models/evaluation/ood_dev_scores.csv`

Hierarchy and API engineering:

- `models/evaluation/hierarchical_dev_metrics.json`
- `models/evaluation/hierarchical_dev_predictions.csv`
- `models/evaluation/hierarchical_dev_error_summary.json`
- `models/evaluation/inference_latency_dev_safe.json`
- `models/evaluation/inference_api_dev_safe_smoke.json`
- `models/evaluation/final_model_inventory.json`
- `models/evaluation/training_run_summary.json`

Historical TEST-named artifacts that predated this continuation remain untouched and are not part of the continuation evaluation.

## 13. Tests

- `python -m pytest -q`: 14 passed. One non-fatal warning reports that pytest cannot create `.pytest_cache` because of filesystem permissions.
- `python -m compileall -q src`: passed.
- Machine-readable JSON parse checks: passed.
- `git diff --check`: passed; only Git line-ending notices are emitted for working-copy files.
- `python -m src.models.verify_final_models`: all 14 compact models load with expected label counts.
- `python -m src.models.validate_inference_api`: passed on manually written safe queries.

## 14. Known Limitations

- The labeled dataset is synthetic/paraphrased only; it does not establish real-user performance.
- Generic augmentation wrappers can omit service cues and create overlapping class language.
- Twenty-four parent-level intent groups have DEV Macro F1 below 0.5; three (`POLICE_GD_INCIDENT_TYPE`, `DRIVING_LICENCE_TEST`, and `DRIVING_LICENCE_RENEWAL`) scored 0 in oracle-parent intent evaluation.
- Every intent has only six train and three DEV rows under the present family split.
- The High-priority class has six train and three DEV rows, all from Police GD; neither priority experiment correctly predicts a DEV High example.
- OOD false acceptance is 53.33% at the provisional threshold, while in-domain false rejection is 14.39%.
- End-to-end predicted intent Macro F1 is 0.3053 and full exact match including OOD acceptance is 29.55%.
- Manual smoke examples expose parent/service routing errors even when service words appear explicitly.
- Cold start and different-route loading are slow on the measured Windows system, although same-route cache latency is approximately 0.34 seconds.
- An older `models/checkpoints/parent_balanced/PASSPORT/` experiment remains. It was not deleted because the selected final Passport parent came from `parent_small_balanced/PASSPORT/checkpoint-294`, so the old run's historical status should be confirmed manually first.
- There has been no held-out final TEST evaluation for these newly selected components.
- There has been no real-user validation.
- No production-readiness or safety claim is warranted.

## 15. What Must Be Reviewed Manually With ChatGPT

1. Decide whether the current weak intent and end-to-end DEV results are sufficient for the academic showcase, without rewriting DEV examples.
2. Review the 24 weak parent intent groups and generic augmentation limitation as methodological findings.
3. Decide whether to expose the learned priority model as-is or add a conservative product-level escalation policy owned and documented separately; do not silently relabel High.
4. Review the OOD threshold trade-off, especially 53.33% false acceptance and 14.39% false rejection.
5. Review hierarchy error propagation and the two manual smoke misroutes.
6. Approve a single locked final TEST protocol before anyone opens TEST or OOD TEST for final evaluation.
7. Decide which uncommitted code, configs, and DEV artifacts should be committed.
8. Decide whether the historical Passport checkpoint experiment can be deleted.
9. Define the exact interface and artifacts Partner B receives, including the requirement for a persistent inference worker.
10. Decide whether the current code and latency are showcase-ready; do not equate warm-cache success with production readiness.

## 16. Exact Remaining Work

Partner A manual work:

- Review and commit selected artifacts only after inspecting `git diff` and preserving `docs/OWNERSHIP.md` as unrelated work.
- Lock the final TEST protocol; run it once later only with explicit authorization.
- Make final showcase decisions for weak intent groups, priority High behavior, OOD threshold, and inference startup.
- Record conclusions as limitations rather than performing test-driven tuning.

Partner B integration work:

- Consume `predict_understanding()` from a long-lived backend worker.
- Add Partner B-owned privacy detection, corpus retrieval, controlled response, backend, and UI layers.
- Use the frozen service/parent/intent IDs exactly and handle `is_ood`, calibration status, and warnings.
- Decide deployment/process lifecycle and avoid per-request Python/model cold starts.

Future research-paper work:

- Collect and annotate real citizen queries under approved privacy controls.
- Evaluate robustness and calibration on genuinely independent data.
- Compare stronger intent and OOD approaches under a pre-registered evaluation protocol.
- Report synthetic-data, imbalance, calibration, and latency limitations without production claims.
